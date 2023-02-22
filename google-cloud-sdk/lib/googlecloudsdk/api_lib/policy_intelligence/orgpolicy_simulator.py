# -*- coding: utf-8 -*- #
# Copyright 2022 Google Inc. All Rights Reserved.
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
"""Utilities for Org Policy Simulator API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


_API_NAME = 'policysimulator'
_MAX_WAIT_TIME_MS = 60 * 60 * 1000  # 60 minutes.

VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1alpha',
    # base.ReleaseTrack.BETA: 'v1beta',
    # base.ReleaseTrack.GA: 'v1'
}


def GetApiVersion(release_track):
  """Return the api version of the Org Policy Simulator service."""
  return VERSION_MAP.get(release_track)


class OrgPolicySimulatorApi(object):
  """Base Class for OrgPolicy Simulatoer API."""

  def __new__(cls, release_track):
    if release_track == base.ReleaseTrack.ALPHA:
      return super(OrgPolicySimulatorApi,
                   cls).__new__(OrgPolicySimulatorApiAlpha)

  def __init__(self, release_track):
    self.api_version = GetApiVersion(release_track)
    self.client = apis.GetClientInstance(_API_NAME, self.api_version)
    self.messages = apis.GetMessagesModule(_API_NAME, self.api_version)

  # TODO(b/263303705): Remove the legacy operation name support
  def _IsLegacyOperationName(self, operation_name):
    return operation_name.startswith('operations/')

  # New operation name has format: organizations/<orgID>/locations/<locationID>/
  # orgPolicyViolationsPreviews/<orgPolicyPreviewID>/operations/<operationID>
  def GetViolationsPreviewId(self, operation_name):
    return operation_name.split('/')[-3]

  def WaitForOperation(self, operation, message):
    """Wait for the operation to complete."""
    # Use "GetOperation" from policysimulator v1
    v1_client = apis.GetClientInstance(_API_NAME, 'v1')
    registry = resources.REGISTRY.Clone()
    registry.RegisterApiByName('policysimulator', 'v1')
    # TODO(b/263303705): Remove the legacy operation name support
    if self._IsLegacyOperationName(operation.name):
      operation_ref = registry.Parse(
          operation.name, collection='policysimulator.operations')
    else:
      operation_ref = registry.Parse(
          operation.name,
          params={
              'organizationsId': properties.VALUES.access_context_manager.organization.GetOrFail,
              'locationsId': 'global',
              'orgPolicyViolationsPreviewsId': self.GetViolationsPreviewId(operation.name),
          },
          collection='policysimulator.organizations.locations.orgPolicyViolationsPreviews.operations')
    poller = waiter.CloudOperationPollerNoResources(v1_client.operations)
    return waiter.WaitFor(
        poller, operation_ref, message, wait_ceiling_ms=_MAX_WAIT_TIME_MS)

  @abc.abstractmethod
  def GenerateOrgPolicyViolationsPreviewRequest(self,
                                                violations_preview=None,
                                                parent=None):
    pass

  @abc.abstractmethod
  def GetPolicysimulatorOrgPolicyViolationsPreview(self,
                                                   name=None,
                                                   overlay=None,
                                                   resource_counts=None,
                                                   state=None,
                                                   violations_count=None):
    pass

  @abc.abstractmethod
  def GetOrgPolicyOverlay(self,
                          custom_constraints=None,
                          policies=None):
    pass

  @abc.abstractmethod
  def GetOrgPolicyPolicyOverlay(
      self,
      policy=None,
      policy_parent=None):
    pass

  @abc.abstractmethod
  def GetOrgPolicyCustomConstraintOverlay(self,
                                          custom_constraint=None,
                                          custom_constraint_parent=None):
    pass


class OrgPolicySimulatorApiAlpha(OrgPolicySimulatorApi):
  """Base Class for OrgPolicy Policy Simulator API Alpha."""

  def GenerateOrgPolicyViolationsPreviewRequest(self,
                                                violations_preview=None,
                                                parent=None):
    return self.messages.PolicysimulatorOrganizationsLocationsOrgPolicyViolationsPreviewsRequest(
        googleCloudPolicysimulatorV1alphaOrgPolicyViolationsPreview=violations_preview,
        parent=parent)

  def GetPolicysimulatorOrgPolicyViolationsPreview(self,
                                                   name=None,
                                                   overlay=None,
                                                   resource_counts=None,
                                                   state=None,
                                                   violations_count=None):
    return self.messages.GoogleCloudPolicysimulatorV1alphaOrgPolicyViolationsPreview(
        name=name,
        overlay=overlay,
        resourceCounts=resource_counts,
        state=state,
        violationsCount=violations_count)

  def GetOrgPolicyOverlay(self,
                          custom_constraints=None,
                          policies=None):
    return self.messages.GoogleCloudPolicysimulatorV1alphaOrgPolicyOverlay(
        customConstraints=custom_constraints,
        policies=policies)

  def GetOrgPolicyPolicyOverlay(self,
                                policy=None,
                                policy_parent=None):
    return self.messages.GoogleCloudPolicysimulatorV1alphaOrgPolicyOverlayPolicyOverlay(
        policy=policy,
        policyParent=policy_parent)

  def GetOrgPolicyCustomConstraintOverlay(self,
                                          custom_constraint=None,
                                          custom_constraint_parent=None):
    return self.messages.GoogleCloudPolicysimulatorV1alphaOrgPolicyOverlayCustomConstraintOverlay(
        customConstraint=custom_constraint,
        customConstraintParent=custom_constraint_parent)
