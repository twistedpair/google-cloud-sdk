# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Base classes for commands for MembershipFeature resource."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.command_lib.container.fleet import base as hub_base
from googlecloudsdk.command_lib.container.fleet.features import info


class MembershipFeatureCommand(hub_base.HubCommand):
  """MembershipFeatureCommand is a mixin adding common utils to the MembershipFeature commands."""
  mf_name = ''  # Derived commands should set this to their MembershipFeature.

  @property
  def feature(self):
    """The Feature info entry for this command's Feature."""
    return info.Get(self.mf_name)

  def MembershipFeatureResourceName(self, membership_path):
    """Builds the full MembershipFeature name, using the membership path."""
    return f'{membership_path}/features/{self.mf_name}'

  def GetMembershipFeature(self, membership_path):
    """Fetch this command's MembershipFeature from the API."""
    return self.hubclient_v2.GetMembershipFeature(
        self.MembershipFeatureResourceName(membership_path)
    )


class UpdateCommandMixin(MembershipFeatureCommand):
  """A mixin for functionality to update a MembershipFeature."""

  def UpdateV2(self, membership_path, mask, patch):
    membershipfeature_path = self.MembershipFeatureResourceName(membership_path)
    op = self.hubclient_v2.UpdateMembershipFeature(
        membershipfeature_path, mask, patch
    )
    msg = (
        f'Waiting for MembershipFeature {membershipfeature_path} to be updated'
    )
    return self.WaitForHubOp(
        self.hubclient_v2.membership_feature_waiter,
        op,
        message=msg,
        warnings=False,
    )


class UpdateCommand(UpdateCommandMixin, calliope_base.UpdateCommand):
  """Base class for the command that updates a MembershipFeature."""


class DeleteCommandMixin(MembershipFeatureCommand):
  """A mixin for functionality to delte a MembershipFeature."""

  def DeleteV2(self, membership_path):
    membershipfeature_path = self.MembershipFeatureResourceName(membership_path)

    try:
      op = self.hubclient_v2.DeleteMembershipFeature(membershipfeature_path)
    except apitools_exceptions.HttpNotFoundError:
      return  # Already deleted.

    msg = (
        f'Waiting for MembershipFeature {membershipfeature_path} to be deleted'
    )
    return self.WaitForHubOp(
        self.hubclient_v2.resourceless_waiter,
        op,
        message=msg,
        warnings=False,
    )


class DeleteCommand(DeleteCommandMixin, calliope_base.DeleteCommand):
  """Base class for the command that deletes a MembershipFeature."""
