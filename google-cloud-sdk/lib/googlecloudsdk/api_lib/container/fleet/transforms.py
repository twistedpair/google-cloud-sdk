# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Fleet resource transforms.

A resource transform function converts a JSON-serializable resource to a string
value. This module contains built-in transform functions that may be used in
resource projection and filter expressions.

NOTICE: Unlike transforms of top-level command groups like 'container', the
transform functions in this module are not publicly documented under
'gcloud topic projections'.
"""


def construct_origin_transform(client, fleet_default_exists):
  """Returns projection for MembershipFeatureSpec's origin.type value.

  Args:
    client: Fleet API client.
    fleet_default_exists (bool): Whether the fleetDefaultMemberConfig exists on
      the Feature in question.
  Returns:
    A projection transform function that accepts the origin.type value and
    returns a string representation of whether the Membership's spec is synced
    to the Feature's Fleet-default Membership configuration.
  """
  def transform_feature_membership_spec_origin(r):
    """Returns formatted origin.

    Args:
      r: The JSON-serializable origin.type value string.
    """
    if not fleet_default_exists:
      return 'FLEET_DEFAULT_NOT_CONFIGURED'
    if not r:
      return 'UNKNOWN'
    if r == str(client.messages.Origin.TypeValueValuesEnum.FLEET):
      return 'YES'
    if (r == str(client.messages.Origin.TypeValueValuesEnum.USER) or
        r == str(client.messages.Origin.TypeValueValuesEnum.FLEET_OUT_OF_SYNC)):
      return 'NO'
    # Showing unknown underlying value fails fast.
    return r
  return transform_feature_membership_spec_origin


def get_transforms(client, fleet_default_exists):
  """Returns the Fleet-specific resource transform symbol table.

  Format strings, either set by the user or the default set in the command, may
  call the transform functions in the table by the associated table keys. Format
  strings call the functions on resource fields returned by commands to change
  the displayed value of that field.

  Args:
    client: Fleet API client.
    fleet_default_exists (bool): Whether the fleetDefaultMemberConfig exists on
      the Feature in question.
  Returns:
    A dictionary of transform names to functions.
  """
  return {
      'synced_to_fleet_default':
          construct_origin_transform(client, fleet_default_exists),
  }
