# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Utilities for interacting with Google Cloud Storage.

This makes use of both the Cloud Storage API as well as the gsutil command-line
tool. We use the command-line tool for syncing the contents of buckets as well
as listing the contents. We use the API for checking ACLs.
"""

import argparse
import mimetypes
import os
import re

from apitools.base.py import exceptions as api_exceptions
from apitools.base.py import list_pager
from apitools.base.py import transfer

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import apis as core_apis
from googlecloudsdk.core import config
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_attr_os
from googlecloudsdk.core.credentials import http
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import platforms


GSUTIL_BUCKET_REGEX = r'^gs://.*$'

LOG_OUTPUT_BEGIN = ' REMOTE BUILD OUTPUT '
LOG_OUTPUT_INCOMPLETE = ' (possibly incomplete) '
OUTPUT_LINE_CHAR = '-'
GCS_URL_PATTERN = (
    'https://www.googleapis.com/storage/v1/b/{bucket}/o/{obj}?alt=media')

STORAGE_MESSAGES = core_apis.GetMessagesModule('storage', 'v1')


class Error(Exception):
  """Base exception for cloud_storage module."""


class UploadError(Error):
  """Error raised when there are problems uploading files."""


class BucketReference(object):
  """A wrapper class to make working with GCS bucket names easier."""

  def __init__(self, bucket_url):
    """Constructor for BucketReference.

    Args:
      bucket_url: str, The bucket to reference. Format: gs://<bucket_name>
    """
    self._bucket_url = bucket_url
    bucket_name = bucket_url.replace('gs://', '').rstrip('/')
    self._ref = resources.Parse(bucket_name, collection='storage.buckets')

  @property
  def bucket(self):
    return self._ref.bucket

  def ToAppEngineApiReference(self):
    return 'https://storage.googleapis.com/{0}'.format(self._ref.bucket)

  def ToBucketUrl(self):
    return self._bucket_url


def _GetMimetype(local_path):
  mime_type, _ = mimetypes.guess_type(local_path)
  return mime_type or 'application/octet-stream'


def _GetFileSize(local_path):
  try:
    return os.path.getsize(local_path)
  except os.error:
    raise exceptions.BadFileException('[{0}] not found or not accessible'
                                      .format(local_path))


def CopyFileToGCS(bucket_ref, local_path, target_path, storage_client):
  """Upload a file to the GCS results bucket using the storage API.

  Args:
    bucket_ref: The user-specified bucket to upload to.
    local_path: str, the path of the file to upload. File must be on the local
      filesystem.
    target_path: str, the path of the file on GCS.
    storage_client: A storage_v1 client object.

  Raises:
    BadFileException if the file upload is not successful.
  """
  file_size = _GetFileSize(local_path)
  src_obj = STORAGE_MESSAGES.Object(size=file_size)
  mime_type = _GetMimetype(local_path)

  upload = transfer.Upload.FromFile(local_path, mime_type=mime_type)
  insert_req = STORAGE_MESSAGES.StorageObjectsInsertRequest(
      bucket=bucket_ref.bucket,
      name=target_path,
      object=src_obj)

  log.info('Uploading [{f}] to [{gcs}]'.format(f=local_path, gcs=target_path))
  try:
    response = storage_client.objects.Insert(insert_req, upload=upload)
  except api_exceptions.HttpError as err:
    raise exceptions.BadFileException(
        'Could not copy [{f}] to [{gcs}] {e}. Please retry.'
        .format(f=local_path, gcs=target_path, e=err))

  if response.size != file_size:
    log.debug('Response size: {0} bytes, but local file is {1} bytes.'.format(
        response.size, file_size))
    raise exceptions.BadFileException(
        'Cloud storage upload failure. Uploaded file does not match local '
        'file: {0}. Please retry.'.format(local_path))


def ListBucket(bucket_ref, client):
  """Lists the contents of a cloud storage bucket.

  Args:
    bucket_ref: The reference to the bucket.
    client: A storage_v1 client.
  Returns:
    A set of names of items.
  """
  request = STORAGE_MESSAGES.StorageObjectsListRequest(bucket=bucket_ref.bucket)
  items = set()
  try:
    # batch_size=None gives us the API default
    for item in list_pager.YieldFromList(client.objects, request,
                                         batch_size=None):
      items.add(item.name)
  except api_exceptions.HttpError as e:
    # TODO(user): Refactor the exception handling before treating this as a
    # shared library.
    raise UploadError('Error uploading files: {e}'.format(e=e))

  return items


def GcsBucketArgument(string):
  """Validates that the argument is a reference to a GCS bucket."""
  if not re.match(GSUTIL_BUCKET_REGEX, string):
    raise argparse.ArgumentTypeError(('Must be a valid Google Cloud Cloud '
                                      'Storage bucket of the form '
                                      '[gs://somebucket]'))

  return string


def _GetGsutilPath():
  """Determines the path to the gsutil binary."""
  sdk_bin_path = config.Paths().sdk_bin_path
  if not sdk_bin_path:
    # Check if gsutil is located on the PATH.
    gsutil_path = file_utils.FindExecutableOnPath('gsutil')
    if gsutil_path:
      log.debug('Using gsutil found at [{path}]'.format(path=gsutil_path))
      return gsutil_path
    else:
      raise exceptions.ToolException(('A SDK root could not be found. Please '
                                      'check your installation.'))
  return os.path.join(sdk_bin_path, 'gsutil')


def _RunGsutilCommand(command_name, command_arg_str, run_concurrent=False):
  """Runs the specified gsutil command and returns the command's exit code.

  Args:
    command_name: The gsutil command to run.
    command_arg_str: Arguments to pass to the command.
    run_concurrent: Whether concurrent uploads should be enabled while running
      the command.

  Returns:
    The exit code of the call to the gsutil command.
  """
  command_path = _GetGsutilPath()

  if run_concurrent:
    command_args = ['-m', command_name]
  else:
    command_args = [command_name]

  command_args += command_arg_str.split(' ')

  if platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS:
    gsutil_args = execution_utils.ArgsForCMDTool(command_path + '.cmd',
                                                 *command_args)
  else:
    gsutil_args = execution_utils.ArgsForExecutableTool(command_path,
                                                        *command_args)
  log.debug('Running command: [{args}]]'.format(args=' '.join(gsutil_args)))
  return execution_utils.Exec(gsutil_args, no_exit=True,
                              pipe_output_through_logger=True,
                              file_only_logger=True)


def Rsync(source_dir, dest_dir, exclude_pattern=None):
  """Copies files from the specified file system directory to a GCS bucket.

  Args:
    source_dir: The source directory for the rsync.
    dest_dir: The destination directory for the rsync.
    exclude_pattern: A string representation of a Python regular expression.
      If provided, this is passed as the '-x' argument for the rsync command.

  Returns:
    The exit code of the call to "gsutil rsync".
  """

  # -m Allows concurrent uploads
  # -c Causes gsutil to compute checksums when comparing files.
  # -R recursively copy all files
  # -x Ignore files using the specified pattern.
  command_arg_str = '-R -c '
  if exclude_pattern:
    command_arg_str += '-x \'{0}\' '.format(exclude_pattern)

  command_arg_str += ' '.join([source_dir, dest_dir])
  return _RunGsutilCommand('rsync', command_arg_str, run_concurrent=True)


class LogTailer(object):
  """Helper class to tail a GCS logfile, printing content as available."""

  def __init__(self, bucket, obj, out=log.status, url_pattern=GCS_URL_PATTERN):
    self.http = http.Http()
    self.url = url_pattern.format(bucket=bucket, obj=obj)
    log.debug('GCS logfile url is ' + self.url)
    # position in the file being read
    self.cursor = 0
    self.out = out

  def Poll(self, is_last=False):
    """Poll the GCS object and print any new bytes to the console.

    Args:
      is_last: True if this is the last poll operation.

    Raises:
      api_exceptions.HttpError: if there is trouble connecting to GCS.
    """
    (res, body) = self.http.request(
        self.url, method='GET',
        headers={'Range': 'bytes={0}-'.format(self.cursor)})

    if res.status == 404:  # Not Found
      # Logfile hasn't been written yet (ie, build hasn't started).
      log.debug('Reading GCS logfile: 404 (no log yet; keep polling)')
      return

    if res.status == 416:  # Requested Range Not Satisfiable
      # We have consumed all available data. We'll get this a lot as we poll.
      log.debug('Reading GCS logfile: 416 (no new content; keep polling)')
      if is_last:
        self._PrintLastLine()
      return

    if res.status == 206 or res.status == 200:  # Partial Content
      # New content available. Print it!
      log.debug('Reading GCS logfile: {code} (read {count} bytes)'.format(
          code=res.status,
          count=len(body)))
      if self.cursor == 0:
        self._PrintFirstLine()
      self.cursor += len(body)
      self._PrintLogLine(body.rstrip('\n'))
      if is_last:
        self._PrintLastLine()
      return

    # For 429/503, there isn't much to do other than retry on the next poll.
    # If we get a 429 after the build has completed, the user may get incomplete
    # logs. This is expected to be rare enough to not justify building a complex
    # exponential retry system.
    if res.status == 429:  # Too Many Requests
      log.warning('Reading GCS logfile: 429 (server is throttling us)')
      if is_last:
        self._PrintLastLine(LOG_OUTPUT_INCOMPLETE)
      return

    if res.status >= 500 and res.status < 600:  # Server Error
      log.warning('Reading GCS logfile: got {0}, retrying'.format(res.status))
      if is_last:
        self._PrintLastLine(LOG_OUTPUT_INCOMPLETE)
      return

    # Default: any other codes are treated as errors.
    raise api_exceptions.HttpError(res, body, self.url)

  def _PrintLogLine(self, text):
    """Testing Hook: This method enables better verification of output."""
    self.out.Print(text)

  def _PrintFirstLine(self):
    width, _ = console_attr_os.GetTermSize()
    self._PrintLogLine(LOG_OUTPUT_BEGIN.center(width, OUTPUT_LINE_CHAR))

  def _PrintLastLine(self, msg=''):
    width, _ = console_attr_os.GetTermSize()
    # We print an extra blank visually separating the log from other output.
    self._PrintLogLine(msg.center(width, OUTPUT_LINE_CHAR) + '\n')
