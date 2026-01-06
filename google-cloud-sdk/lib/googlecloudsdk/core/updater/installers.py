# -*- coding: utf-8 -*- #
# Copyright 2013 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Implementations of installers for different component types."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import re
import stat
import tarfile

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import local_file_adapter
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import transport
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.credentials import exceptions as creds_exceptions
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import http_encoding
from googlecloudsdk.core.util import retry

import requests
import six


UPDATE_MANAGER_COMMAND_PATH = 'UPDATE_MANAGER'

TIMEOUT_IN_SEC = 60
UPDATE_MANAGER_TIMEOUT_IN_SEC = 3
WRITE_BUFFER_SIZE = 16*1024


class Error(exceptions.Error):
  """Base exception for the installers module."""
  pass


class ComponentDownloadFailedError(Error):
  """Exception for when we cannot download a component for some reason."""

  def __init__(self, component_id, e):
    super(ComponentDownloadFailedError, self).__init__(
        'The component [{component_id}] failed to download.\n\n'.format(
            component_id=component_id) + six.text_type(e))


class URLFetchError(Error):
  """Exception for problems fetching via HTTP."""
  pass


class AuthenticationError(Error):
  """Exception for when the resource is protected by authentication."""

  def __init__(self, msg, e):
    super(AuthenticationError, self).__init__(msg + '\n\n' + six.text_type(e))


class UnsupportedSourceError(Error):
  """An exception when trying to install a component with an unknown source."""
  pass


def MakeRequest(url, command_path):
  """Gets the request object for the given URL using the requests library.

  If the URL is for cloud storage and we get a 403, this will try to load the
  active credentials and use them to authenticate the download.

  Args:
    url: str, the URL to download.
    command_path: str, the command path to include in the User-Agent header if
      the URL is HTTP.

  Raises:
    AuthenticationError: If this download requires authentication and there
      are no credentials or the credentials do not have access.

  Returns:
    requests.Response object
  """
  # pylint: disable=g-import-not-at-top
  from googlecloudsdk.core.credentials import store
  # pylint: enable=g-import-not-at-top
  if url.startswith(ComponentInstaller.GCS_BROWSER_DL_URL):
    url = url.replace(ComponentInstaller.GCS_BROWSER_DL_URL,
                      ComponentInstaller.GCS_API_DL_URL, 1)
  headers = {
      b'Cache-Control':
          b'no-cache',
      b'User-Agent':
          http_encoding.Encode(transport.MakeUserAgentString(command_path))
  }
  timeout = TIMEOUT_IN_SEC
  if command_path == UPDATE_MANAGER_COMMAND_PATH:
    timeout = UPDATE_MANAGER_TIMEOUT_IN_SEC

  try:
    return _RawRequest(url, headers=headers, timeout=timeout)
  except requests.exceptions.HTTPError as e:
    if e.response.status_code != 403 or not e.response.url.startswith(
        ComponentInstaller.GCS_API_DL_URL):
      raise e
    try:
      creds = store.LoadFreshCredential()
      creds.apply(headers)
    except creds_exceptions.Error as e:
      # If we fail here, it is because there are no active credentials or the
      # credentials are bad.
      raise AuthenticationError(
          'This component requires valid credentials to install.', e)
    try:
      # Retry the download using the credentials.
      return _RawRequest(url, headers=headers, timeout=timeout)
    except requests.exceptions.HTTPError as e:
      if e.response.status_code != 403:
        raise e
      # If we fail again with a 403, that means we used the credentials, but
      # they didn't have access to the resource.
      raise AuthenticationError(
          """\
Account [{account}] does not have permission to install this component.  Please
ensure that this account should have access or run:

$ gcloud config set account `ACCOUNT`

to choose another account.""".format(
    account=properties.VALUES.core.account.Get()), e)


def _RawRequest(*args, **kwargs):
  """Executes an HTTP request."""

  def RetryIf(exc_type, exc_value, unused_traceback, unused_state):
    return (exc_type == requests.exceptions.HTTPError and
            exc_value.response.status_code == 404)

  def StatusUpdate(unused_result, unused_state):
    log.debug('Retrying request...')

  retryer = retry.Retryer(
      max_retrials=3,
      exponential_sleep_multiplier=2,
      jitter_ms=100,
      status_update_func=StatusUpdate)
  try:
    return retryer.RetryOnException(
        _ExecuteRequestAndRaiseExceptions,
        args,
        kwargs,
        should_retry_if=RetryIf,
        sleep_ms=500)
  except retry.RetryException as e:
    # last_result is (return value, sys.exc_info)
    if e.last_result[1]:
      exceptions.reraise(e.last_result[1][1], tb=e.last_result[1][2])
    raise


def _ExecuteRequestAndRaiseExceptions(url, headers, timeout):
  """Executes an HTTP request using requests.

  Args:
    url: str, the url to download.
    headers: obj, the headers to include in the request.
    timeout: int, the timeout length for the request.

  Returns:
    A response object from the request.

  Raises:
    requests.exceptions.HTTPError in the case of a client or server error.
  """
  # pylint: disable=g-import-not-at-top
  from googlecloudsdk.core import requests as core_requests
  # pylint: enable=g-import-not-at-top
  requests_session = core_requests.GetSession()
  if url.startswith('file://'):
    requests_session.mount('file://', local_file_adapter.LocalFileAdapter())
  response = requests_session.get(
      url, headers=headers, timeout=timeout, stream=True)
  response.raise_for_status()
  return response


def DownloadTar(url, download_dir, progress_callback=None,
                command_path='unknown'):
  """Download the given tar file.

  Args:
    url: str, The URL to download.
    download_dir: str, The path to put the temporary download file into.
    progress_callback: f(float), A function to call with the fraction of
      completeness.
    command_path: the command path to include in the User-Agent header if the
      URL is HTTP

  Returns:
    str, The path of the downloaded tar file.

  Raises:
    URLFetchError: If there is a problem fetching the given URL.
  """
  progress_callback = progress_callback or console_io.DefaultProgressBarCallback
  if not os.path.exists(download_dir):
    file_utils.MakeDir(download_dir)
  download_file_path = os.path.join(download_dir, os.path.basename(url))
  if os.path.exists(download_file_path):
    os.remove(download_file_path)

  try:
    response = MakeRequest(url, command_path)
    with file_utils.BinaryFileWriter(download_file_path) as fp:
      total_written = 0
      total_size = len(response.content)
      for chunk in response.iter_content(chunk_size=WRITE_BUFFER_SIZE):
        fp.write(chunk)
        total_written += len(chunk)
        progress_callback(total_written / total_size)
    progress_callback(1)
  except (requests.exceptions.HTTPError, OSError) as e:
    raise URLFetchError(e)

  return download_file_path


def ExtractTar(downloaded_archive, extract_dir, progress_callback=None):
  """Extracts the given archive.

  Args:
    downloaded_archive: str, The path to the archive downloaded previously.
    extract_dir: str, The path to extract the tar into.
    progress_callback: f(float), A function to call with the fraction of
      completeness.

  Returns:
    [str], The files that were extracted from the tar file.
  """
  progress_callback = progress_callback or console_io.DefaultProgressBarCallback
  if not os.path.exists(extract_dir):
    file_utils.MakeDir(extract_dir)

  with tarfile.open(name=downloaded_archive) as tar:
    members = tar.getmembers()
    total_files = len(members)

    files = []
    for num, member in enumerate(members, start=1):
      files.append(member.name + '/' if member.isdir() else member.name)
      tar.extract(member, extract_dir)
      full_path = os.path.join(extract_dir, member.name)
      # Ensure read-and-write permission for all files
      if os.path.isfile(full_path) and not os.access(full_path, os.W_OK):
        os.chmod(full_path, stat.S_IWUSR|stat.S_IREAD)
      progress_callback(num / total_files)

    progress_callback(1)

  os.remove(downloaded_archive)
  return files


class ComponentInstaller(object):
  """A class to install Cloud SDK components of different source types."""

  DOWNLOAD_DIR_NAME = '.download'
  # This is the URL prefix for files that require authentication which triggers
  # browser based cookie authentication.  We will use URLs with this pattern,
  # but we never want to actually try to download from here because we are not
  # using a browser and it will return the html of the sign in page.
  GCS_BROWSER_DL_URL = 'https://storage.cloud.google.com/'
  # All files accessible though the above prefix, are accessible through this
  # prefix when you insert authentication data into the http headers.  If no
  # auth is required, you can also use this URL directly with no headers.
  GCS_API_DL_URL = 'https://storage.googleapis.com/'

  def __init__(self, sdk_root, state_directory):
    """Initializes an installer for components of different source types.

    Args:
      sdk_root:  str, The path to the root directory of all Cloud SDK files.
      state_directory: str, The path to the directory where the local state is
        stored.
    """
    self.__sdk_root = sdk_root
    self.__state_directory = state_directory
    self.__download_directory = os.path.join(
        self.__state_directory, ComponentInstaller.DOWNLOAD_DIR_NAME)

  def Download(self, component, progress_callback=None, command_path='unknown'):
    """Downloads the given component for whatever source type it has.

    Args:
      component: schemas.Component, The component from the snapshot to install.
      progress_callback: f(float), A function to call with the fraction of
        completeness.
      command_path: the command path to include in the User-Agent header if the
        URL is HTTP

    Returns:
      Optional[str], The path of the downloaded archive, or None if the
        component has no actual sources.

    Raises:
      UnsupportedSourceError: If the component data source is of an unknown
        type.
      URLFetchError: If the URL associated with the component data source
        cannot be fetched.
    """
    data = component.data

    if not data:
      # No source data, just a configuration component
      return None

    if data.type == 'tar':
      return self._DownloadTar(
          component, progress_callback=progress_callback,
          command_path=command_path)

    raise UnsupportedSourceError(
        'tar is the only supported source format [{datatype}]'.format(
            datatype=data.type))

  def Extract(self, downloaded_archive, progress_callback=None):
    """Extracts the archive previously downloaded from self.Download().

    Args:
      downloaded_archive: Optional[str], The path to the archive downloaded
        previously.
      progress_callback: f(float), A function to call with the fraction of
        completeness.

    Returns:
      list of str, The files that were installed or [] if nothing was installed.
    """
    if downloaded_archive is None:
      # From a component with no actual data/sources; nothing to extract.
      return []

    return ExtractTar(
        downloaded_archive, self.__sdk_root,
        progress_callback=progress_callback)

  def _DownloadTar(self, component, progress_callback=None,
                   command_path='unknown'):
    """Download implementation for a component with source in a .tar.gz.

    Downloads the .tar for the component and returns its path.

    Args:
      component: schemas.Component, The component to install.
      progress_callback: f(float), A function to call with the fraction of
        completeness.
      command_path: the command path to include in the User-Agent header if the
        URL is HTTP

    Returns:
      Optional[str], The path of the downloaded archive, or None if the
        component has no actual sources.

    Raises:
      ValueError: If the source URL for the tar file is relative, but there is
        no location information associated with the snapshot we are installing
        from.
      URLFetchError: If there is a problem fetching the component's URL.
    """
    url = component.data.source
    if not url:
      # not all components must have real source
      return None

    if not re.search(r'^\w+://', url):
      raise ValueError('Cannot install component [{0}] from a relative path '
                       'because the base URL of the snapshot is not defined.'
                       .format(component.id))

    try:
      return DownloadTar(
          url, self.__download_directory, progress_callback=progress_callback,
          command_path=command_path)
    except (URLFetchError, AuthenticationError) as e:
      raise ComponentDownloadFailedError(component.id, e)
