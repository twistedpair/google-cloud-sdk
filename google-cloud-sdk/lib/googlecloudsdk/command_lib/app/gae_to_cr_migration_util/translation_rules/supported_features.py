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

"""Translate supported features found at app.yaml to equivalent Cloud Run flags."""

from typing import Mapping, Sequence

from googlecloudsdk.command_lib.app.gae_to_cr_migration_util.common import util
from googlecloudsdk.command_lib.app.gae_to_cr_migration_util.config import feature_helper
from googlecloudsdk.core import properties


ENTRYPOINT_FEATURE_KEYS = util.ENTRYPOINT_FEATURE_KEYS
_ALLOW_ENV_VARIABLES_KEY = 'env_variables'
_ALLOW_SERVICE_ACCOUNT_KEY = 'service_account'
_EXCLUDE_FEATURES = util.ENTRYPOINT_FEATURE_KEYS + [_ALLOW_ENV_VARIABLES_KEY]


def translate_supported_features(
    input_type: feature_helper.InputType,
    input_data: Mapping[str, any],
    supported_features: Mapping[str, feature_helper.SupportedFeature],
    project_cli_flag: str,
) -> Sequence[str]:
  """Translate supported features."""
  output_flags = []
  for key, feature in supported_features.items():
    if key in input_data:
      # excluded features are handled in separate translation rules.
      if key in _EXCLUDE_FEATURES:
        continue
      input_value = f'"{input_data[key]}"'
      output_flags += util.generate_output_flags(feature.flags, input_value)

  output_flags += _get_output_flags_for_env_variables(
      input_type, input_data, supported_features
  )
  output_flags += _get_output_flags_for_default_service_account(
      input_data, supported_features, project_cli_flag
  )
  return output_flags


def _get_output_flags_for_env_variables(
    input_type: feature_helper.InputType,
    input_data: Mapping[str, any],
    supported_features: Mapping[str, feature_helper.SupportedFeature],
) -> Sequence[str]:
  """Get output flags for env_variables."""
  # env_variables values is a dict, therefore, the feature key 'env_variables'
  # won't be contained in the flatten input_key_value_pairs, it would be
  # contain in the unflatten input_data instead.
  output_flags = []
  env_variables_key_from_input = util.get_feature_key_from_input(
      input_data, [_ALLOW_ENV_VARIABLES_KEY]
  )
  if env_variables_key_from_input:
    # If input is deployed version, envVariables is a list, otherwise it is a
    # dict.
    if input_type == feature_helper.InputType.ADMIN_API:
      env_variables_value_for_admin_api = input_data[
          env_variables_key_from_input
      ]
      dict_env_variables_value_for_admin_api = {
          value.key: value.value
          for value in env_variables_value_for_admin_api
      }
      env_variables_value = _generate_envs_output(
          dict_env_variables_value_for_admin_api
      )
    else:
      env_variables_value = _generate_envs_output(
          input_data[env_variables_key_from_input]
      )
    feature = supported_features[env_variables_key_from_input]
    output_flags += util.generate_output_flags(
        feature.flags, f'"{env_variables_value}"'
    )
  return output_flags


def _get_output_flags_for_default_service_account(
    input_data: Mapping[str, any],
    supported_features: Mapping[str, feature_helper.SupportedFeature],
    project_cli_flag: str,
) -> Sequence[str]:
  """Get output flags for default service account."""
  input_has_service_account_key = util.get_feature_key_from_input(
      input_data, [_ALLOW_SERVICE_ACCOUNT_KEY]
  )
  # if service_account is not specified in app.yaml/deployed version, use
  # the default service account:
  # https://cloud.google.com/appengine/docs/standard/go/service-account
  if not input_has_service_account_key:
    # if input doesn't contain service account, try to generate the default \
    # service account with the project id:
    # - check if a project id is provided via the --project cli flag.
    # or
    # - check if gcloud config has project id .
    project_id = (
        project_cli_flag
        if project_cli_flag is not None
        else properties.VALUES.core.project.Get()
    )

    feature = supported_features['service_account']
    default_service_account = f'{project_id}@appspot.gserviceaccount.com'
    return util.generate_output_flags(feature.flags, default_service_account)
  return []


def _generate_envs_output(envs: Mapping[str, str]) -> str:
  """Generate output string for env variables.

  Args:
    envs: A dictionary of environment variables.

  Returns:
    A string representing the environment variables in the format
    key=value,key=value or key=value@key=value if value contains comma.
    Returns an empty string if the input is empty.
  """
  if not envs.items():
    return ''
  value_contains_comma = False
  for _, value in envs.items():
    if ',' in value:
      value_contains_comma = True
      break
  delimiter = '@' if value_contains_comma else ','
  output_str = '' if delimiter == ',' else f'^{delimiter}^'
  for key, value in envs.items():
    output_str += f'{key}={value}{delimiter}'
  return output_str[:-1]
