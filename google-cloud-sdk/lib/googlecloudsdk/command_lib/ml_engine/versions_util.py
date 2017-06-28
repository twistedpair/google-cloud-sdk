# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Utilities for ml versions commands."""
from googlecloudsdk.command_lib.ml_engine import models_util
from googlecloudsdk.command_lib.ml_engine import uploads
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io


class InvalidArgumentCombinationError(exceptions.Error):
  """Indicates that a given combination of arguments was invalid."""
  pass


def ParseVersion(model, version):
  """Parses a model/version ID into a version resource object."""
  return resources.REGISTRY.Parse(
      version,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
          'modelsId': model
      },
      collection='ml.projects.models.versions')


def WaitForOpMaybe(operations_client, op, async_=False, message=None):
  """Waits for an operation if async_ flag is on.

  Args:
    operations_client: api_lib.ml_engine.operations.OperationsClient, the client
      via which to poll
    op: Cloud ML Engine operation, the operation to poll
    async_: bool, whether to wait for the operation or return immediately
    message: str, the message to display while waiting for the operation

  Returns:
    The result of the operation if async_ is true, or the Operation message
        otherwise
  """
  if async_:
    return op
  return operations_client.WaitForOperation(op, message=message).response


def Create(versions_client, operations_client, version_id,
           model=None, origin=None, staging_bucket=None, runtime_version=None,
           config_file=None, async_=None):
  """Create a version, optionally waiting for creation to finish."""
  if origin:
    try:
      origin = uploads.UploadDirectoryIfNecessary(origin, staging_bucket)
    except uploads.MissingStagingBucketException:
      raise InvalidArgumentCombinationError(
          'If --origin is provided as a local path, --staging-bucket must be '
          'given as well.')

  model_ref = models_util.ParseModel(model)
  version = versions_client.BuildVersion(version_id,
                                         path=config_file,
                                         deployment_uri=origin,
                                         runtime_version=runtime_version)
  if not version.deploymentUri:
    raise InvalidArgumentCombinationError(
        'Either `--origin` must be provided or `deploymentUri` must be '
        'provided in the file given by `--config`.')
  op = versions_client.Create(model_ref, version)
  return WaitForOpMaybe(
      operations_client, op, async_=async_,
      message='Creating version (this might take a few minutes)...')


def Delete(versions_client, operations_client, version, model=None):
  version_ref = ParseVersion(model, version)
  console_io.PromptContinue(
      'This will delete version [{}]...'.format(version_ref.versionsId),
      cancel_on_no=True)
  op = versions_client.Delete(version_ref)
  return WaitForOpMaybe(
      operations_client, op, async_=False,
      message='Deleting version [{}]...'.format(version_ref.versionsId))


def Describe(versions_client, version, model=None):
  version_ref = ParseVersion(model, version)
  return versions_client.Get(version_ref)


def List(versions_client, model=None):
  model_ref = models_util.ParseModel(model)
  return versions_client.List(model_ref)


def SetDefault(versions_client, version, model=None):
  version_ref = ParseVersion(model, version)
  return versions_client.SetDefault(version_ref)
