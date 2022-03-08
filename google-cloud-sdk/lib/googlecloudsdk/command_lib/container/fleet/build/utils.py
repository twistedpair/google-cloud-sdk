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
"""Utils for Fleet Cloud Build Hybrid commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import re

from googlecloudsdk.api_lib.container.fleet import client
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.core import exceptions


class Error(exceptions.Error):
  """Class for errors raised by Cloud Build commands."""


def VerifyMembership(membership):
  """Verify the format of `membership` and check the membership exists in Fleet.

  Args:
    membership: The full membership ID.

  Raises:
    Error: if the membership specification is improper.
  """

  fleet_membership_regex = r'^projects/(?P<ProjectNum>[0-9-]+)/locations/global/memberships/(?P<Membership>[a-z0-9-]+)$'
  if re.search(fleet_membership_regex, membership) is None:
    raise Error(
        'Improper membership specification. '
        'Format should be: projects/[PROJECT_NUM]/locations/global/memberships/[MEMBERSHIP-ID]'
    )
  # We're ignoring the result of this call because we just want to verify the
  # membership exists in the fleet.
  v1beta1_client = apis.GetClientInstance('gkehub', 'v1beta1')
  v1beta1_client.projects_locations_memberships.Get(
      v1beta1_client.MESSAGES_MODULE
      .GkehubProjectsLocationsMembershipsGetRequest(name=membership))


def ParseSecuritypolicy(securitypolicy, message):
  """Convert a string representation of a security policy to an enum representation.

  Args:
    securitypolicy: string representation of the security policy
    message: message module client

  Returns:
    an enum representation of the security policy
  """

  return arg_utils.ChoiceToEnum(
      securitypolicy,
      message.CloudBuildMembershipConfig.SecurityPolicyValueValuesEnum)


def GetFeatureSpecMemberships(feature, messages):
  """Returns the feature spec for every member that has Cloud Build installed.

  Args:
    feature: Cloud Build feature
    messages: message client

  Returns:
    Cloud Build Feature Specs dictionary {"membership": membershipConfig}
  """
  spec = feature.cloudbuildFeatureSpec
  if spec is None:
    return {}
  return collections.OrderedDict(
      (k, v)
      for k, v in client.HubClient.ToPyDict(spec.membershipConfigs).items()
      if v != messages.CloudBuildMembershipConfig())


def GetFeatureStateMemberships(feature):
  """Returns the feature state for every member that has Cloud Build installed.

  Args:
    feature: Cloud Build feature

  Returns:
    Cloud Build Feature States dictionary {"membership": featureState}
  """
  state = feature.featureState
  if state is None:
    return {}
  return client.HubClient.ToPyDict(state.detailsByMembership)


def MembershipSpecPatch(messages, membership, spec):
  """Builds a Feature message for updating one CloudBuildMembershipConfig.

  Args:
    messages: The v1alpha1 Fleet messages package
    membership: The membership name to use as the key.
    spec: The CloudBuildMembershipConfig to use as the value.

  Returns:
    The messages.Feature, properly populated.
  """
  spec_map = {membership: spec}
  value = client.HubClient.ToProtoMap(
      messages.CloudBuildFeatureSpec.MembershipConfigsValue, spec_map)
  return messages.Feature(
      cloudbuildFeatureSpec=messages.CloudBuildFeatureSpec(
          membershipConfigs=value))
