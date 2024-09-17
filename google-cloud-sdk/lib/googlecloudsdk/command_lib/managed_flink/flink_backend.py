# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Flink command library functions for the Flink cli binary."""

import copy
import os

from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.util.anthos import binary_operations
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core.util import platforms


DEFAULT_ENV_ARGS = {}

DEFAULT_CONFIG_LOCATION = {
    platforms.OperatingSystem.WINDOWS.id: os.path.join(
        '%APPDATA%', 'google', 'flink', 'config.yaml'
    ),
    platforms.OperatingSystem.MACOSX.id: (
        '~/Library/Preferences/google/flink/config.yaml'
    ),
    platforms.OperatingSystem.LINUX.id: '~/.config/google/flink/config.yaml',
}

_RELEASE_TRACK_TO_VERSION = {
    base.ReleaseTrack.ALPHA: 'v1alpha',
    base.ReleaseTrack.BETA: 'v1beta',
    base.ReleaseTrack.GA: 'v1',
}

MISSING_BINARY = (
    'Could not locate managed flink client executable [{binary}]'
    ' on the system PATH. '
    'Please ensure gcloud managed-flink component is properly '
    'installed. '
    'See https://cloud.google.com/sdk/docs/components for '
    'more details.'
)


class FileUploadError(core_exceptions.Error):
  """Exception raised when a file upload fails."""


def DummyJar():
  """Get flink python jar location."""
  return os.path.join(
      config.Paths().sdk_root,
      'platform',
      'managed-flink-client',
      'lib',
      'flink-python-1.19.0.jar',
  )


def Upload(files, destination, storage_client=None):
  """Uploads a list of files passed as strings to a Cloud Storage bucket."""
  client = storage_client or storage_api.StorageClient()
  destinations = dict()
  for file_to_upload in files:
    file_name = os.path.basename(file_to_upload)
    dest_url = os.path.join(destination, file_name)
    dest_object = storage_util.ObjectReference.FromUrl(dest_url)
    try:
      client.CopyFileToGCS(file_to_upload, dest_object)
      destinations[file_to_upload] = dest_url
    except exceptions.BadFileException as e:
      raise FileUploadError(
          'Failed to upload file ["{}"] to "{}": {}'.format(
              ','.join(files), destination, e
          )
      )
  return destinations


def CheckStagingLocation(staging_location):
  dest = storage_util.ObjectReference.FromUrl(staging_location, True)
  storage_util.ValidateBucketUrl(dest.bucket)
  storage_api.StorageClient().GetBucket(dest.bucket)


def GetEnvArgsForCommand(extra_vars=None, exclude_vars=None):
  """Helper function to add our environment variables to the environment."""
  env = copy.deepcopy(os.environ)
  env.update(DEFAULT_ENV_ARGS)
  if extra_vars:
    env.update(extra_vars)
  if exclude_vars:
    for var in exclude_vars:
      env.pop(var, None)
  return env


def PlatformExecutable():
  """Get the platform executable location."""
  return os.path.join(
      config.Paths().sdk_root,
      'platform',
      'managed-flink-client',
      'bin',
      'managed-flink-client',
  )


def ValidateAutotuning(
    autotuning_mode, min_parallelism, max_parallelism, parallelism
):
  """Validate autotuning configurations."""
  if autotuning_mode == 'elastic':
    if parallelism:
      raise exceptions.InvalidArgumentException(
          'parallelism',
          'Parallelism must NOT be set for elastic autotuning mode.',
      )
    if not min_parallelism:
      raise exceptions.InvalidArgumentException(
          'min-parallelism',
          'Min parallelism must be set for elastic autotuning mode.',
      )
    if not max_parallelism:
      raise exceptions.InvalidArgumentException(
          'max-parallelism',
          'Max parallelism must be set for elastic autotuning mode.',
      )
    if min_parallelism > max_parallelism:
      raise exceptions.InvalidArgumentException(
          'min-parallelism',
          'Min parallelism must be less than or equal to max parallelism.',
      )
  else:
    if not parallelism:
      raise exceptions.InvalidArgumentException(
          'parallelism',
          'Parallelism must be set to a value of 1 or greater for fixed'
          ' autotuning mode.',
      )
    if min_parallelism:
      raise exceptions.InvalidArgumentException(
          'min-parallelism',
          'Min parallelism must NOT be set for fixed autotuning mode.',
      )
    if max_parallelism:
      raise exceptions.InvalidArgumentException(
          'max-parallelism',
          'Max parallelism must NOT be set for fixed autotuning mode.',
      )


class FlinkClientWrapper(binary_operations.BinaryBackedOperation):
  """Wrapper for the Flink client binary."""

  _java_path = None

  def __init__(self, **kwargs):
    custom_errors = {
        'MISSING_EXEC': MISSING_BINARY.format(binary='managed-flink-client')
    }
    super(FlinkClientWrapper, self).__init__(
        binary='managed-flink-client', custom_errors=custom_errors, **kwargs
    )
    # BinaryBackedOperation assumes the binary lives in bin, but that's
    # not the case for managed-flink-client so we need to perform an
    # additiona search. If it still doesn't exist then we can admit that
    # it's not installed.
    if not os.path.exists(self._executable):
      component_executable = PlatformExecutable()
      if os.path.exists(component_executable):
        self._executable = component_executable

  def _ParseArgsForCommand(
      self,
      command,
      job_type,
      jar,
      staging_location,
      temp_dir,
      target='local',
      release_track=base.ReleaseTrack.ALPHA,
      location=None,
      deployment=None,
      network=None,
      subnetwork=None,
      name=None,
      extra_jars=None,
      managed_kafka_clusters=None,
      main_class=None,
      extra_args=None,
      extra_archives=None,
      python_venv=None,
      **kwargs
  ):
    """Parses the arguments for the given command."""

    if command != 'run':
      raise binary_operations.InvalidOperationForBinary(
          'Invalid operation [{}] for Flink CLI.'.format(command)
      )

    args = list()
    if network:
      args.append('-Dgcloud.network={0}'.format(network))
    if subnetwork:
      args.append('-Dgcloud.subnetwork={0}'.format(subnetwork))
    if location:
      args.append('-Dgcloud.region={0}'.format(location))
    if deployment:
      args.append('-Dgcloud.deployment={0}'.format(deployment))
    if name:
      args.append('-Dgcloud.job.display-name={0}'.format(name))
    #   This has been temporarily disabled and commented out to avoid
    #   confusing coverage.
    #    if managed_kafka_clusters:
    #      args.append(
    #          '-Dgcloud.managed-kafka-clusters={0}'.format(
    #              ','.join(managed_kafka_clusters)
    #          )
    #      )

    if not extra_args:
      extra_args = []

    job_args = list()
    for arg in extra_args:
      if arg.startswith('-D'):
        args.append(arg)
      else:
        job_args.append(arg)

    if job_type == 'sql':
      udfs = []
      if extra_jars:
        for j in extra_jars:
          udfs.append('--jar')
          udfs.append(j)

      return (
          args
          + [
              '-Dexecution.target=gcloud',
              '-Dgcloud.output-path={0}'.format(temp_dir),
              '-Dgcloud.api.staging-location={0}'.format(staging_location),
              '--file',
              jar,
          ]
          + udfs
          + job_args
      )
    elif job_type == 'python':
      udfs = []
      if extra_jars:
        udfs.append('--jar')
        for j in extra_jars:
          udfs.append(',')
          udfs.append(j)

      env_folder = python_venv.split('/')[-1]
      archives = ['-Dpython.archives={0}'.format(python_venv)]
      if extra_archives:
        for archive in extra_archives:
          archives.append(',')
          archives.append(archive)
      return (
          [
              command,
              '--target',
              target,
              '--class',
              'org.apache.flink.client.python.PythonDriver',
          ]
          + args
          + [
              '-Dgcloud.output-path={0}'.format(temp_dir),
              '-Dgcloud.api.staging-location={0}'.format(staging_location),
              '-Dpython.client.executable={0}/bin/python3'.format(env_folder),
              '-Dpython.executable={0}/bin/python3'.format(env_folder),
              '-Dpython.pythonpath={0}/lib/python3.10/site-packages/'.format(
                  env_folder
              ),
          ]
          + archives
          + udfs
          + [
              DummyJar(),
              '--python',
              jar,
          ]
          + job_args
      )
    else:
      class_arg = []
      if main_class:
        class_arg = ['--class', main_class]

      return (
          [command, '--target', target]
          + class_arg
          + args
          + [
              '-Dgcloud.output-path={0}'.format(temp_dir),
              '-Dgcloud.api.staging-location={0}'.format(staging_location),
              jar,
          ]
          + job_args
      )
