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

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import apis as core_apis
from googlecloudsdk.core import config
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import platforms


GSUTIL_BUCKET_REGEX = r'^gs://.*$'

LOG_OUTPUT_BEGIN = ' REMOTE BUILD OUTPUT '
LOG_OUTPUT_INCOMPLETE = ' (possibly incomplete) '
OUTPUT_LINE_CHAR = '-'
GCS_URL_PATTERN = (
    'https://www.googleapis.com/storage/v1/b/{bucket}/o/{obj}?alt=media')


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

  def ToAppEngineApiReference(self):
    return 'https://storage.googleapis.com/{0}'.format(self.ref.bucket)

  def ToBucketUrl(self):
    return self._bucket_url

  @classmethod
  def Argument(cls, string):
    """Validates that the argument is a reference to a Cloud Storage bucket."""
    if not re.match(GSUTIL_BUCKET_REGEX, string):
      raise argparse.ArgumentTypeError(('Must be a valid Google Cloud Cloud '
                                        'Storage bucket of the form '
                                        '[gs://somebucket]'))
    return cls.FromBucketUrl(string)

  @classmethod
  def FromBucketUrl(cls, url):
    ref = resources.REGISTRY.Parse(url.rstrip('/'),
                                   collection='storage.buckets')
    return cls(url, ref)


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
