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
"""Utilities for the cloud deploy describe commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.command_lib.deploy import rollout_util
from googlecloudsdk.command_lib.deploy import target_util
from googlecloudsdk.core import log
from googlecloudsdk.core import resources


def DescribeTarget(target_ref, pipeline_id):
  """Describes details specific to the individual target, delivery pipeline qualified.

  The output contains four sections:

  target
    - detail of the target to be described.

  current release
    - the detail of the active release in the target.

  last deployment
    - timestamp of the last successful deployment.

  pending approvals
    - list the rollouts that require approval.
  Args:
    target_ref: protorpc.messages.Message, target reference.
    pipeline_id: str, delivery pipeline ID.

  Returns:
    A dictionary of <section name:output>.

  """
  target_obj = target_util.GetTarget(target_ref)
  output = {'Target': target_obj}
  releases, current_rollout = target_util.GetReleasesAndCurrentRollout(
      target_ref, pipeline_id)
  output = SetCurrentReleaseAndRollout(current_rollout, output)
  if target_obj.requireApproval:
    output = ListPendingApprovals(releases, target_ref, output)

  return output


def SetCurrentReleaseAndRollout(current_rollout, output):
  """Set current release and the last deployment section in the output.

  Args:
    current_rollout: rollout message.
    output: a directory holds the output content.

  Returns:
    a content directory.
  """

  if current_rollout:
    current_rollout_ref = resources.REGISTRY.Parse(
        current_rollout.name,
        collection='clouddeploy.projects.locations.deliveryPipelines.releases.rollouts'
    )
    # get the name of the release associated with the current rollout.
    output['Current Release'] = current_rollout_ref.Parent().RelativeName()
    output['Last deployment'] = current_rollout.deployEndTime

  return output


def ListPendingApprovals(releases, target_ref, output):
  """Lists the rollouts in pending approval state for the specified target.

  Args:
    releases: releases associated with the target.
    target_ref: protorpc.messages.Message, target object.
    output: dict[str:str], a directory holds the output content.

  Returns:
    A content directory.

  """
  if releases:
    try:
      pending_approvals = rollout_util.ListPendingRollouts(releases, target_ref)
      if pending_approvals:
        output['Pending Approvals'] = [ro.name for ro in pending_approvals]
    except apitools_exceptions.HttpError as error:
      log.debug('Failed to list pending approvals: ' + error.content)

  return output
