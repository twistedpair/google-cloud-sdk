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
"""Utils for GKE Hub Cloud Build Hybrid commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import os
import re
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.util import exceptions as api_lib_exceptions
from googlecloudsdk.command_lib.container.hub.features import base
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.core import exceptions


def GetFeature(feature_name, feature_display_name, project):
  """Fetch the Cloud Build Hybrid Feature.

  Args:
    feature_name: feature name
    feature_display_name: feature name as displayed in CLI
    project: project id

  Returns:
    CloudBuildFeature
  """
  try:
    name = 'projects/{0}/locations/global/features/{1}'.format(
        project, feature_name)
    feature = base.GetFeature(name)
  except apitools_exceptions.HttpNotFoundError as e:
    raise api_lib_exceptions.HttpException(
        e,
        error_format='The {} Feature for project [{}] is not enabled'.format(
            feature_display_name, project))

  return feature


def GetMembership(membership, project):
  """Retrieve the membership if it's in the hub.

  Args:
    membership: membership id
    project: project id

  Returns:
    membership: A membership name
  Raises: Error, if the membership speciciation is imroper
  """

  hub_membership_regex = r'^projects/(?P<ProjectNum>[0-9-]+)/locations/global/memberships/(?P<Membership>[a-z0-9-]+)$'
  if re.search(hub_membership_regex, membership) is None:
    raise exceptions.Error(
        'Improper membership specification. '
        'Format should be: projects/[PROJECT_NUM]/locations/global/memberships/[MEMBERSHIP-ID]'
    )
  # We're ignoring the result of this call because we want the membership path
  # specified with the project number
  # This function returns the membership path specified with the project id
  # We call this function to verify the membership exists in the hub
  base.GetMembership(project, os.path.basename(membership))

  return membership


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

  if feature.cloudbuildFeatureSpec is None or feature.cloudbuildFeatureSpec.membershipConfigs is None:
    feature_spec_membership_details = []
  else:
    feature_spec_membership_details = feature.cloudbuildFeatureSpec.membershipConfigs.additionalProperties

  return collections.OrderedDict(
      (membership_detail.key, membership_detail.value)
      for membership_detail in feature_spec_membership_details
      if membership_detail.value != messages.CloudBuildMembershipConfig())


def GetFeatureStateMemberships(feature):
  """Returns the feature state for every member that has Cloud Build installed.

  Args:
    feature: Cloud Build feature

  Returns:
    Cloud Build Feature States dictionary {"membership": featureState}
  """
  if feature.featureState is None or feature.featureState.detailsByMembership is None:
    feature_state_membership_details = []
  else:
    feature_state_membership_details = feature.featureState.detailsByMembership.additionalProperties

  return {
      membership_detail.key: membership_detail
      for membership_detail in feature_state_membership_details
  }
