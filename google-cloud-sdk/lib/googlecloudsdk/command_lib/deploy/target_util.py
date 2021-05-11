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
"""Utilities for the cloud deploy target resource."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.clouddeploy import release
from googlecloudsdk.api_lib.clouddeploy import rollout
from googlecloudsdk.core import log


def GetReleasesAndCurrentRollout(target_ref, index=0):
  """Gets the releases in the specified target and the last deployment associated with the target.

  Args:
    target_ref: target resource object.
    index: the nth rollout that is deployed to the target.

  Returns:
    release messages associated with the target.
    last deployed rollout message.

  Raises:
    - exceptions raised by RolloutClient.GetCurrentRollout()
  """
  releases = []
  current_rollout = None
  try:
    # get all of the releases associated with the target.
    releases = release.ReleaseClient().ListReleasesByTarget(target_ref)
    # find the last deployed rollout.
    current_rollout = rollout.RolloutClient().GetCurrentRollout(
        releases, target_ref, index)
  except apitools_exceptions.HttpError as error:
    log.debug('failed to get the releases and current rollout of target {}: {}'
              .format(target_ref.RelativeName(), error.content))

  return releases, current_rollout
