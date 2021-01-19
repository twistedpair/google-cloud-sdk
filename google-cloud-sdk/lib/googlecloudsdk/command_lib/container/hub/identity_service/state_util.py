# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Utils for GKE Hub Anthos Identity Service commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os


def parse_feature_spec_memberships(response):
  """Parses feature spec to create structured memberConfig data map.

  Args:
    response: API response containing identityserviceFeatureSpec to parse.

  Returns:
    Mapping from cluster names to MemberConfigs.
  """
  if response.identityserviceFeatureSpec is None or response.identityserviceFeatureSpec.memberConfigs is None:
    feature_spec_membership_details = []
  else:
    feature_spec_membership_details = response.identityserviceFeatureSpec.memberConfigs.additionalProperties
  return {
      membership_detail.key: membership_detail.value
      for membership_detail in feature_spec_membership_details
  }


def parse_feature_state_memberships(response):
  """Parses response to create structured feature state memberbership data map.

  Args:
    response: API response containing featureState to parse.

  Returns:
    Mapping from cluster names to featureStates.
  """
  if response.featureState is None or response.featureState.detailsByMembership is None:
    feature_state_membership_details = []
  else:
    feature_state_membership_details = response.featureState.detailsByMembership.additionalProperties
  return {
      os.path.basename(membership_detail.key): membership_detail
      for membership_detail in feature_state_membership_details
  }


class IdentityServiceMembershipState(object):
  """class stores Identity Service status for memberships to be printed."""

  def __init__(self, cluster_name, cluster_in_spec=None, cluster_in_state=None):
    """Constructor for class to structure membership cluster output.

    Args:
      cluster_name: name of membership cluster that will be printed.
      cluster_in_spec: memberConfig contents of IdentityServiceFeatureSpec.
      cluster_in_state: membership contents of IdentityServiceFeatureState.


    Returns:
      Structured output for membership to be printed in describe command.
    """
    self.membership_name = cluster_name
    self.auth_methods = {}

    # Populate IdentityServiceFeatureSpec values to be printed.
    if cluster_in_spec is not None:
      for auth_method in cluster_in_spec.authMethods:
        if auth_method.oidcConfig is not None:
          name = auth_method.name
          oidc_config = auth_method.oidcConfig
          self.auth_methods[name] = {
              'proxy': auth_method.proxy,
              'protocol': 'OIDC',
              'issuerUri': oidc_config.issuerUri,
              'clientId': oidc_config.clientId,
              'certificateAuthorityData': oidc_config.certificateAuthorityData,
              'extraParams': oidc_config.extraParams,
              'deployCloudConsoleProxy': oidc_config.deployCloudConsoleProxy,
              'groupPrefix': oidc_config.groupPrefix,
              'groupsClaim': oidc_config.groupsClaim,
              'kubectlRedirectUri': oidc_config.kubectlRedirectUri,
              'scopes': oidc_config.scopes,
              'userClaim': oidc_config.userClaim,
              'userPrefix': oidc_config.userPrefix,
          }

    self.feature_state = {}
    identityservice_feature_state = {}
    # Populate FeatureState values to be printed.
    if cluster_in_state is not None:
      self.feature_state['code'] = cluster_in_state.code
      self.feature_state['description'] = cluster_in_state.description
      self.feature_state['updateTime'] = cluster_in_state.updateTime
      # Populate identityserviceFeatureState values to be printed.
      is_feature_state = cluster_in_state.identityserviceFeatureState
      identityservice_feature_state[
          'failureReason'] = is_feature_state.failureReason
      identityservice_feature_state[
          'installedVersion'] = is_feature_state.installedVersion
      identityservice_feature_state[
          'state'] = is_feature_state.state

    self.feature_state[
        'identityserviceFeatureState'] = identityservice_feature_state


