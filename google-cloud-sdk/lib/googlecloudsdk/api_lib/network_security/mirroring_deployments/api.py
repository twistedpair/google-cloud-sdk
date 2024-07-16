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
"""API wrapper for `gcloud network-security mirroring-deployments` commands."""

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
}
_API_NAME = 'networksecurity'


def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  api_version = GetApiVersion(release_track)
  return apis.GetMessagesModule(_API_NAME, api_version)


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  api_version = GetApiVersion(release_track)
  return apis.GetClientInstance(_API_NAME, api_version)


def GetEffectiveApiEndpoint(release_track=base.ReleaseTrack.ALPHA):
  api_version = GetApiVersion(release_track)
  return apis.GetEffectiveApiEndpoint(_API_NAME, api_version)


def GetApiVersion(release_track=base.ReleaseTrack.ALPHA):
  return _API_VERSION_FOR_TRACK.get(release_track)


class Client:
  """API client for Mirroring Deployments commands.

  Attributes:
    messages: API messages class, The Network Security API messages.
  """

  def __init__(self, release_track):
    self._client = GetClientInstance(release_track)
    self._deployments_client = (
        self._client.projects_locations_mirroringDeployments
    )
    self._operations_client = self._client.projects_locations_operations
    self.messages = GetMessagesModule(release_track)
    self._resource_parser = resources.Registry()
    self._resource_parser.RegisterApiByName(
        _API_NAME, _API_VERSION_FOR_TRACK.get(release_track)
    )

  def CreateDeployment(
      self,
      parent,
      forwarding_rule,
      mirroring_deployment_group,
      deployment_id=None,
      labels=None,
  ):
    """Calls the CreateMirroringDeployment API.

    Args:
      parent: The parent of the deployment, e.g.
        "projects/myproj/locations/us-central1"
      forwarding_rule: The forwarding rule of the deployment, e.g.
        "projects/myproj/regions/us-central1/forwardingRules/my-rule"
      mirroring_deployment_group: The deployment group of the deployment, e.g.
        "projects/myproj/locations/global/mirroringDeploymentGroups/my-group"
      deployment_id: The ID of the deployment, e.g. "my-deployment".
      labels: A dictionary with the labels of the deployment.

    Returns:
      NetworksecurityProjectsLocationsMirroringDeploymentsCreateResponse
    """

    deployment = self.messages.MirroringDeployment(
        forwardingRule=forwarding_rule,
        mirroringDeploymentGroup=mirroring_deployment_group,
        labels=labels,
    )

    create_request = self.messages.NetworksecurityProjectsLocationsMirroringDeploymentsCreateRequest(
        mirroringDeployment=deployment,
        mirroringDeploymentId=deployment_id,
        parent=parent,
    )
    return self._deployments_client.Create(create_request)

  def DeleteDeployment(self, name):
    """Calls the DeleteMirroringDeployment API."""
    delete_request = self.messages.NetworksecurityProjectsLocationsMirroringDeploymentsDeleteRequest(
        name=name
    )
    return self._deployments_client.Delete(delete_request)

  def DescribeDeployment(self, name):
    """Calls the GetMirroringDeployment API."""
    get_request = self.messages.NetworksecurityProjectsLocationsMirroringDeploymentsGetRequest(
        name=name
    )
    return self._deployments_client.Get(get_request)

  def ListDeployments(
      self, parent, limit=None, page_size=None, list_filter=None
  ):
    """Calls the ListMirroringDeployments API."""
    list_request = self.messages.NetworksecurityProjectsLocationsMirroringDeploymentsListRequest(
        parent=parent, filter=list_filter
    )
    return list_pager.YieldFromList(
        self._deployments_client,
        list_request,
        batch_size=page_size,
        limit=limit,
        field='mirroringDeployments',
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
        (the Mirroring Deployment) when it completes. If False, nothing will be
        returned (useful for Delete operations).
      max_wait: The time to wait for the operation to succeed before timing out.

    Returns:
      If has_result = True, a Mirroring Deployment entity.
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
