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
"""API wrapper for `gcloud network-security intercept-deployments` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources


_API_VERSION_FOR_TRACK = {
    base.ReleaseTrack.ALPHA: 'v1alpha1',
    base.ReleaseTrack.BETA: 'v1beta1',
    base.ReleaseTrack.GA: 'v1',
}
_API_NAME = 'networksecurity'


def GetMessagesModule(release_track=base.ReleaseTrack.BETA):
  api_version = GetApiVersion(release_track)
  return apis.GetMessagesModule(_API_NAME, api_version)


def GetClientInstance(release_track=base.ReleaseTrack.BETA):
  api_version = GetApiVersion(release_track)
  return apis.GetClientInstance(_API_NAME, api_version)


def GetEffectiveApiEndpoint(release_track=base.ReleaseTrack.BETA):
  api_version = GetApiVersion(release_track)
  return apis.GetEffectiveApiEndpoint(_API_NAME, api_version)


def GetApiVersion(release_track=base.ReleaseTrack.BETA):
  return _API_VERSION_FOR_TRACK.get(release_track)


class Client:
  """API client for Intercept Deployments commands.

  Attributes:
    messages: API messages class, The Network Security API messages.
  """

  def __init__(self, release_track):
    self._client = GetClientInstance(release_track)
    self._deployments_client = (
        self._client.projects_locations_interceptDeployments
    )
    self._operations_client = self._client.projects_locations_operations
    self.messages = GetMessagesModule(release_track)
    self._resource_parser = resources.Registry()
    self._resource_parser.RegisterApiByName(
        _API_NAME, GetApiVersion(release_track)
    )

  def CreateDeployment(
      self,
      parent,
      forwarding_rule,
      intercept_deployment_group,
      description,
      deployment_id=None,
      labels=None,
  ):
    """Calls the CreateInterceptDeployment API.

    Args:
      parent: The parent of the deployment, e.g.
        "projects/myproj/locations/us-central1"
      forwarding_rule: The forwarding rule of the deployment, e.g.
        "projects/myproj/regions/us-central1/forwardingRules/my-rule"
      intercept_deployment_group: The deployment group of the deployment, e.g.
        "projects/myproj/locations/global/interceptDeploymentGroups/my-group"
      description: The description of the deployment.
      deployment_id: The ID of the deployment, e.g. "my-deployment".
      labels: A dictionary with the labels of the deployment.

    Returns:
      NetworksecurityProjectsLocationsInterceptDeploymentsCreateResponse
    """

    deployment = self.messages.InterceptDeployment(
        forwardingRule=forwarding_rule,
        interceptDeploymentGroup=intercept_deployment_group,
        labels=labels,
    )
    # TODO(b/391304673): Remove this check once the field is
    # available in V1.
    if hasattr(deployment, 'description'):
      deployment.description = description

    create_request = self.messages.NetworksecurityProjectsLocationsInterceptDeploymentsCreateRequest(
        interceptDeployment=deployment,
        interceptDeploymentId=deployment_id,
        parent=parent,
    )
    return self._deployments_client.Create(create_request)

  def DeleteDeployment(self, name):
    """Calls the DeleteInterceptDeployment API."""
    delete_request = self.messages.NetworksecurityProjectsLocationsInterceptDeploymentsDeleteRequest(
        name=name
    )
    return self._deployments_client.Delete(delete_request)

  def UpdateDeployment(
      self,
      name,
      description,
      update_fields,
  ):
    """Calls the UpdateInterceptDeployment API.

    Args:
      name: The name of the deployment.
      description: The description of the deployment.
      update_fields: A dictionary of the fields to update mapped to their new
        values.

    Returns:
      Operation ref to track the long-running process.
    """
    deployment = self.messages.InterceptDeployment(
        labels=update_fields.get('labels', None),
    )
    # TODO(b/391304673): Remove this check once the field is
    # available in V1.
    if hasattr(deployment, 'description'):
      deployment.description = description

    update_request = self.messages.NetworksecurityProjectsLocationsInterceptDeploymentsPatchRequest(
        name=name,
        interceptDeployment=deployment,
        updateMask=','.join(update_fields.keys())
    )
    return self._deployments_client.Patch(update_request)

  def DescribeDeployment(self, name):
    """Calls the GetInterceptDeployment API."""
    get_request = self.messages.NetworksecurityProjectsLocationsInterceptDeploymentsGetRequest(
        name=name
    )
    return self._deployments_client.Get(get_request)

  def ListDeployments(
      self, parent, limit=None, page_size=None, list_filter=None
  ):
    """Calls the ListInterceptDeployments API."""
    list_request = self.messages.NetworksecurityProjectsLocationsInterceptDeploymentsListRequest(
        parent=parent, filter=list_filter
    )
    return list_pager.YieldFromList(
        self._deployments_client,
        list_request,
        batch_size=page_size,
        limit=limit,
        field='interceptDeployments',
        batch_size_attribute='pageSize',
    )

  def GetOperationRef(self, operation):
    """Converts an Operation to a Resource to use with `waiter.WaitFor`."""
    return self._resource_parser.ParseRelativeName(
        operation.name, 'networksecurity.projects.locations.operations'
    )

  def WaitForOperation(
      self,
      operation_ref,
      message,
      has_result=True,
      max_wait=datetime.timedelta(seconds=600),
  ):
    """Waits for an operation to complete.

    Polls the Network Security Operation service until the operation completes,
    fails, or max_wait_seconds elapses.

    Args:
      operation_ref: A Resource created by GetOperationRef describing the
        Operation.
      message: The message to display to the user while they wait.
      has_result: If True, the function will return the target of the operation
        (the Intercept Deployment) when it completes. If False, nothing will be
        returned (useful for Delete operations).
      max_wait: The time to wait for the operation to succeed before timing out.

    Returns:
      If has_result = True, an Intercept Deployment entity.
      Otherwise, None.
    """
    if has_result:
      poller = waiter.CloudOperationPoller(
          self._deployments_client, self._operations_client
      )
    else:
      poller = waiter.CloudOperationPollerNoResources(self._operations_client)

    return waiter.WaitFor(
        poller,
        operation_ref,
        message,
        max_wait_ms=int(max_wait.total_seconds()) * 1000,
    )
