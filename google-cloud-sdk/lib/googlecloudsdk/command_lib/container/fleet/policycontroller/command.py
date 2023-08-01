# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Provides a utility mixin for Poco-specific gcloud commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import argparse
from typing import Any, Dict

from googlecloudsdk.api_lib.container.fleet import util as fleet_util
from googlecloudsdk.command_lib.container.fleet.features import base
from googlecloudsdk.command_lib.container.fleet.policycontroller import exceptions

# Type alias for a mapping of membership paths to corresponding specs.
SpecMapping = Dict[str, Any]


class PocoCommand:
  """A mixin for Policy Controller specific functionality."""

  def path_specs(self, args: argparse.Namespace) -> SpecMapping:
    """Retrieves memberships specied by the command that exist in the Feature.

    Args:
      args: The argparse object passed to the command.

    Returns:
      A dict mapping a path to the membership spec.

    Raises:
      exceptions.DisabledMembershipError: If the membership is invalid or not
      enabled.
    """
    # Get all specs for memberships
    memberships = [
        fleet_util.MembershipPartialName(p)
        for p in base.ParseMembershipsPlural(
            args, search=True, prompt=True, prompt_cancel=False, autoselect=True
        )
    ]
    specs = self.hubclient.ToPyDict(self.GetFeature().membershipSpecs)

    # Contextual function for determining if a membership (path) is enabled.
    def f(path) -> bool:
      return fleet_util.MembershipPartialName(path) in memberships

    # Report error if any memberships are missing
    errors = [
        exceptions.InvalidPocoMembershipError(
            'Policy Controller is not enabled for membership {}'.format(path)
        )
        for path in specs.keys() if not f(path)
    ]
    if errors:
      raise exceptions.InvalidPocoMembershipError(errors)

    # Otherwise send back path->spec mapping.
    return specs

  def update_specs(self, specs: SpecMapping) -> None:
    """Merges spec changes and sends and update to the API.

    Args:
      specs: Specs with updates. These are merged with the existing spec (new
        values overriding) and the merged result is sent to the Update api.

    Returns:
      None
    """
    orig = self.hubclient.ToPyDict(self.GetFeature().membershipSpecs)
    merged = {path: specs.get(path, spec) for path, spec in orig.items()}
    self.Update(
        ['membership_specs'],
        self.messages.Feature(
            membershipSpecs=self.hubclient.ToMembershipSpecs(merged)
        ),
    )
