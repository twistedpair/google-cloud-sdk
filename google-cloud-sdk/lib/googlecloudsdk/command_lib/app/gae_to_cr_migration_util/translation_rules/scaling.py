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

"""Translation rule for scaling features."""

import enum
import logging
from typing import Mapping, Sequence

import frozendict
from googlecloudsdk.command_lib.app.gae_to_cr_migration_util.common import util
from googlecloudsdk.command_lib.app.gae_to_cr_migration_util.config import feature_helper


class ScalingTypeAppYaml(enum.Enum):
  """Enum of scaling types in app.yaml."""

  AUTOMATIC_SCALING = 'automatic_scaling'
  MANUAL_SCALING = 'manual_scaling'
  BASIC_SCALING = 'basic_scaling'


_SCALING_FEATURE_KEYS_ALLOWED_LIST = frozendict.frozendict({
    ScalingTypeAppYaml.AUTOMATIC_SCALING: [
        'automatic_scaling.min_instances',
        'automatic_scaling.max_instances',
    ],
    ScalingTypeAppYaml.MANUAL_SCALING: ['manual_scaling.instances'],
    ScalingTypeAppYaml.BASIC_SCALING: ['basic_scaling.max_instances'],
})


def translate_scaling_features(
    input_data: Mapping[str, any],
    range_limited_features: Mapping[str, feature_helper.RangeLimitFeature],
) -> Sequence[str]:
  """Translate scaling features.

  Args:
    input_data: Dictionary of the parsed app.yaml file.
    range_limited_features: Dictionary of scaling features with range limits.

  Returns:
    A list of strings representing the flags for Cloud Run.

  Translation rule: - Only one of the scaling options could be specified:

      - automatic_scaling
      - manual_scaling
      - basic_scaling.
  """
  scaling_types_used = get_scaling_features_used(input_data)
  if not scaling_types_used:
    return []
  if len(scaling_types_used) > 1:
    logging.warning(
        'Warning: More than one scaling type is defined,only one'
        ' scaling option should be used.'
    )
    return []

  scaling_type = scaling_types_used[0]
  return _get_output_flags(input_data, range_limited_features, scaling_type)


def _get_output_flags(
    input_data: Mapping[str, any],
    range_limited_features: Mapping[str, feature_helper.RangeLimitFeature],
    scaling_type: ScalingTypeAppYaml,
) -> Sequence[str]:
  """Get the output flags for the given scaling type.

  Args:
    input_data: Dictionary of the parsed app.yaml file.
    range_limited_features: Dictionary of scaling features with range limits.
    scaling_type: The scaling type used in app.yaml.

  Returns:
    A list of strings representing the flags for Cloud Run.
  """
  input_key_value_pairs = util.flatten_keys(input_data, '')
  # Get feature keys from the input app.yaml that has the scaling type
  # (e.g. 'automatic_scaling') prefix.
  input_feature_keys = util.get_features_by_prefix(
      input_key_value_pairs, scaling_type.value
  )
  # Filter the input_feature_keys by allowed_list, this is to avoid processing
  # other scaling features such as `automatic_scaling.max_concurrent_requests`
  # and `automatic_scaling.target_concurrent_requests`, etc.
  allowed_keys = _SCALING_FEATURE_KEYS_ALLOWED_LIST[scaling_type]
  allowed_input_feature_keys = [
      key for key in input_feature_keys if key in allowed_keys
  ]
  output_flags = []
  for key in allowed_input_feature_keys:
    input_value = input_key_value_pairs[key]
    range_limited_feature = range_limited_features[key]
    output_flags += _get_output_flags_by_scaling_type(
        key, range_limited_feature, input_value
    )
  return output_flags


def _get_output_flags_by_scaling_type(
    feature_key: str,
    range_limited_feature: feature_helper.RangeLimitFeature,
    input_value: str,
) -> Sequence[str]:
  """Get the output flags for the given scaling type.

  Args:
    feature_key: The feature key in app.yaml.
    range_limited_feature: The range limited feature.
    input_value: The input value from app.yaml.

  Returns:
    A list of strings representing the flags for Cloud Run.
  """
  if input_value < range_limited_feature.range['min']:
    logging.warning(
        'Warning: %s has a negagive value of %s, minimum value is %s.',
        feature_key,
        input_value,
        range_limited_feature.range['min'],
    )
    return []

  target_value = (
      input_value
      if range_limited_feature.validate(input_value)
      else range_limited_feature.range['max']
  )
  return util.generate_output_flags(range_limited_feature.flags, target_value)


def get_scaling_features_used(
    input_data: Mapping[str, any],
) -> Sequence[ScalingTypeAppYaml]:
  """Detect which scaling features are used in input (app.yaml)."""
  scaling_types_detected = set()
  for scaling_type in ScalingTypeAppYaml:
    scaling_features_from_input = util.get_features_by_prefix(
        input_data, scaling_type.value
    )
    if scaling_features_from_input:
      scaling_types_detected.add(scaling_type)
  return list(scaling_types_detected)

