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

from googlecloudsdk.api_lib.clouddeploy import release
from googlecloudsdk.api_lib.clouddeploy import rollout
from googlecloudsdk.api_lib.clouddeploy import target
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources


def DescribeTarget(target_ref):
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
    target_ref: target reference.

  Returns:
    a dictionary of <section name:output>.

  """
  try:
    deploy_target = target.TargetsClient().Get(target_ref.RelativeName())
  except apitools_exceptions.HttpError as error:
    raise exceptions.HttpException(error)
  output = {'Target': deploy_target}
  releases, output = GetCurrentRelease(target_ref, output)
  if deploy_target.approvalRequired:
    output = ListPendingApprovals(releases, target_ref, output)

  return output


def GetCurrentRelease(target_ref, output):
  """Gets the current release in the specified target and the last deployment associated with the release.

  Args:
    target_ref: target object.
    output: a directory holds the output content.

  Returns:
    releases associated with the target.
    a content directory.
  """
  releases = []
  try:
    release_client = release.ReleaseClient()
    # get all of the releases associated with the target.
    releases = release_client.ListReleasesByTarget(target_ref)
    # find the last deployed rollout.
    current_rollout = rollout.RolloutClient().GetCurrentRollout(
        releases, target_ref)
    if current_rollout:
      current_rollout_ref = resources.REGISTRY.Parse(
          current_rollout.name,
          collection='clouddeploy.projects.locations.deliveryPipelines.releases.rollouts'
      )
      # get the name of the release associated with the current rollout.
      output['Current Release'] = current_rollout_ref.Parent().RelativeName()
      output['Last deployment'] = current_rollout.deployEndTime
  except apitools_exceptions.HttpError as error:
    log.debug('failed to get current release: ' + error.content)

  return releases, output


def ListPendingApprovals(releases, target_ref, output):
  """Lists the rollouts in pending approval state for the specified target.

  Args:
    releases: releases associated with the target.
    target_ref: target object.
    output: a directory holds the output content.

  Returns:
    a content directory.

  """
  if releases:
    try:
      pending_approvals = rollout.RolloutClient().ListPendingRollouts(
          releases, target_ref)
      if pending_approvals:
        rollouts = {}
        for ro in pending_approvals:
          rollouts[ro.name] = ro.description
        output['Pending Approvals'] = rollouts
    except apitools_exceptions.HttpError as error:
      log.debug('failed to list pending approvals: ' + error.content)

  return output
