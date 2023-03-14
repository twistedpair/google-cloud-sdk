# -*- coding: utf-8 -*- #
# Copyright 2022 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Provider-neutral tools for manipulating metadata."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import posix_util
from googlecloudsdk.command_lib.storage import user_request_args_factory
from googlecloudsdk.core import yaml
from googlecloudsdk.core.cache import function_result_cache
from googlecloudsdk.core.util import files

import six


@function_result_cache.lru(maxsize=None)
def cached_read_yaml_json_file(file_path):
  """Converts JSON or YAML file to an in-memory dict.

  Args:
    file_path (str): Path for the file to parse passed in by the user.

  Returns:
    parsed (dict): Parsed value from the provided file_path.

  Raises:
    InvalidUrlError: The provided file_path either failed to load or be parsed
      as a dict.
  """
  expanded_file_path = os.path.realpath(os.path.expanduser(file_path))
  try:
    # Since json is a subset of yaml, parse file as yaml.
    parsed = yaml.load(files.ReadFileContents(expanded_file_path))
    if isinstance(parsed, dict) or isinstance(parsed, list):
      return parsed
  except yaml.YAMLParseError as e:
    raise errors.InvalidUrlError(
        'Found invalid JSON/YAML file {}\n\nOriginal Error: {}'.format(
            file_path, six.text_type(e)
        )
    )

  raise errors.InvalidUrlError(
      'Found invalid JSON/YAML file {}'.format(file_path)
  )


def get_updated_custom_fields(existing_custom_fields,
                              request_config,
                              file_path=None):
  """Returns a dictionary containing new custom metadata for an object.

  Assumes that the custom metadata setter, clear flag, and a group containing
  the update and flags are in a mutually exclusive group, meaning values can be
  provided for one of these three flags/groups. The preserve POSIX flag is not a
  member of this group, meaning it can be set with any of these flags.

  Args:
    existing_custom_fields (dict): Existing custom metadata provided by an API.
    request_config (request_config): May contain custom metadata fields that
      should be modified.
    file_path (str|None): If present, used for parsing POSIX data from a file on
      the system for the --preserve-posix flag.

  Returns:
    Optional[dict] that should be the value of the storage provider's custom
    metadata field. `None` means that existing metadata should remain unchanged.
    Empty dictionary means it should be cleared.
  """
  resource_args = request_config.resource_args
  if not resource_args:
    return

  should_parse_file_posix = request_config.preserve_posix and file_path
  if (not should_parse_file_posix and not resource_args.custom_fields_to_set and
      not resource_args.custom_fields_to_remove and
      not resource_args.custom_fields_to_update):
    return

  posix_metadata = {}
  if should_parse_file_posix:
    posix_attributes = posix_util.get_posix_attributes_from_file(file_path)
    posix_util.update_custom_metadata_dict_with_posix_attributes(
        posix_metadata, posix_attributes)

  if resource_args.custom_fields_to_set == user_request_args_factory.CLEAR:
    # Providing preserve POSIX and clear flags means that an object's metadata
    # should only include POSIX information.
    return posix_metadata

  # POSIX metadata overrides existing values but is overridden by fields
  # provided in update, remove, and set flags.
  if resource_args.custom_fields_to_set:
    posix_metadata.update(resource_args.custom_fields_to_set)
    return posix_metadata

  custom_fields = dict(existing_custom_fields, **posix_metadata)

  # Removes fields before updating them to avoid metadata loss.
  if resource_args.custom_fields_to_remove:
    for key in resource_args.custom_fields_to_remove:
      if key in custom_fields:
        del custom_fields[key]

  if resource_args.custom_fields_to_update:
    custom_fields.update(resource_args.custom_fields_to_update)

  return custom_fields
