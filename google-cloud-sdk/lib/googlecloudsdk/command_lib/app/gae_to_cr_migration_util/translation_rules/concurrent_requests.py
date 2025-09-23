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

"""Translation rule for concurrent_requests feature."""

import logging
from typing import Mapping, Sequence
from googlecloudsdk.command_lib.app.gae_to_cr_migration_util.common import util
from googlecloudsdk.command_lib.app.gae_to_cr_migration_util.config import feature_helper


_MAX_CONCURRENT_REQUESTS_KEY = 'automatic_scaling.max_concurrent_requests'
_ALLOW_MAX_CONCURRENT_REQ_KEYS = _MAX_CONCURRENT_REQUESTS_KEY
_DEFAULT_STANDARD_CONCURRENCY = 10


def translate_concurrent_requests_features(
    input_data: Mapping[str, any],
    range_limited_features: feature_helper.RangeLimitFeature) -> Sequence[str]:
  """Translate max_concurrent_requests (standard) to Cloud Run --concurrency flag."""
  feature_key = util.get_feature_key_from_input(
      input_data, _ALLOW_MAX_CONCURRENT_REQ_KEYS
  )
  input_has_concurrent_requests = feature_key is not None

  # if input does not have max_concurrent_request/target_concurrent_request
  # specified, use the `automatic_scaling.max_concurrent_requests` from the
  # app2run/config/features.yaml as the default feature.
  if not input_has_concurrent_requests:
    feature = range_limited_features[_MAX_CONCURRENT_REQUESTS_KEY]
    default_value = _DEFAULT_STANDARD_CONCURRENCY
    return util.generate_output_flags(feature.flags, default_value)
  feature = range_limited_features[feature_key]
  input_value = input_data[feature_key]
  if input_value < feature.range['min']:
    logging.warning(
        '%s has invalid value of %s, minimum value is %s',
        feature_key, input_value, feature.range['min']
    )
    return []
  if input_value > feature.range['max']:
    logging.warning(
        '%s has invalid value of %s, maximum value is %s.',
        feature_key, input_value, feature.range['max']
    )
    return util.generate_output_flags(feature.flags, feature.range['max'])
  target_value = (
      input_value if feature.validate(input_value) else feature.range['max']
  )
  return util.generate_output_flags(feature.flags, target_value)
