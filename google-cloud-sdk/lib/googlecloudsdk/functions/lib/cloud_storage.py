# Copyright 2015 Google Inc. All Rights Reserved.

"""Utilities for interacting with Google Cloud Storage."""

import os

from googlecloudsdk.core import config
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core.util import platforms


def BuildRemoteDestination(bucket, path):
  return '{0}/{1}'.format(bucket, path)


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
  args = execution_utils.ArgsForBinaryTool(_GetGsutilPath(), *gsutil_args)
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
