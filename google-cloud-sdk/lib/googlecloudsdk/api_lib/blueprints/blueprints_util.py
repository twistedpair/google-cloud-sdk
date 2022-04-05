# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utilities for the blueprints API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from apitools.base.py import encoding
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import retry

_API_NAME = 'config'
_ALPHA_API_VERSION = 'v1alpha1'

# The maximum amount of time to wait in between polling long-running operations.
_WAIT_CEILING_MS = 10 * 1000

# The maximum amount of time to wait for the long-running operation.
_MAX_WAIT_TIME_MS = 3 * 60 * 60 * 1000

RELEASE_TRACK_TO_API_VERSION = {
    base.ReleaseTrack.ALPHA: 'v1alpha1',
}


def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  """Returns the messages module for Blueprints Controller.

  Args:
    release_track: The desired value of the enum
      googlecloudsdk.calliope.base.ReleaseTrack.

  Returns:
    Module containing the definitions of messages for Blueprints Controller.
  """
  return apis.GetMessagesModule(_API_NAME,
                                RELEASE_TRACK_TO_API_VERSION[release_track])


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA, use_http=True):
  """Returns an instance of the Blueprints Controller client.

  Args:
    release_track: The desired value of the enum
      googlecloudsdk.calliope.base.ReleaseTrack.
    use_http: bool, True to create an http object for this client.

  Returns:
    base_api.BaseApiClient, An instance of the Cloud Build client.
  """
  return apis.GetClientInstance(
      _API_NAME,
      RELEASE_TRACK_TO_API_VERSION[release_track],
      no_http=(not use_http))


def GetRevision(name):
  """Calls into the GetRevision API.

  Args:
    name: the fully qualified name of the revision, e.g.
      "projects/p/locations/l/deployments/d/revisions/r".

  Returns:
    A messages.Revision.

  Raises:
    HttpNotFoundError: if the revision didn't exist.
  """
  client = GetClientInstance()
  messages = client.MESSAGES_MODULE
  return client.projects_locations_deployments_revisions.Get(
      messages.ConfigProjectsLocationsDeploymentsRevisionsGetRequest(name=name))


def GetDeployment(name):
  """Calls into the GetDeployment API.

  Args:
    name: the fully qualified name of the deployment, e.g.
      "projects/p/locations/l/deployments/d".

  Returns:
    A messages.Deployment.

  Raises:
    HttpNotFoundError: if the deployment didn't exist.
  """
  client = GetClientInstance()
  messages = client.MESSAGES_MODULE
  return client.projects_locations_deployments.Get(
      messages.ConfigProjectsLocationsDeploymentsGetRequest(name=name))


def CreateDeployment(deployment, deployment_id, location):
  """Calls into the CreateDeployment API.

  Args:
    deployment: a messages.Deployment resource (containing properties like the
      blueprint).
    deployment_id: the ID of the deployment, e.g. "my-deployment" in
      "projects/p/locations/l/deployments/my-deployment".
    location: the location in which to create the deployment.

  Returns:
    A messages.OperationMetadata representing the long-running operation.
  """
  client = GetClientInstance()
  messages = client.MESSAGES_MODULE
  return client.projects_locations_deployments.Create(
      messages.ConfigProjectsLocationsDeploymentsCreateRequest(
          parent=location, deployment=deployment, deploymentId=deployment_id))


def UpdateDeployment(deployment, deployment_full_name):
  """Calls into the UpdateDeployment API.

  Args:
    deployment: a messages.Deployment resource (containing properties like the
      blueprint).
    deployment_full_name: the fully qualified name of the deployment.

  Returns:
    A messages.OperationMetadata representing the long-running operation.
  """
  client = GetClientInstance()
  messages = client.MESSAGES_MODULE
  return client.projects_locations_deployments.Patch(
      messages.ConfigProjectsLocationsDeploymentsPatchRequest(
          deployment=deployment, name=deployment_full_name, updateMask=None))


def DeleteDeployment(deployment_full_name):
  """Calls into the DeleteDeployment API.

  Args:
    deployment_full_name: the fully qualified name of the deployment.

  Returns:
    A messages.OperationMetadata representing the long-running operation.
  """
  client = GetClientInstance()
  messages = client.MESSAGES_MODULE
  return client.projects_locations_deployments.Delete(
      messages.ConfigProjectsLocationsDeploymentsDeleteRequest(
          name=deployment_full_name,
          # Delete all child revisions.
          force=True))


def CreatePreview(preview, location):
  """Calls into the CreatePreview API.

  Args:
    preview: a messages.Preview resource (containing properties like the
      blueprint).
    location: string representing the location in which to create the
      deployment.

  Returns:
    A messages.OperationMetadata representing the long-running operation.
  """
  client = GetClientInstance()
  messages = client.MESSAGES_MODULE
  return client.projects_locations_previews.Create(
      messages.ConfigProjectsLocationsPreviewsCreateRequest(
          parent=location, preview=preview))


def WaitForDeleteDeploymentOperation(operation):
  """Waits for the given "delete deployment" LRO to complete.

  Args:
    operation: the operation to poll.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error

  Returns:
    An Operation.ResponseValue instance
  """
  client = GetClientInstance()
  operation_ref = resources.REGISTRY.ParseRelativeName(
      operation.name, collection='config.projects.locations.operations')
  poller = waiter.CloudOperationPollerNoResources(
      client.projects_locations_operations)

  return waiter.WaitFor(
      poller,
      operation_ref,
      'Deleting the deployment',
      wait_ceiling_ms=_WAIT_CEILING_MS)


def WaitForApplyDeploymentOperation(operation, progress_message):
  """Waits for the given "apply deployment" LRO to complete.

  Args:
    operation: the operation to poll.
    progress_message: string to display for default progress_tracker.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error

  Returns:
    A messages.Deployment resource.
  """
  client = GetClientInstance()
  operation_ref = resources.REGISTRY.ParseRelativeName(
      operation.name, collection='config.projects.locations.operations')
  poller = waiter.CloudOperationPoller(client.projects_locations_deployments,
                                       client.projects_locations_operations)

  return WaitForApplyLROWithStagedTracker(poller, operation_ref,
                                          progress_message)


def ApplyProgressStages(preview=False):
  """Gets an OrderedDict of progress_tracker.Stage keys to message mappings.

  Args:
    preview: bool, True if it's a preview LRO, False if it's a deployment LRO.

  Returns:
    An OrderedDict where the keys are the respective stage keys and the values
    are the messages to show for the particular stage.
  """
  messages = GetMessagesModule()
  step_enum = messages.DeploymentOperationMetadata.StepValueValuesEnum

  # **NOTE**: The ordering by which stages are added to this dict is important
  # and MUST match the order in which the CLH executes the stages, otherwise
  # gcloud crashes at runtime with a ValueError.
  stages = collections.OrderedDict()
  stages[step_enum.PREPARING_STORAGE_BUCKET.name] = (
      'Preparing storage bucket (this can take up to 7 minutes on the '
      'first deployment).')
  # TODO(b/195148906): Add Cloud Build log URL to pipeline and apply messages.
  stages[step_enum.RUNNING_PIPELINE
         .name] = 'Processing blueprint through kpt pipeline.'
  if preview:
    stages[step_enum.RUNNING_PREVIEW
           .name] = 'Previewing blueprint with Config Controller.'
  else:
    stages[step_enum.RUNNING_APPLY
           .name] = 'Applying blueprint to Config Controller.'
  return stages


def WaitForApplyLROWithStagedTracker(poller,
                                     operation_ref,
                                     message,
                                     preview=False):
  """Waits for an "apply" deployment/preview LRO using a StagedProgressTracker.

  This function is a wrapper around waiter.PollUntilDone that uses a
  progress_tracker.StagedProgressTracker to display the individual steps of
  an apply deployment or preview LRO.

  Args:
    poller: a waiter.Poller instance
    operation_ref: Reference to the operation to poll on.
    message: string containing the main progress message to display.
    preview: bool, True if it's a preview LRO, False if it's a deployment LRO.

  Returns:
    A response object message from the LRO (i.e. a messages.Preview or
    messages.Deployment).
  """
  messages = GetMessagesModule()
  stages = []
  progress_stages = ApplyProgressStages(preview)
  for key, msg in progress_stages.items():
    stages.append(progress_tracker.Stage(msg, key))

  with progress_tracker.StagedProgressTracker(
      message=message, stages=stages,
      tracker_id='meta.deployment_progress') as tracker:

    def _StatusUpdate(result, status):
      """Updates poller.detailed_message on every tick with an appropriate message.

      Args:
        result: the latest messages.Operation object.
        status: unused.
      """
      del status  # Unused by this logic

      # Need to encode to JSON and then decode to Message to be able to
      # reasonably access attributes.
      json = encoding.MessageToJson(result.metadata)
      deployment_metadata = encoding.JsonToMessage(messages.OperationMetadata,
                                                   json).deploymentMetadata

      if deployment_metadata and deployment_metadata.step and progress_stages.get(
          deployment_metadata.step.name) is not None:
        tracker.StartStage(deployment_metadata.step.name)

        # Complete all previous stages.
        ordered_stages = list(progress_stages.keys())
        current_index = ordered_stages.index(deployment_metadata.step.name)
        for i in range(current_index):
          if not tracker.IsComplete(ordered_stages[i]):
            tracker.CompleteStage(ordered_stages[i])

    try:
      operation = waiter.PollUntilDone(
          poller,
          operation_ref,
          status_update=_StatusUpdate,
          max_wait_ms=_MAX_WAIT_TIME_MS,
          wait_ceiling_ms=_WAIT_CEILING_MS)
    except retry.WaitException:
      # Operation timed out.
      raise waiter.TimeoutError(
          '{0} timed out after {1} seconds. Please retry this operation.'
          .format(operation_ref.Name(), _MAX_WAIT_TIME_MS / 1000))
    result = poller.GetResult(operation)

    if preview:
      # Preview result from the LRO needs to be converted to Message since
      # there is no Get method for preview and poller doesn't automatically
      # do this.
      json = encoding.MessageToJson(result)
      result = encoding.JsonToMessage(messages.Preview, json)
      is_complete = (
          result.state == messages.Preview.StateValueValuesEnum.COMPLETED)
    else:
      is_complete = (
          result.state == messages.Deployment.StateValueValuesEnum.ACTIVE)

    if result is not None and is_complete:
      for stage in stages:
        if not tracker.IsComplete(stage.key):
          tracker.CompleteStage(stage.key)

    return result


def WaitForApplyPreviewOperation(operation):
  """Waits for the given "preview apply" LRO to complete.

  Args:
    operation: the operation to poll.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error

  Returns:
    A messages.Preview resource.
  """
  client = GetClientInstance()
  operation_ref = resources.REGISTRY.ParseRelativeName(
      operation.name, collection='config.projects.locations.operations')
  poller = waiter.CloudOperationPollerNoResources(
      client.projects_locations_operations)
  progress_message = 'Previewing the deployment'
  return WaitForApplyLROWithStagedTracker(
      poller, operation_ref, progress_message, preview=True)


def WaitForDeletePreviewOperation(operation):
  """Waits for the given "preview delete" LRO to complete.

  Args:
    operation: the operation to poll.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error

  Returns:
    A messages.Preview resource.
  """
  client = GetClientInstance()
  operation_ref = resources.REGISTRY.ParseRelativeName(
      operation.name, collection='config.projects.locations.operations')
  poller = waiter.CloudOperationPollerNoResources(
      client.projects_locations_operations)
  progress_message = 'Previewing the deployment deletion'
  result = waiter.WaitFor(
      poller,
      operation_ref,
      progress_message,
      max_wait_ms=_MAX_WAIT_TIME_MS,
      wait_ceiling_ms=_WAIT_CEILING_MS)
  json = encoding.MessageToJson(result)
  messages = GetMessagesModule()
  return encoding.JsonToMessage(messages.Preview, json)
