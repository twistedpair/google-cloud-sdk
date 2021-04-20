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

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources

_API_NAME = 'config'
_ALPHA_API_VERSION = 'v1alpha1'

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


def GetDeployment(name):
  """Calls into the GetDeployment API.

  Args:
    name: the fully qualified name of the deployment, e.g.
      "projects/p/locations/l/deployments/d".

  Returns:
    A messages.Deployment or None if one didn't exist.
  """
  client = GetClientInstance()
  messages = client.MESSAGES_MODULE
  try:
    return client.projects_locations_deployments.Get(
        messages.ConfigProjectsLocationsDeploymentsGetRequest(
            name=name
        )
    )
  except apitools_exceptions.HttpNotFoundError:
    return None


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
          parent=location,
          deployment=deployment,
          deploymentId=deployment_id
      )
  )


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
          deployment=deployment,
          name=deployment_full_name,
          updateMask=None
      )
  )


def WaitForDeploymentOperation(operation, progress_message):
  """Waits for the given google.longrunning.Operation to complete.

  Args:
    operation: The operation to poll.
    progress_message: String to display for default progress_tracker.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error

  Returns:
    The created Deployment resource.
  """
  client = GetClientInstance()
  operation_ref = resources.REGISTRY.ParseRelativeName(
      operation.name, collection='config.projects.locations.operations')
  poller = waiter.CloudOperationPoller(
      client.projects_locations_deployments,
      client.projects_locations_operations)
  return waiter.WaitFor(poller, operation_ref, progress_message)
