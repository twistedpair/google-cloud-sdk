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

"""Utilities for interacting with Google Cloud Storage."""

import argparse
import os
import re
import string

from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import config
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import platforms


GSUTIL_BUCKET_PREFIX = 'gs://'
GSUTIL_OBJECT_REGEX = r'^(?P<bucket>gs://[^/]+)/(?P<object>.+)'
GSUTIL_BUCKET_REGEX = r'^(?P<bucket>gs://[^/]+)/?'


LOG_OUTPUT_BEGIN = ' REMOTE BUILD OUTPUT '
LOG_OUTPUT_INCOMPLETE = ' (possibly incomplete) '
OUTPUT_LINE_CHAR = '-'
GCS_URL_PATTERN = (
    'https://www.googleapis.com/storage/v1/b/{bucket}/o/{obj}?alt=media')


class InvalidNameError(ValueError):
  """Error indicating that a given name is invalid."""

  def __init__(self, name, reason):
    super(InvalidNameError, self).__init__(
        ('Invalid {type} name [{name}]: {reason}\n\n'
         'See {url} for details.').format(name=name, reason=reason,
                                          type=self.TYPE, url=self.URL))


class InvalidBucketNameError(InvalidNameError):
  """Error indicating that a given bucket name is invalid."""
  TYPE = 'bucket'
  URL = 'https://cloud.google.com/storage/docs/naming#requirements'


class InvalidObjectNameError(InvalidNameError):
  """Error indicating that a given object name is invalid."""
  TYPE = 'object'
  URL = 'https://cloud.google.com/storage/docs/naming#objectnames'


VALID_BUCKET_CHARS_MESSAGE = """\
Bucket names must contain only lowercase letters, numbers, dashes (-), \
underscores (_), and dots (.)."""
VALID_BUCKET_START_END_MESSAGE = """\
Bucket names must start and end with a number or letter."""
VALID_BUCKET_LENGTH_MESSAGE = """\
Bucket names must contain 3 to 63 characters. \
Names containing dots can contain up to 222 characters, but each \
dot-separated component can be no longer than 63 characters."""
VALID_BUCKET_DOTTED_DECIMAL_MESSAGE = """\
Bucket names cannot be represented as an IP address in dotted-decimal \
notation (for example, 192.168.5.4)."""


VALID_OBJECT_LENGTH_MESSAGE = """\
Object names can contain any sequence of valid Unicode characters, \
of length 1-1024 bytes when UTF-8 encoded."""
VALID_OBJECT_CHARS_MESSAGE = """\
Object names must not contain Carriage Return or Line Feed characters."""


def _ValidateBucketName(name):
  """Validate the given bucket name according to the naming requirements.

  See https://cloud.google.com/storage/docs/naming#requirements

  Args:
    name: the name of the bucket, not including 'gs://'

  Raises:
    InvalidBucketNameError: if the given bucket name is invalid
  """
  components = name.split('.')
  if not (3 <= len(name) <= 222) or any(len(c) > 63 for c in components):
    raise InvalidBucketNameError(name, VALID_BUCKET_LENGTH_MESSAGE)

  if set(name) - set(string.ascii_lowercase + string.digits + '-_.'):
    raise InvalidBucketNameError(name, VALID_BUCKET_CHARS_MESSAGE)

  if set(name[0] + name[-1]) - set(string.ascii_lowercase + string.digits):
    raise InvalidBucketNameError(name, VALID_BUCKET_START_END_MESSAGE)

  if len(components) == 4 and ''.join(components).isdigit():
    raise InvalidBucketNameError(name, VALID_BUCKET_DOTTED_DECIMAL_MESSAGE)

  # Not validating the following guidelines, since Google can create such
  # buckets and they may be read from:
  # - Bucket names cannot begin with the "goog" prefix.
  # - Bucket names cannot contain "google" or close misspellings of "google".

  # Not validating the following guideline, because it seems to be a guideline
  # and not a requirement:
  # - Also, for DNS compliance and future compatibility, you should not use
  #   underscores (_) or have a period adjacent to another period or dash. For
  #   example, ".." or "-." or ".-" are not valid in DNS names.


def _ValidateBucketUrl(url):
  # These are things that cause unhelpful error messages during parsing, so we
  # check for them here.
  if url.startswith(GSUTIL_BUCKET_PREFIX):
    name = url[len(GSUTIL_BUCKET_PREFIX):]
  else:
    name = url
  _ValidateBucketName(name.rstrip('/'))


class BucketReference(object):
  """A wrapper class to make working with GCS bucket names easier."""

  def __init__(self, bucket_url, ref):
    """Constructor for BucketReference.

    Args:
      bucket_url: str, The bucket to reference. Format: gs://<bucket_name>
      ref: Resource, resource corresponding to Bucket
    """
    self._bucket_url = bucket_url
    self.ref = ref

  @property
  def bucket(self):
    return self.ref.bucket

  def GetPublicUrl(self):
    return 'https://storage.googleapis.com/{0}'.format(self.ref.bucket)

  def ToBucketUrl(self):
    return 'gs://{}'.format(self.bucket)

  @classmethod
  def FromArgument(cls, value, require_prefix=True):
    """Validates that the argument is a reference to a Cloud Storage bucket."""
    if require_prefix and not value.startswith(GSUTIL_BUCKET_PREFIX):
      raise argparse.ArgumentTypeError(
          'Must be a valid Google Cloud Storage bucket of the form '
          '[gs://somebucket]')

    try:
      _ValidateBucketUrl(value)
    except InvalidBucketNameError as err:
      raise argparse.ArgumentTypeError(str(err))

    return cls.FromBucketUrl(value)

  @classmethod
  def FromBucketUrl(cls, url):
    """Parse a bucket URL ('gs://' optional) into a BucketReference."""
    return cls(url, resources.REGISTRY.Parse(url, collection='storage.buckets'))

  def __eq__(self, other):
    return self.ToBucketUrl() == other.ToBucketUrl()

  def __ne__(self, other):
    return not self.__eq__(other)


class ObjectReference(object):
  """Wrapper class to make working with Cloud Storage bucket/objects easier."""

  def __init__(self, bucket_ref, name):
    self.bucket_ref = bucket_ref
    self.name = name
    self._ValidateObjectName()

  def _ValidateObjectName(self):
    """Validate the given object name according to the naming requirements.

    See https://cloud.google.com/storage/docs/naming#objectnames

    Raises:
      InvalidObjectNameError: if the given bucket name is invalid
    """
    if not 0 <= len(self.name.encode('utf8')) <= 1024:
      raise InvalidObjectNameError(self.name, VALID_OBJECT_LENGTH_MESSAGE)
    if '\r' in self.name or '\n' in self.name:
      raise InvalidObjectNameError(self.name, VALID_OBJECT_CHARS_MESSAGE)

  @property
  def bucket(self):
    return self.bucket_ref.bucket

  @classmethod
  def FromUrl(cls, url, allow_empty_object=False):
    """Parse an object URL ('gs://' required) into an ObjectReference."""
    match = re.match(GSUTIL_OBJECT_REGEX, url, re.DOTALL)
    if match:
      return cls(BucketReference.FromBucketUrl(match.group('bucket')),
                 match.group('object'))
    match = re.match(GSUTIL_BUCKET_REGEX, url, re.DOTALL)
    if match:
      if allow_empty_object:
        return cls(BucketReference.FromBucketUrl(match.group('bucket')), '')
      else:
        raise InvalidObjectNameError('', 'Empty object name is not allowed')
    raise ValueError('Must be of form gs://bucket/object')

  @classmethod
  def FromArgument(cls, url, allow_empty_object=False):
    try:
      return cls.FromUrl(url, allow_empty_object=allow_empty_object)
    except (InvalidObjectNameError, ValueError) as err:
      raise argparse.ArgumentTypeError(str(err))

  @classmethod
  def IsStorageUrl(cls, path):
    try:
      cls.FromUrl(path)
    except ValueError:
      return False
    return True

  def ToUrl(self):
    return '{}/{}'.format(self.bucket_ref.ToBucketUrl(), self.name)

  def GetPublicUrl(self):
    return '{}/{}'.format(self.bucket_ref.GetPublicUrl(), self.name)

  def __eq__(self, other):
    return self.ToUrl() == other.ToUrl()

  def __ne__(self, other):
    return not self.__eq__(other)


def GetMessages():
  """Import and return the appropriate storage messages module."""
  return core_apis.GetMessagesModule('storage', 'v1')


def GetClient():
  """Import and return the appropriate storage client."""
  return core_apis.GetClientInstance('storage', 'v1')


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


def RunGsutilCommand(command_name, command_arg_str, run_concurrent=False):
  """Runs the specified gsutil command and returns the command's exit code.

  This is more reliable than storage_api.StorageClient.CopyFilesToGcs especially
  for large files.

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
                              out_func=log.file_only_logger.debug,
                              err_func=log.file_only_logger.debug)
