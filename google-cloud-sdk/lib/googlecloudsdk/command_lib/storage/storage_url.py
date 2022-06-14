# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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

"""File and Cloud URL representation classes."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import enum
import os
import stat

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.core import log
from googlecloudsdk.core.util import platforms

import six
from six.moves import urllib


TEMPORARY_FILE_SUFFIX = '_.gstmp'


class ProviderPrefix(enum.Enum):
  """Provider prefix strings for storage URLs."""
  FILE = 'file'
  GCS = 'gs'
  HTTP = 'http'
  HTTPS = 'https'
  POSIX = 'posix'
  S3 = 's3'


VALID_CLOUD_SCHEMES = frozenset([ProviderPrefix.GCS, ProviderPrefix.S3])
VALID_HTTP_SCHEMES = frozenset([ProviderPrefix.HTTP, ProviderPrefix.HTTPS])
VALID_SCHEMES = frozenset([scheme.value for scheme in ProviderPrefix])
CLOUD_URL_DELIMITER = '/'
AZURE_DOMAIN = 'blob.core.windows.net'


class StorageUrl(six.with_metaclass(abc.ABCMeta)):
  """Abstract base class for file and Cloud Storage URLs."""

  @abc.abstractproperty
  def delimiter(self):
    """Returns the delimiter for the url."""

  @property
  def is_pipe(self):
    """Returns if URL points to a named pipe (FIFO) or stream."""
    raise NotImplementedError

  @abc.abstractproperty
  def url_string(self):
    """Returns the string representation of the instance."""

  @abc.abstractproperty
  def versionless_url_string(self):
    """Returns the string representation of the instance without the version."""

  def join(self, part):
    """Appends part at the end of url_string.

    The join is performed in 3 steps:
    1) Strip off one delimiter (if present) from the right of the url_string.
    2) Strip off one delimiter (if present) from the left of the part.
    3) Join the two strings with delimiter in between.

    Note that the behavior is slight different from os.path.join for cases
    where the part starts with a delimiter.
    os.path.join('a/b', '/c') => '/c'
    But this join method will return a StorageUrl with url_string as 'a/b/c'.
    This is done to be consistent across FileUrl and CloudUrl.

    The delimiter of the instance will be used. So, if you are trying to append
    a Windows path to a CloudUrl instance, you have to make sure to convert
    the Windows path before passing it to this method.

    Args:
      part (str): The part that needs to be appended.

    Returns:
      A StorageUrl instance.
    """
    left = rstrip_one_delimiter(self.versionless_url_string, self.delimiter)
    right = part[1:] if part.startswith(self.delimiter) else part
    new_url_string = '{}{}{}'.format(left, self.delimiter, right)
    return storage_url_from_string(new_url_string)

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return self.url_string == other.url_string

  def __hash__(self):
    return hash(self.url_string)

  def __str__(self):
    return self.url_string


class FileUrl(StorageUrl):
  """File URL class providing parsing and convenience methods.

  This class assists with usage and manipulation of an
  (optionally wildcarded) file URL string.  Depending on the string
  contents, this class represents one or more directories or files.

  Attributes:
    scheme (ProviderPrefix): This will always be "file" for FileUrl.
    bucket_name (str): None for FileUrl.
    object_name (str): The file/directory path.
    generation (str): None for FileUrl.
  """

  def __init__(self, url_string):
    """Initialize FileUrl instance.

    Args:
      url_string (str): The string representing the filepath.
    """
    super(FileUrl, self).__init__()
    self.scheme = ProviderPrefix.FILE
    self.bucket_name = None
    self.generation = None

    if url_string.startswith('file://'):
      filename = url_string[len('file://'):]
    else:
      filename = url_string

    # On Windows, the pathname component separator is "\" instead of "/". If we
    # find an occurrence of "/", replace it with "\" so that other logic can
    # rely on being able to split pathname components on `os.sep`.
    if platforms.OperatingSystem.IsWindows():
      self.object_name = filename.replace('/', os.sep)
    else:
      self.object_name = filename

    self._warn_if_unsupported_double_wildcard()

  def _warn_if_unsupported_double_wildcard(self):
    """Log warning if ** use may lead to undefined results."""
    # Accepted 'url_string' values with '**', where '^' = start, and '$' = end.
    # - ^**$
    # - ^**/
    # - /**$
    # - /**/
    if not self.object_name:
      return
    delimiter_bounded_url = self.delimiter + self.object_name + self.delimiter
    split_url = delimiter_bounded_url.split(
        '{delim}**{delim}'.format(delim=self.delimiter))
    removed_correct_double_wildcards_url_string = ''.join(split_url)
    if '**' in removed_correct_double_wildcards_url_string:
      # Found a center '**' not in the format '/**/'.
      log.warning(
          '** behavior is undefined if directly preceeded or followed by'
          ' with characters other than / in the cloud and {} locally.'.format(
              os.sep))

  @property
  def delimiter(self):
    """Returns the pathname separator character used by the OS."""
    return os.sep

  @property
  def is_stream(self):
    """Returns True when stdin is requested."""
    return self.object_name == '-'

  @property
  def is_pipe(self):
    """Returns if URL points to a named pipe (FIFO) or stream."""
    return self.is_stream or (os.path.exists(self.object_name) and
                              stat.S_ISFIFO(os.stat(self.object_name).st_mode))

  def exists(self):
    """Returns True if the file/directory exists."""
    return os.path.exists(self.object_name)

  def isdir(self):
    """Returns True if the path represents a directory."""
    return os.path.isdir(self.object_name)

  @property
  def url_string(self):
    """Returns the string representation of the instance."""
    return '%s://%s' % (self.scheme.value, self.object_name)

  @property
  def versionless_url_string(self):
    """Returns the string representation of the instance without the version."""
    return self.url_string


class PosixFileSystemUrl(StorageUrl):
  """URL class representing local and external POSIX file systems.

  *Intended for transfer component.*

  This class is different from FileUrl in many ways:
  1) It supports only POSIX file systems (not Windows).
  2) It can represent file systems on external machines.
  3) It cannot run checks on the address of the URL like "exists" or "is_pipe"
     because the URL may point to a different machine.
  4) The class is intended for use in "agent transfers". This is when a
     Transfer Service customer installs agents on one machine or multiple and
     uses the agent software to upload and download files on the machine(s).

  We implement this class in the "storage" component for convenience and
  because the "storage" and "transfer" products are tightly coupled.

  Attributes:
    scheme (ProviderPrefix): This will always be "posix" for PosixFileSystemUrl.
    bucket_name (None): N/A
    object_name (str): The file/directory path.
    generation (None): N/A
  """

  def __init__(self, url_string):
    """Initialize PosixFileSystemUrl instance.

    Args:
      url_string (str): Local or external POSIX file path.
    """
    super(PosixFileSystemUrl, self).__init__()
    self.scheme = ProviderPrefix.POSIX
    self.bucket_name = None
    # Use object_name to represent a schemeless root URL.
    self.object_name = url_string[len(ProviderPrefix.POSIX.value + '://'):]
    if not self.object_name.startswith(self.delimiter):
      log.warning(
          'POSIX URLs typically start at the root directory. Did you mean:'
          ' {}://{}{}'.format(self.scheme.value, self.delimiter,
                              self.object_name))

    self.generation = None

  @property
  def delimiter(self):
    """Returns the pathname separator character used by POSIX."""
    return '/'

  @property
  def url_string(self):
    """Returns the string representation of the instance."""
    return '%s://%s' % (self.scheme.value, self.object_name)

  @property
  def versionless_url_string(self):
    """Returns the string representation of the instance without the version."""
    return self.url_string


class CloudUrl(StorageUrl):
  """Cloud URL class providing parsing and convenience methods.

    This class assists with usage and manipulation of an
    (optionally wildcarded) cloud URL string.  Depending on the string
    contents, this class represents a provider, bucket(s), or object(s).

    This class operates only on strings.  No cloud storage API calls are
    made from this class.

    Attributes:
      scheme (ProviderPrefix): The cloud provider.
      bucket_name (str): The bucket name if url represents an object or bucket.
      object_name (str): The object name if url represents an object or prefix.
      generation (str): The generation number if present.
  """
  CLOUD_URL_DELIM = '/'

  def __init__(self, scheme, bucket_name=None, object_name=None,
               generation=None):
    super(CloudUrl, self).__init__()
    self.scheme = scheme if scheme else None
    self.bucket_name = bucket_name if bucket_name else None
    self.object_name = object_name if object_name else None
    self.generation = str(generation) if generation else None
    self._validate_scheme()
    self._validate_object_name()

  @classmethod
  def from_url_string(cls, url_string):
    """Parse the url string and return the storage url object.

    Args:
      url_string (str): Cloud storage url of the form gs://bucket/object

    Returns:
      CloudUrl object

    Raises:
      InvalidUrlError: Raised if the url_string is not a valid cloud url.
    """
    scheme = _get_scheme_from_url_string(url_string)

    # gs://a/b/c/d#num => a/b/c/d#num
    schemeless_url_string = url_string[len(scheme.value + '://'):]

    if schemeless_url_string.startswith('/'):
      raise errors.InvalidUrlError(
          'Cloud URL scheme should be followed by colon and two slashes: "://".'
          ' Found: "{}"'.format(url_string))

    # a/b/c/d#num => a, b/c/d#num
    bucket_name, _, object_name = schemeless_url_string.partition(
        CLOUD_URL_DELIMITER)

    # b/c/d#num => b/c/d, num
    object_name, _, generation = object_name.partition('#')

    return cls(scheme, bucket_name, object_name, generation)

  def _validate_scheme(self):
    if self.scheme not in VALID_CLOUD_SCHEMES:
      raise errors.InvalidUrlError('Unrecognized scheme "%s"' % self.scheme)

  def _validate_object_name(self):
    if self.object_name == '.' or self.object_name == '..':
      raise errors.InvalidUrlError('%s is an invalid root-level object name.' %
                                   self.object_name)

  @property
  def url_string(self):
    url_str = self.versionless_url_string
    if self.generation:
      url_str += '#%s' % self.generation
    return url_str

  @property
  def versionless_url_string(self):
    if self.is_provider():
      return '%s://' % self.scheme.value
    elif self.is_bucket():
      return '%s://%s/' % (self.scheme.value, self.bucket_name)
    return '%s://%s/%s' % (self.scheme.value, self.bucket_name,
                           self.object_name)

  @property
  def delimiter(self):
    return self.CLOUD_URL_DELIM

  def is_bucket(self):
    return bool(self.bucket_name and not self.object_name)

  def is_object(self):
    return bool(self.bucket_name and self.object_name)

  def is_provider(self):
    return bool(self.scheme and not self.bucket_name)


class AzureUrl(CloudUrl):
  """CloudUrl subclass for Azure's unique blob storage URL structure.

    Attributes:
      scheme (ProviderPrefix): AZURE (http) or AZURE_TLS (https).
      bucket_name (str|None): Storage container name in URL.
      object_name (str|None): Storage object name in URL.
      generation (str|None): Equivalent to Azure 'versionId'. Datetime string.
      snapshot (str|None): Similar to 'versionId'. URL parameter used to capture
        a specific version of a storage object. Datetime string.
      account (str): Account owning storage resource.
  """

  def __init__(self,
               scheme,
               bucket_name=None,
               object_name=None,
               generation=None,
               snapshot=None,
               account=None):
    super(AzureUrl, self).__init__(scheme, bucket_name, object_name, generation)
    self.snapshot = snapshot if snapshot else None

    if not account:
      raise errors.InvalidUrlError('Azure URLs must contain an account name.')
    self.account = account

  @classmethod
  def from_url_string(cls, url_string):
    """Parse the url string and return the storage URL object.

    Args:
      url_string (str): Azure storage URL of the form:
        http://account.blob.core.windows.net/container/blob

    Returns:
      AzureUrl object

    Raises:
      InvalidUrlError: Raised if the url_string is not a valid cloud URL.
    """
    scheme = _get_scheme_from_url_string(url_string)

    AzureUrl.validate_url_string(url_string, scheme)

    # http://account.blob.core.windows.net/container/blob?snapshot=<DateTime>
    # &versionId=<DateTime>
    # -> account.blob.core.windows.net/container/blob?snapshot=<DateTime>
    # &versionId=<DateTime>
    schemeless_url_string = url_string[len(scheme.value + '://'):]
    # account.blob.core.windows.net/container/blob?snapshot=<DateTime>
    # &versionId=<DateTime>
    # -> account.blob.core.windows.net,
    # container/blob?snapshot=<DateTime>&versionId=<DateTime>
    hostname, _, path_and_params = schemeless_url_string.partition(
        CLOUD_URL_DELIMITER)
    # account.blob.core.windows.net -> account
    account, _, _ = hostname.partition('.')
    # container/blob?snapshot=<DateTime>&versionId=<DateTime>
    # -> container, blob?snapshot=<DateTime>&versionId=<DateTime>
    container, _, blob_and_params = path_and_params.partition(
        CLOUD_URL_DELIMITER)
    # blob?snapshot=<DateTime>&versionId=<DateTime>
    # -> blob, snapshot=<DateTime>&versionId=<DateTime>
    blob, _, params = blob_and_params.partition('?')
    # snapshot=<DateTime>&versionId=<DateTime>
    # -> {'snapshot': <DateTime>, 'versionId': <DateTime>}
    params_dict = urllib.parse.parse_qs(params)

    return cls(
        scheme,
        bucket_name=container,
        object_name=blob,
        generation=params_dict['versionId'][0]
        if 'versionId' in params_dict else None,
        snapshot=params_dict['snapshot'][0]
        if 'snapshot' in params_dict else None,
        account=account)

  @classmethod
  def is_valid_scheme(cls, scheme):
    return scheme in VALID_HTTP_SCHEMES

  def _validate_scheme(self):
    if not AzureUrl.is_valid_scheme(self.scheme):
      raise errors.InvalidUrlError('Invalid Azure scheme "{}"'.format(
          self.scheme))

  @classmethod
  def validate_url_string(cls, url_string, scheme):
    AzureUrl.is_valid_scheme(scheme)
    if not (AZURE_DOMAIN in url_string and AzureUrl.is_valid_scheme(scheme)):
      raise errors.InvalidUrlError('Invalid Azure URL: "{}"'.format(url_string))

  @property
  def url_string(self):
    url_parts = list(urllib.parse.urlsplit(self.versionless_url_string))
    url_parameters = {}
    if self.generation:
      url_parameters['versionId'] = self.generation
    if self.snapshot:
      url_parameters['snapshot'] = self.snapshot
    url_parts[3] = urllib.parse.urlencode(url_parameters)

    return urllib.parse.urlunsplit(url_parts)

  @property
  def versionless_url_string(self):
    if self.is_provider():
      return '{}://{}.{}'.format(self.scheme.value, self.account, AZURE_DOMAIN)
    elif self.is_bucket():
      return '{}://{}.{}/{}'.format(self.scheme.value, self.account,
                                    AZURE_DOMAIN, self.bucket_name)
    return '{}://{}.{}/{}/{}'.format(self.scheme.value, self.account,
                                     AZURE_DOMAIN, self.bucket_name,
                                     self.object_name)


def _get_scheme_from_url_string(url_string):
  """Returns scheme component of a URL string."""
  end_scheme_idx = url_string.find('://')
  if end_scheme_idx == -1:
    # File is the default scheme.
    return ProviderPrefix.FILE
  else:
    prefix_string = url_string[0:end_scheme_idx].lower()
    if prefix_string not in VALID_SCHEMES:
      raise errors.InvalidUrlError(
          'Unrecognized scheme "{}"'.format(prefix_string))
    return ProviderPrefix(prefix_string)


def storage_url_from_string(url_string):
  """Static factory function for creating a StorageUrl from a string.

  Args:
    url_string (str): Cloud url or local filepath.

  Returns:
     StorageUrl object.

  Raises:
    InvalidUrlError: Unrecognized URL scheme.
  """
  scheme = _get_scheme_from_url_string(url_string)
  if scheme == ProviderPrefix.FILE:
    return FileUrl(url_string)
  if scheme == ProviderPrefix.POSIX:
    return PosixFileSystemUrl(url_string)
  if scheme in VALID_HTTP_SCHEMES:
    # Azure's scheme breaks from other clouds.
    return AzureUrl.from_url_string(url_string)
  if scheme in VALID_CLOUD_SCHEMES:
    return CloudUrl.from_url_string(url_string)
  raise errors.InvalidUrlError('Unrecognized URL scheme.')


def rstrip_one_delimiter(string, delimiter=CloudUrl.CLOUD_URL_DELIM):
  """Strip one delimiter char from the end.

  Args:
    string (str): String on which the action needs to be performed.
    delimiter (str): A delimiter char.

  Returns:
    str: String with trailing delimiter removed.
  """
  if string.endswith(delimiter):
    return string[:-len(delimiter)]
  return string


def switch_scheme(original_url, new_scheme):
  """Returns best-effort new StorageUrl based on original with new scheme.

  This relies strongly on "storage_url_from_string" and will probably fail
  for unusual formats like Azure URL. However, delimiter replacement is
  handled for cases like converting Windows to cloud URLs.

  Ignores versioning info embedded in URLs because each URL type tends to have
  non-translatable syntax for its versions.

  Args:
    original_url (StorageUrl): URL to convert.
    new_scheme (ProviderPrefix): Scheme to update URL with. probably fail or
      have unexpected results because URL formats tend to have non-translatable
      versioning syntax.

  Returns:
    StorageUrl with updated scheme and best-effort transformation.
  """
  _, old_url_string_no_scheme = original_url.versionless_url_string.split('://')
  unprocessed_new_url = storage_url_from_string('{}://{}'.format(
      new_scheme.value, old_url_string_no_scheme))

  if original_url.delimiter == unprocessed_new_url.delimiter:
    return unprocessed_new_url

  old_url_string_no_scheme_correct_delimiter = old_url_string_no_scheme.replace(
      original_url.delimiter, unprocessed_new_url.delimiter)
  return storage_url_from_string('{}://{}'.format(
      new_scheme.value, old_url_string_no_scheme_correct_delimiter))
