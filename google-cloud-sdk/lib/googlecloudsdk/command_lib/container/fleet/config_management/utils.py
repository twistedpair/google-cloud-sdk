# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Utils for Fleet Anthos Config Management commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.container.fleet import client
from googlecloudsdk.api_lib.container.fleet import util


APPLY_SPEC_VERSION_1 = """
applySpecVersion: 1
spec:
  configSync:
    enabled: false
    sourceFormat: hierarchy
    policyDir:
    preventDrift: false
    httpsProxy:
    secretType: none|ssh|cookiefile|token|gcenode
    syncBranch: master
    syncRepo: URL
    syncWait: 15
    syncRev: HEAD
    gcpServiceAccountEmail:
  policyController:
    enabled: false
    referentialRulesEnabled: false
    templateLibraryInstalled: true
    logDeniesEnabled: false
    auditIntervalSeconds: 60
    exemptableNamespaces: []
    mutationEnabled: false
  hierarchyController:
     enabled: false
     enablePodTreeLabels: false
     enableHierarchicalResourceQuota: false
"""

CONFIG_SYNC = 'configSync'
POLICY_CONTROLLER = 'policyController'
HNC = 'hierarchyController'
PREVENT_DRIFT_VERSION = '1.10.0'
MONITORING_VERSION = '1.12.0'


def versions_for_member(feature, membership):
  """Parses the version fields from an ACM Feature for a given membership.

  Args:
    feature: A v1alpha, v1beta, or v1 ACM Feature.
    membership: The short membership name whose version to return.

  Returns:
    A tuple of the form (spec.version, state.spec.version), with unset versions
    defaulting to the empty string.
  """
  spec_version = None
  specs = client.HubClient.ToPyDict(feature.membershipSpecs)
  for full_membership, spec in specs.items():
    if util.MembershipShortname(full_membership) == membership:
      if spec is not None and spec.configmanagement is not None:
        spec_version = spec.configmanagement.version
      break

  state_version = None
  states = client.HubClient.ToPyDict(feature.membershipStates)
  for full_membership, state in states.items():
    if util.MembershipShortname(full_membership) == membership:
      if state is not None and state.configmanagement is not None:
        if state.configmanagement.membershipSpec is not None:
          state_version = state.configmanagement.membershipSpec.version
      break

  return (spec_version or '', state_version or '')


def get_backfill_version_from_feature(feature, membership_id):
  """Get the value the version field in FeatureSpec should be set to.

  Args:
    feature: the feature obtained from hub API.
    membership_id: The membership short name whose Spec will be backfilled.

  Returns:
    version: A string denoting the version field in MembershipConfig
  """
  spec_version, state_version = versions_for_member(feature, membership_id)

  if spec_version:
    return spec_version
  # backfill non-specified spec version with current state_version
  return state_version
