# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""Hooks for ApiHub commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re


_SYSTEM_ATTRIBUTE_SUFFIXES = [
    'enum_values',
    'enumValues',
    'string_values',
    'stringValues',
    'json_values',
    'jsonValues',
    'uri_values',
    'uriValues',
]


def _CamelCase(snake_str):
  """Converts a snake_case string to camelCase, handling dots."""
  parts = snake_str.split('.')
  camel_parts = []
  for part in parts:
    camel_parts.append(re.sub(r'_([a-z])', lambda x: x.group(1).upper(), part))
  return '.'.join(camel_parts)


def _AddConfigEntries(config, snake_field, suffixes, target=None):
  """Adds config entries for a field, handling snake_case and camelCase.

  Args:
    config: The dictionary to add entries to.
    snake_field: The field name in snake_case.
    suffixes: A list of suffixes for this field.
    target: The top-level field name in the update mask. Defaults to
      snake_field.
  """
  if target is None:
    target = snake_field
  camel_field = _CamelCase(snake_field)

  for suffix in suffixes:
    config[f'{snake_field}.{suffix}'] = target
    if snake_field != camel_field:
      config[f'{camel_field}.{suffix}'] = target


def _AddSystemAttributeConfigEntries(config, *snake_fields):
  for field in snake_fields:
    _AddConfigEntries(config, field, _SYSTEM_ATTRIBUTE_SUFFIXES)


def ModifyUpdateMask(ref, unused_args, request):
  """Modifies the update mask to use top-level fields for complex attributes.

  Args:
    ref: The resource reference.
    unused_args: The parsed command arguments.
    request: The request message.

  Returns:
    The modified request.
  """
  if not request.updateMask:
    return request

  # API Collection Config
  # Collection: apihub.projects.locations.apis
  api_field_config = {}
  _AddSystemAttributeConfigEntries(
      api_field_config,
      'team',
      'target_user',
      'business_unit',
      'maturity_level',
      'api_style',
      'api_requirements',
      'api_functional_requirements',
      'api_technical_requirements',
  )
  _AddConfigEntries(
      api_field_config, 'owner', ['email', 'display_name', 'displayName']
  )
  _AddConfigEntries(
      api_field_config, 'documentation', ['external_uri', 'externalUri']
  )

  # Version Collection Config
  # Collection: apihub.projects.locations.apis.versions
  version_field_config = {}
  _AddSystemAttributeConfigEntries(
      version_field_config, 'lifecycle', 'compliance', 'accreditation'
  )
  _AddConfigEntries(
      version_field_config, 'documentation', ['external_uri', 'externalUri']
  )

  # Operation Collection Config
  # Collection: apihub.projects.locations.apis.versions.operations
  operation_field_config = {}
  _AddConfigEntries(
      operation_field_config,
      'details.documentation',
      ['external_uri', 'externalUri'],
  )
  _AddConfigEntries(
      operation_field_config,
      'details.http_operation.path',
      ['description', 'path'],
  )
  _AddConfigEntries(
      operation_field_config, 'details.http_operation.method', ['method']
  )

  # Spec Collection Config
  # Collection: apihub.projects.locations.apis.versions.specs
  spec_field_config = {}
  _AddSystemAttributeConfigEntries(spec_field_config, 'spec_type')
  _AddConfigEntries(
      spec_field_config, 'documentation', ['external_uri', 'externalUri']
  )
  _AddConfigEntries(
      spec_field_config, 'contents', ['mime_type', 'mimeType', 'contents']
  )

  # Deployment Collection Config
  # Collection: apihub.projects.locations.deployments
  deployment_field_config = {}
  _AddSystemAttributeConfigEntries(
      deployment_field_config,
      'deployment_type',
      'slo',
      'environment',
      'management_url',
      'source_uri',
  )
  _AddConfigEntries(
      deployment_field_config, 'documentation', ['external_uri', 'externalUri']
  )

  # Select config based on collection
  collection = ref.Collection()
  config_map = {
      'apihub.projects.locations.apis': api_field_config,
      'apihub.projects.locations.apis.versions': version_field_config,
      'apihub.projects.locations.apis.versions.specs': spec_field_config,
      'apihub.projects.locations.deployments': deployment_field_config,
      'apihub.projects.locations.apis.versions.operations': (
          operation_field_config
      ),
  }
  mask_replacements = config_map.get(collection, {})

  new_mask_paths = []
  raw_paths = request.updateMask.split(',')

  for path in raw_paths:
    path = path.strip()
    # Check if this path needs to be replaced
    replaced = False
    for granulated, top_level in mask_replacements.items():
      # Handle both exact match and sub-field match
      if path == granulated or path.startswith(granulated + '.'):
        if top_level not in new_mask_paths:
          new_mask_paths.append(top_level)
        replaced = True
        break

    if not replaced:
      new_mask_paths.append(path)

  # Remove duplicates and join
  new_mask_paths = sorted(list(set(new_mask_paths)))
  request.updateMask = ','.join(new_mask_paths)

  return request
