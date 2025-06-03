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

"""Translation rule for timeout feature."""

from typing import Mapping, Sequence
from googlecloudsdk.command_lib.app.gae_to_cr_migration_util.translation_rules import scaling


_SCALING_METHOD_W_10_MIN_TIMEOUT = frozenset(
    {scaling.ScalingTypeAppYaml.AUTOMATIC_SCALING}
)
_SCALING_METHOD_W_60_MIN_TIMEOUT = frozenset({
    scaling.ScalingTypeAppYaml.MANUAL_SCALING,
    scaling.ScalingTypeAppYaml.BASIC_SCALING,
})


def translate_timeout_features(input_data: Mapping[str, any]) -> Sequence[str]:
  """Translate timeout features based on scaling method."""
  scaling_features_used = scaling.get_scaling_features_used(input_data)

  if len(scaling_features_used) == 1:
    scaling_feature = scaling_features_used[0]
    if scaling_feature in _SCALING_METHOD_W_10_MIN_TIMEOUT:
      return ['--timeout=10m']
    if scaling_feature in _SCALING_METHOD_W_60_MIN_TIMEOUT:
      return ['--timeout=60m']
  return []
