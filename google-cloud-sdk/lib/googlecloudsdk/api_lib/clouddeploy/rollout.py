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
"""Support library to handle the rollout subcommands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import operator

from googlecloudsdk.api_lib.clouddeploy import client_util
from googlecloudsdk.core import exceptions

PENDING_APPROVAL_FILTER_TEMPLATE = (
    'approvalState="NEEDS_APPROVAL" AND '
    'state="PENDING_APPROVAL" AND targetId="{}"')
DEPLOYED_ROLLOUT_FILTER_TEMPLATE = (
    '(approvalState!="REJECTED" AND '
    'approvalState!="NEEDS_APPROVAL") AND state="SUCCEEDED" AND targetId="{}"')


class RolloutClient(object):
  """Client for release service in the Cloud Deploy API."""

  def __init__(self, client=None, messages=None):
    """Initialize a release.ReleaseClient.

    Args:
      client: base_api.BaseApiClient, the client class for Cloud Deploy.
      messages: module containing the definitions of messages for Cloud Deploy.
    """
    self.client = client or client_util.GetClientInstance()
    self.messages = messages or client_util.GetMessagesModule(client)
    self._service = self.client.projects_locations_deliveryPipelines_releases_rollouts

  def ListPendingRollouts(self, releases, target_ref):
    """Lists the rollouts in PENDING_APPROVAL state for the releases associated with the specified target.

    The rollouts must be approvalState=NEEDS_APPROVAL and
    state=PENDING_APPROVAL. The returned list is sorted by rollout's create
    time.

    Args:
      releases: releases objects.
      target_ref: target object.

    Returns:
      a sorted list of rollouts.
    """
    rollouts = []
    for release in releases:
      request = self.messages.ClouddeployProjectsLocationsDeliveryPipelinesReleasesRolloutsListRequest(
          parent=release.name,
          filter=PENDING_APPROVAL_FILTER_TEMPLATE.format(target_ref.Name()))
      rollouts.extend(self._service.List(request).rollouts)

    return sorted(rollouts, key=lambda x: x.createTime, reverse=True)

  def GetCurrentRollout(self, releases, target_ref, index=0):
    """Gets the last deployed rollouts for the releases associated with the specified target.

    Args:
      releases: releases objects.
      target_ref: target object.
      index: the nth rollout in the list to be returned.

    Returns:
      a rollout object.
    """
    rollouts = []
    for release in releases:
      request = self.messages.ClouddeployProjectsLocationsDeliveryPipelinesReleasesRolloutsListRequest(
          parent=release.name,
          filter=DEPLOYED_ROLLOUT_FILTER_TEMPLATE.format(target_ref.Name()))
      rollouts.extend(self._service.List(request).rollouts)

    if rollouts:
      if not 0 <= index < len(rollouts):
        raise exceptions.Error(
            'total number of rollouts for target {} is {}, index {} out of range.'
            .format(target_ref.Name(), len(rollouts), index))

      return sorted(
          rollouts, key=operator.attrgetter('deployEndTime'),
          reverse=True)[index]

    return None

  def Approve(self, name, approved):
    """Calls the approve API to approve or reject a rollout..

    Args:
      name: Name of the Rollout. Format is
        projects/{project}/locations/{location}/deliveryPipelines/{deliveryPipeline}/releases/{release}/rollouts/{rollout}.
      approved: True = approve; False = reject

    Returns:
      ApproveRolloutResponse message.
    """
    request = self.messages.ClouddeployProjectsLocationsDeliveryPipelinesReleasesRolloutsApproveRequest(
        name=name,
        approveRolloutRequest=self.messages.ApproveRolloutRequest(
            approved=approved))
    return self._service.Approve(request)

  def Get(self, name):
    """Gets a rollout resource.

    Args:
      name: rollout resource name.

    Returns:
      rollout message.
    """
    request = self.messages.ClouddeployProjectsLocationsDeliveryPipelinesReleasesRolloutsGetRequest(
        name=name)
    return self._service.Get(request)
