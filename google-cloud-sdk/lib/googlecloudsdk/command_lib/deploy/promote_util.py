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
"""Utilities for the promote operation."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib.clouddeploy import client_util
from googlecloudsdk.api_lib.clouddeploy import release
from googlecloudsdk.command_lib.deploy import target_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources


def Promote(release_ref, to_target, rollout_id=None):
  """Calls promote API and waits for the operation to finish.

  Args:
    release_ref: release resource object.
    to_target: the target to promote the release to.
    rollout_id: ID to assign to the generated rollout.
  """
  resp = release.ReleaseClient().Promote(release_ref, to_target, rollout_id)
  operation_ref = resources.REGISTRY.ParseRelativeName(
      resp.rollout.operation,
      collection='clouddeploy.projects.locations.operations')
  op_client = client_util.OperationsClient()
  response_msg = op_client.WaitForOperation(
      op_client.Get(operation_ref), operation_ref).response
  if response_msg is not None:
    response = encoding.MessageToPyValue(response_msg)
    if 'name' in response:
      log.status.Print('Created Cloud Deploy rollout {} in target {}.'.format(
          response['name'], resp.rollout.target))


def GetToTargetID(release_obj):
  """Get the to_target parameter for promote API.

  This checks the promotion sequence to get the next stage to promote the
  release to.

  Args:
    release_obj: release message.

  Returns:
    the target ID.
  """

  if not release_obj.targetSnapshots:
    raise exceptions.Error('No snapped targets in the release {}.'.format(
        release_obj.name))

  to_target = release_obj.targetSnapshots[0].name
  # The order of target snapshots represents the promotion sequence.
  # E.g. test->stage->prod. Here we start with the last stage.
  reversed_snapshots = list(reversed(release_obj.targetSnapshots))
  for i, snapshot in enumerate(reversed_snapshots):
    target_ref = resources.REGISTRY.ParseRelativeName(
        snapshot.name,
        collection='clouddeploy.projects.locations.deliveryPipelines.targets')
    _, current_rollout = target_util.GetReleasesAndCurrentRollout(target_ref)

    if current_rollout:
      current_rollout_ref = resources.REGISTRY.Parse(
          current_rollout.name,
          collection='clouddeploy.projects.locations.deliveryPipelines.releases.rollouts'
      )
      # Promotes the release from the target that is farthest along in the
      # promotion sequence to its next stage in the promotion sequence.
      if current_rollout_ref.Parent().RelativeName() == release_obj.name:
        if i > 0:
          to_target = reversed_snapshots[i - 1].name
        else:
          log.status.Print(
              'Release {} is already deployed to the last target {} in the promotion sequence.'
              .format(release_obj.name, target_ref.RelativeName()))
          to_target = target_ref.RelativeName()
        break

  return resources.REGISTRY.ParseRelativeName(
      to_target,
      collection='clouddeploy.projects.locations.deliveryPipelines.targets'
  ).Name()
