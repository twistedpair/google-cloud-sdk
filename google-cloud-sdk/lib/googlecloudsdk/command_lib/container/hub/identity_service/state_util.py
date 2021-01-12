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


class IdentityServiceMembershipState(object):
  """class stores Identity Service status for memberships to be printed."""

  def __init__(self, cluster_name, cluster_in=None):
    """Constructor for class to structure membership cluster output.

    Args:
      cluster_name: name of membership cluster that will be printed.
      cluster_in: memberConfig contents of IdentityServiceFeatureSpec.

    Returns:
      Structured output for membership to be printed in describe command.
    """
    self.cluster_name = cluster_name
    self.auth_methods = {}

    if cluster_in is not None:
      for auth_method in cluster_in.authMethods:
        if auth_method.oidcConfig is not None:
          name = auth_method.name
          oidc_config = auth_method.oidcConfig
          self.auth_methods[name] = {
              'protocol': 'OIDC',
              'issuerUri': oidc_config.issuerUri,
              'clientId': oidc_config.clientId,
          }
