# Copyright 2015 Google Inc. All Rights Reserved.

"""Utilities for interacting with Google Cloud Storage.

This makes use of both the Cloud Storage API as well as the gsutil command-line
tool. We use the command-line tool for syncing the contents of buckets as well
as listing the contents. We use the API for checking ACLs.
"""

import argparse
import os
import re

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import config
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.util import platforms

GSUTIL_BUCKET_REGEX = r'^gs://.*$'


def GcsBucketArgument(string):
  """Validates that the argument is a reference to a GCS bucket."""
  if not re.match(GSUTIL_BUCKET_REGEX, string):
    raise argparse.ArgumentTypeError(('Must be a valid Google Cloud Cloud '
                                      'Storage bucket of the form '
                                      '[gs://somebucket]'))

  return string


def ParseGcsUri(gcs_uri):
  """Parses a gs://bucket/path uri into (bucket, object).

  Args:
    gcs_uri: the uri to be parsed.

  Returns:
    Tuple of two strings: (bucket, object).
  """
  GcsBucketArgument(gcs_uri)
  return gcs_uri[len('gs://'):].split('/', 1)


def GsutilReferenceToApiReference(bucket):
  # TODO(user) Consider using the JSON API version of bucket urls:
  # http://www.googleapis.com/storage/v1/b/
  # If we do this, we can use resources.Parse() to auto-generate references.
  return bucket.replace('gs://', 'https://storage.googleapis.com/')


def _GetGsutilPath():
  """Determines the path to the gsutil binary."""
  sdk_bin_path = config.Paths().sdk_bin_path
  if not sdk_bin_path:
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
  env = None

  if platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS:
    gsutil_args = execution_utils.ArgsForCMDTool(command_path + '.cmd',
                                                 *command_args)
  else:
    gsutil_args = execution_utils.ArgsForShellTool(command_path, *command_args)
  log.debug('Running command: [{args}], Env: [{env}]'.format(
      args=' '.join(gsutil_args),
      env=env))
  return execution_utils.Exec(gsutil_args, no_exit=True, env=env,
                              pipe_output_through_logger=True)


def Copy(source_file, dest_obj):
  """Copies a file from the specified file system directory to a GCS bucket.

  Args:
    source_file: The file to be copied.
    dest_obj: The destination location.

  Returns:
    The exit code of the call to "gsutil cp".
  """
  command_arg_str = ' '.join([source_file, dest_obj])
  return _RunGsutilCommand('cp', command_arg_str)


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
