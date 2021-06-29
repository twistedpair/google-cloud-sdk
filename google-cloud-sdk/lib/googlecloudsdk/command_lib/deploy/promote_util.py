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

from googlecloudsdk.api_lib.clouddeploy import release
from googlecloudsdk.command_lib.deploy import exceptions
from googlecloudsdk.command_lib.deploy import release_util
from googlecloudsdk.command_lib.deploy import rollout_util
from googlecloudsdk.command_lib.deploy import target_util
from googlecloudsdk.core import log
from googlecloudsdk.core import resources

_LAST_TARGET_IN_SEQUENCE = (
    'Release {} is already deployed to the last target '
    '({}) in the promotion sequence.\n- Release: {}\n- Target: {}\n')


def Promote(release_ref,
            release_obj,
            to_target,
            rollout_id=None,
            annotations=None,
            labels=None):
  """Calls promote API and waits for the operation to finish.

  Args:
    release_ref: protorpc.messages.Message, release resource object.
    release_obj: apitools.base.protorpclite.messages.Message, release message
      object.
    to_target: str, the target to promote the release to.
    rollout_id: str, ID to assign to the generated rollout.
    annotations: dict[str,str], a dict of annotation (key,value) pairs that
      allow clients to store small amounts of arbitrary data in cloud deploy
      resources.
    labels: dict[str,str], a dict of label (key,value) pairs that can be used to
      select cloud deploy resources and to find collections of cloud deploy
      resources that satisfy certain conditions.
  """
  resp = release.ReleaseClient().Promote(release_ref, to_target, rollout_id,
                                         annotations, labels)
  if resp:
    target_id = target_util.TargetId(resp.target)
    output = 'Created Cloud Deploy rollout {} in target {}. '.format(
        rollout_util.RolloutId(resp.rolloutResource), target_id)

    # Check if it requires approval.
    target_obj = release_util.GetSnappedTarget(release_obj, target_id)
    if target_obj and target_obj.requireApproval:
      output += 'The rollout is pending approval.'

    log.status.Print(output)


def GetToTargetID(release_obj):
  """Get the to_target parameter for promote API.

  This checks the promotion sequence to get the next stage to promote the
  release to.

  Args:
    release_obj: apitools.base.protorpclite.messages.Message, release message.

  Returns:
    the target ID.
  """

  if not release_obj.targetSnapshots:
    raise exceptions.NoSnappedTargets(release_obj.name)
  # Use release short name to avoid the issue by mixed use of
  # the project number and id.
  release_ref = resources.REGISTRY.ParseRelativeName(
      release_obj.name,
      collection='clouddeploy.projects.locations.deliveryPipelines.releases',
  )
  to_target = release_obj.targetSnapshots[0].name
  # The order of target snapshots represents the promotion sequence.
  # E.g. test->stage->prod. Here we start with the last stage.
  reversed_snapshots = list(reversed(release_obj.targetSnapshots))
  for i, snapshot in enumerate(reversed_snapshots):
    target_ref = target_util.TargetReferenceFromName(snapshot.name)
    _, current_rollout = target_util.GetReleasesAndCurrentRollout(
        target_ref,
        release_ref.AsDict()['deliveryPipelinesId'])

    if current_rollout:
      current_rollout_ref = resources.REGISTRY.Parse(
          current_rollout.name,
          collection='clouddeploy.projects.locations.deliveryPipelines.releases.rollouts'
      )
      # Promotes the release from the target that is farthest along in the
      # promotion sequence to its next stage in the promotion sequence.
      if current_rollout_ref.Parent().Name() == release_ref.Name():
        if i > 0:
          to_target = reversed_snapshots[i - 1].name
        else:
          log.status.Print(
              _LAST_TARGET_IN_SEQUENCE.format(
                  release_ref.Name(), target_ref.Name(),
                  release_util.ResourceNameProjectNumberToId(
                      release_ref.RelativeName()),
                  release_util.ResourceNameProjectNumberToId(
                      target_ref.RelativeName())))
          to_target = target_ref.RelativeName()
        break

  # This means the release is not deployed to any target,
  # to_target flag is required in this case.
  if to_target == release_obj.targetSnapshots[0].name:
    raise exceptions.ReleaseInactiveError()

  return target_util.TargetId(to_target)
