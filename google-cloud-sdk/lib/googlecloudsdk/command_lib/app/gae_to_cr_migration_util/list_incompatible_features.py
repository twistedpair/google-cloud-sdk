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
"""List incompatible features for GAE to CR migration."""
import logging
from os import path as os_path
from typing import Dict, List, Mapping, Sequence
from googlecloudsdk.command_lib.app.gae_to_cr_migration_util.common import util
from googlecloudsdk.command_lib.app.gae_to_cr_migration_util.config import feature_helper
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import yaml


_TEMPLATE_PATH = os_path.join(os_path.dirname(__file__), '../config/')


class IncompatibleFeaturesFoundError(exceptions.Error):
  """An error that is raised when incompatible features are found."""


def check_for_urlmap_conditions(
    url_maps: List[any], input_type: feature_helper.InputType
) -> bool:
  """Checks if any UrlMap in the list has urlRegex='.*' and scriptPath='auto'.

  Args:
      url_maps: A list of UrlMap objects.
      input_type: The input type of the app.yaml file.
  Returns:
      True if all UrlMap matches the conditions, False otherwise.
  """
  for url_map in url_maps:
    if (
        input_type == feature_helper.InputType.ADMIN_API
        and (url_map.urlRegex == '.*' or url_map.urlRegex == '/.*')
        and url_map.script.scriptPath == 'auto'
    ):
      continue
    elif (
        input_type == feature_helper.InputType.APP_YAML
        and url_map['url'] == '/.*'
        and url_map['script'] == 'auto'
    ):
      continue
    else:
      return False
  return True


def get_length(val: any) -> int:
  """Returns the length of the given value."""
  if isinstance(val, list):
    return len(val)
  elif isinstance(val, str):
    return len(val)
  elif isinstance(val, bytes):
    return len(val)
  else:
    return 0


def list_incompatible_features(
    appyaml: str, service: str, version: str
) -> None:
  """Lists the incompatible features in the app.yaml file or deployed app version.

  Args:
      appyaml: The path to the app.yaml file.
      service: The service name.
      version: The version name.
  """
  input_type, input_data = util.validate_input(appyaml, service, version)
  if not input_type or not input_data:
    return
  incompatible_list = _check_for_incompatibility(input_data, input_type)
  appyaml = 'app.yaml' if appyaml is None else appyaml
  input_name = _generate_input_name(input_type, appyaml, service, version)
  _generate_output(incompatible_list, input_type, input_name)


def _generate_input_name(
    input_type: feature_helper.InputType,
    appyaml: str,
    service: str,
    version: str,
) -> str:
  """Generates the input name for the input type."""
  if input_type == feature_helper.InputType.APP_YAML:
    return appyaml
  project_id = properties.VALUES.core.project.Get()
  return f'{project_id}/{service}/{version}'


def _check_for_incompatibility(
    input_data: Mapping[str, any], input_type: feature_helper.InputType
) -> Sequence[any]:
  """Check for incompatibility features in the input yaml."""
  incompatible_list: List[any] = []
  feature_config = feature_helper.get_feature_config()
  unsupported_features = feature_helper.get_feature_list_by_input_type(
      input_type, feature_config.unsupported
  )
  range_limited_features = feature_helper.get_feature_list_by_input_type(
      input_type, feature_config.range_limited
  )
  value_restricted_features = feature_helper.get_feature_list_by_input_type(
      input_type, feature_config.value_limited
  )
  input_key_value_pairs = util.flatten_keys(input_data, '')
  for key, val in input_key_value_pairs.items():
    # Check for unsupported features.
    if key.startswith('build_env_variables'):
      incompatible_list.append(unsupported_features['build_env_variables'])
      continue
    if key.startswith('buildEnvVariables'):
      incompatible_list.append(unsupported_features['buildEnvVariables'])
      continue
    if key in unsupported_features:
      if (
          key.startswith('inboundServices')
          or key.startswith('inbound_services')
      ) and get_length(val) > 0:
        incompatible_list.append(unsupported_features[key])
        continue
      if (
          key.startswith('errorHandlers') or key.startswith('error_handlers')
      ) and get_length(val) > 0:
        incompatible_list.append(unsupported_features[key])
        continue
      if key == 'handlers' and not check_for_urlmap_conditions(val, input_type):
        incompatible_list.append(unsupported_features[key])
        continue
      if key not in [
          'handlers',
          'inbound_services',
          'error_handlers',
          'inboundServices',
          'errorHandlers',
      ]:
        incompatible_list.append(unsupported_features[key])
    # Check for range_limited features.
    if key in range_limited_features:
      if not range_limited_features[key].validate(val):
        incompatible_list.append(range_limited_features[key])
    # Check for value_restricted features.
    if key in value_restricted_features:
      if not value_restricted_features[key].validate(key, val):
        incompatible_list.append(value_restricted_features[key])
  return incompatible_list


def _generate_output(
    incompatible_features: List[feature_helper.UnsupportedFeature],
    input_type: feature_helper.InputType,
    input_name: str,
) -> None:
  """Generate readable output for features compatibility check result."""
  print(f'List incompatible features output for {input_name}:\n')
  logging.info('list-incompatible-features output for %s:\n', input_name)
  if not incompatible_features:
    print('No incompatibilities found.\n')
    logging.info('No incompatibilities found.\n')
    return
  major_features = []
  minor_features = []
  for feature in incompatible_features:
    if feature.severity == 'major':
      major_features.append(feature)
    elif feature.severity == 'minor':
      minor_features.append(feature)
  if minor_features:
    print(
        f'Summary:\nminor: {len(minor_features)}\n'
        f'incompatible_features\n{yaml.dump(_get_display_features(minor_features, input_type))}\n'
    )
    logging.info(
        'Summary:\nminor: %s\nincompatible_features\n%s',
        len(minor_features),
        yaml.dump(_get_display_features(minor_features, input_type)),
    )
  if major_features:
    display_major_features = yaml.dump(
        _get_display_features(major_features, input_type)
    )
    error_message = (
        f'Summary:\nmajor: {len(major_features)}\n'
        f'incompatible_features\n{display_major_features}\n '
    )
    raise IncompatibleFeaturesFoundError(
        error_message
    )


def _get_display_features(
    features: List[feature_helper.UnsupportedFeature],
    input_type: feature_helper.InputType
) -> Sequence[Dict[str, str]]:
  """Convert a List List[Tuple] to List[Object] in order to print desired out format."""
  features_display = []
  for feature in features:
    features_display.append({
        'message': feature.reason,
        'category': feature.path[input_type.value],
        'severity': feature.severity,
    })
  return features_display
