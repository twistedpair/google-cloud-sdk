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

import os

from googlecloudsdk.core import config
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core.util import platforms


def BuildRemoteDestination(bucket, path):
  return '{0}{1}'.format(bucket, path)


def _GetGsutilPath():
  """Builds path to gsutil tool.

  Returns:
    A string containing a full path to gsutil tool

  """
  sdk_bin_path = config.Paths().sdk_bin_path
  if not sdk_bin_path:
    sdk_bin_path = ''
  gsutil_file = os.path.join(sdk_bin_path, 'gsutil')
  if platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS:
    gsutil_file += '.cmd'
  return gsutil_file


def _RunGsutilCommand(gsutil_args):
  """Run a gsutil command.

  Args:
    gsutil_args: The list of arguments to pass to gsutil.

  Returns:
    The exit code of the call to the gsutil command.
  """
  args = execution_utils.ArgsForExecutableTool(_GetGsutilPath(), *gsutil_args)
  return execution_utils.Exec(args, no_exit=True)


def Upload(local_file, destination):
  """Runs gsutil to upload files to GCS.

  Args:
    local_file: a full path to the file that should be uploaded.
    destination: a GCS url to which the file must be uploaded.

  Returns:
    The exit code of the call to the gsutil command.
  """
  gsutil_args = ['cp', local_file, destination]
  return _RunGsutilCommand(gsutil_args)
