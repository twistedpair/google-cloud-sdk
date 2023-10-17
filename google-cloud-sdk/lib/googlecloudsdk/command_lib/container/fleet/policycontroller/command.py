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

from typing import Dict

from apitools.base.protorpclite import messages
from googlecloudsdk.api_lib.container.fleet import util as fleet_util
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.command_lib.container.fleet.features import base
from googlecloudsdk.command_lib.container.fleet.policycontroller import exceptions
from googlecloudsdk.core import exceptions as gcloud_exceptions
import six

# Type alias for a mapping of membership paths to corresponding specs.
SpecMapping = Dict[str, messages.Message]


class PocoCommand:
  """A mixin for Policy Controller specific functionality."""

  def update_fleet_default(self, default_cfg) -> None:
    """Update the feature configuration."""
    mask = ['fleet_default_member_config']
    feature = self.messages.Feature(
        # TODO(b/302390572) Figure out the right way to do this.
        # Inserting this so that something exists on the feature during deletes.
        # Otherwise the CLH will drop the update.
        # DO NOT PUT 'name' IN THE MASK.
        name='notarealname'
    )
    if default_cfg is not None:
      feature.fleetDefaultMemberConfig = (
          self.messages.CommonFleetDefaultMemberConfigSpec(
              policycontroller=default_cfg
          )
      )

    try:
      return self.Update(mask, feature)
    except gcloud_exceptions.Error as e:
      fne = self.FeatureNotEnabledError()
      if six.text_type(e) == six.text_type(fne):
        return self.Enable(feature)
      else:
        raise e

  def current_specs(self) -> SpecMapping:
    """Fetches the current specs from the server.

    If the feature is not enabled, this will return an empty dictionary.

    Returns:
      dictionary mapping from full path to membership spec.
    """
    try:
      return self.hubclient.ToPyDict(self.GetFeature().membershipSpecs)
    except gcloud_exceptions.Error as e:
      fne = self.FeatureNotEnabledError()
      if six.text_type(e) == six.text_type(fne):
        return dict()
      else:
        raise e

  def path_specs(
      self, args: parser_extensions.Namespace, ignore_missing: bool = False
  ) -> SpecMapping:
    """Retrieves memberships specified by the command that exist in the Feature.

    Args:
      args: The argparse object passed to the command.
      ignore_missing: Use this to return a mapping that includes an 'empty' spec
        for each specified path if it doesn't already exist.

    Returns:
      A dict mapping a path to the membership spec.

    Raises:
      exceptions.DisabledMembershipError: If the membership is invalid or not
      enabled.
    """
    # These memberships have their project id in their full path.
    # Shorten to a set of 'region/membership' paths.
    memberships_paths = {
        fleet_util.MembershipPartialName(path): path
        for path in base.ParseMembershipsPlural(
            args, prompt=True, prompt_cancel=False, autoselect=True
        )
    }

    # Map short path to full path and spec.
    # These specs have their project number in their full path.
    specs = {
        fleet_util.MembershipPartialName(path): (path, self._rebuild_spec(spec))
        for path, spec in self.current_specs().items()
        if fleet_util.MembershipPartialName(path) in memberships_paths
    }

    # Ensure that we find all the memberships we are looking for.
    missing = [(s, f) for s, f in memberships_paths.items() if s not in specs]
    if ignore_missing:
      for short, full in missing:
        specs[short] = (full, self.messages.MembershipFeatureSpec())
    else:
      msg = 'Policy Controller is not enabled for membership {}'
      missing_memberships = [
          exceptions.InvalidPocoMembershipError(msg.format(path))
          for path in memberships_paths if path not in specs
      ]
      if missing_memberships:
        raise exceptions.InvalidPocoMembershipError(missing_memberships)

    # Drop the short path info and send back the specs, if they were all found.
    return {path: spec for (path, spec) in specs.values()}

  def _rebuild_spec(self, spec: messages.Message) -> messages.Message:
    """Rebuilds the spec to only include information from policycontroller.

    This is necessary so that feature-level values managed by Hub are not
    unintentionally overwritten (i.e. 'origin').

    Args:
      spec: The spec found by querying the API.

    Returns:
      MembershipFeatureSpec with only policycontroller values, leaving off
      other top-level data.
    """
    return self.messages.MembershipFeatureSpec(
        policycontroller=spec.policycontroller
    )

  def update_specs(self, specs: SpecMapping) -> None:
    """Merges spec changes and sends and update to the API.

    Specs refer to PolicyControllerMembershipSpec objects defined here:
    third_party/py/googlecloudsdk/generated_clients/apis/gkehub/v1alpha/gkehub_v1alpha_messages.py

    (Note the above is for the ALPHA api track. Other tracks are found
    elsewhere.)

    Args:
      specs: Specs with updates. These are merged with the existing spec (new
        values overriding) and the merged result is sent to the Update api.

    Returns:
      None
    """
    feature = self.messages.Feature(
        membershipSpecs=self.hubclient.ToMembershipSpecs(specs)
    )
    try:
      return self.Update(['membership_specs'], feature)
    except gcloud_exceptions.Error as e:
      fne = self.FeatureNotEnabledError()
      if six.text_type(e) == six.text_type(fne):
        return self.Enable(feature)
      else:
        raise e
