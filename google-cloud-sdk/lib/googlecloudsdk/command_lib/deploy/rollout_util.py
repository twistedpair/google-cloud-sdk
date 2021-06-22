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
"""Utilities for the cloud deploy rollout resource."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import resources

_ROLLOUT_COLLECTION = 'clouddeploy.projects.locations.deliveryPipelines.releases.rollouts'


def RolloutId(rollout_name_or_id):
  """Returns rollout ID.

  Args:
    rollout_name_or_id: str, rollout full name or ID.

  Returns:
    Rollout ID.
  """

  if 'projects/' in rollout_name_or_id:
    return resources.REGISTRY.ParseRelativeName(
        rollout_name_or_id, collection=_ROLLOUT_COLLECTION).Name()

  return rollout_name_or_id
