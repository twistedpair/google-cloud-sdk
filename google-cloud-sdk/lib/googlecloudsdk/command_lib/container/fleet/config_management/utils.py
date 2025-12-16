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

from googlecloudsdk.api_lib.container.fleet import util

CONFIG_MANAGEMENT_FEATURE_NAME = 'configmanagement'

# TODO(b/433355766): Move code not used by GA commands into separate file.
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


# TODO(b/459918638): Python unit test this complex helper.
def extract_membership_versions_from_feature(
    feature,
    memberships: list[str]
) -> tuple[list[str], list[str]]:
  """Returns a spec version list and a state version list for memberships.

  Args:
    feature: v1 Feature from which the versions are extracted.
    memberships: List of full Membership names to extract versions for.

  Returns:
    tuple of 2 lists:
      - List of version field values from the configmanagement spec on Feature
        for each Membership in the order of memberships. Empty string elements
        for Memberships whose version field is not set.
      - List of version field values from membershipSpec in the configmanagement
        state on Feature for each Membership in the order of memberships. Empty
        string elements for Memberships whose version field is not set.
  """
  partial_memberships = [util.MembershipPartialName(m) for m in memberships]
  partial_membership_checker = set(partial_memberships)
  spec_versions_by_partial_membership = {}
  if feature.membershipSpecs:
    spec_versions_by_partial_membership = {
        util.MembershipPartialName(entry.key):
            entry.value.configmanagement.version
        for entry in feature.membershipSpecs.additionalProperties
        if (util.MembershipPartialName(entry.key) in partial_membership_checker
            # value cannot be None; check unit tests.
            # configmanagement should never be None, but check just to be safe.
            and entry.value.configmanagement
            # Do not mix None with strings.
            and entry.value.configmanagement.version)
    }
  spec_versions = [
      spec_versions_by_partial_membership.get(m, '')
      for m in partial_memberships
  ]
  state_versions_by_partial_membership = {}
  if feature.membershipStates:
    state_versions_by_partial_membership = {
        util.MembershipPartialName(entry.key):
            entry.value.configmanagement.membershipSpec.version
        for entry in feature.membershipStates.additionalProperties
        if (util.MembershipPartialName(entry.key) in partial_membership_checker
            # value cannot be None; check unit tests.
            # configmanagement should never be None, but check just to be safe.
            and entry.value.configmanagement
            and entry.value.configmanagement.membershipSpec
            # Do not include None with strings.
            and entry.value.configmanagement.membershipSpec.version)
    }
  state_versions = [
      state_versions_by_partial_membership.get(m, '')
      for m in partial_memberships
  ]
  return spec_versions, state_versions


def get_backfill_versions_from_feature(
    feature,
    memberships: list[str]
) -> list[str]:
  """Returns a list of versions to backfill into the Membership configurations.

  Args:
    feature: v1 Feature from which the versions are extracted.
    memberships: List of full Membership names to extract versions for.

  Returns:
    string list: Last used version (currently configured or installed version)
      for each Membership in the order of memberships. Empty string if neither
      exists.
  """
  spec_versions, state_versions = extract_membership_versions_from_feature(
      feature,
      memberships,
  )
  return [
      spec_version or state_version
      for spec_version, state_version in zip(spec_versions, state_versions)
  ]
