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

CONFIG_MANAGEMENT_FEATURE_NAME = 'configmanagement'

APPLY_SPEC_VERSION_1 = """
applySpecVersion: 1
spec:
  upgrades:
  cluster:
  version:
  configSync:
    enabled: true
    stopSyncing: false
    sourceFormat: hierarchy
    policyDir:
    preventDrift: false
    httpsProxy:
    sourceType: git|oci
    secretType: none|ssh|cookiefile|token|gcenode|gcpserviceaccount
    syncBranch: master
    syncRepo: URL
    syncWait: 15
    syncRev: HEAD
    gcpServiceAccountEmail:
    metricsGcpServiceAccountEmail:
    deploymentOverrides:
      name:
      namespace:
      containers:
        name:
        cpuRequest:
        memoryRequest:
        cpuLimit:
        memoryLimit:
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

UPGRADES = 'upgrades'
UPGRADES_AUTO = 'auto'
UPGRADES_MANUAL = 'manual'
UPGRADES_EMPTY = ''
MANAGEMENT_AUTOMATIC = 'MANAGEMENT_AUTOMATIC'
MANAGEMENT_MANUAL = 'MANAGEMENT_MANUAL'
CLUSTER = 'cluster'
VERSION = 'version'
CONFIG_SYNC = 'configSync'
DEPLOYMENT_OVERRIDES = 'deploymentOverrides'
CONTAINER_OVERRIDES = 'containers'
POLICY_CONTROLLER = 'policyController'
HNC = 'hierarchyController'
PREVENT_DRIFT_VERSION = '1.10.0'
MONITORING_VERSION = '1.12.0'
OCI_SUPPORT_VERSION = '1.12.0'
STATUS_PENDING = 'PENDING'
STATUS_STOPPED = 'STOPPED'
STATUS_ERROR = 'ERROR'
STATUS_NOT_INSTALLED = 'NOT_INSTALLED'
STATUS_INSTALLED = 'INSTALLED'


def versions_for_member(feature, membership):
  """Parses the version fields from an ACM Feature for a given membership.

  Args:
    feature: A v1alpha, v1beta, or v1 ACM Feature.
    membership: The full membership name whose version to return.

  Returns:
    A tuple of the form (spec.version, state.spec.version), with unset versions
    defaulting to the empty string.
  """
  spec_version = None
  specs = client.HubClient.ToPyDict(feature.membershipSpecs)
  for full_membership, spec in specs.items():
    if util.MembershipPartialName(
        full_membership) == util.MembershipPartialName(membership):
      if spec is not None and spec.configmanagement is not None:
        spec_version = spec.configmanagement.version
      break

  state_version = None
  states = client.HubClient.ToPyDict(feature.membershipStates)
  for full_membership, state in states.items():
    if util.MembershipPartialName(
        full_membership) == util.MembershipPartialName(membership):
      if state is not None and state.configmanagement is not None:
        if state.configmanagement.membershipSpec is not None:
          state_version = state.configmanagement.membershipSpec.version
      break

  return (spec_version or '', state_version or '')


def get_backfill_version_from_feature(feature, membership):
  """Get the value the version field in FeatureSpec should be set to.

  Args:
    feature: the feature obtained from hub API.
    membership: The full membership name whose Spec will be backfilled.

  Returns:
    version: A string denoting the version field in MembershipConfig
  """
  spec_version, state_version = versions_for_member(feature, membership)

  if spec_version:
    return spec_version
  # backfill non-specified spec version with current state_version
  return state_version
