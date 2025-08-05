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
"""Shared resource args for insights dataset-configs command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import csv
import enum
import os
from typing import Sequence

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.core.util import files


class ConfigType(enum.Enum):
  PROJECTS = 'projects'
  FOLDERS = 'folders'


def get_source_configs_list(
    source_configs_file: str, config_type: ConfigType
) -> Sequence[int]:
  """Parses a CSV file to extract a list of source configs.

  Args:
    source_configs_file: The path to the CSV file.
    config_type: The type of config from ConfigType enum. This is used to
      generate relevant error messages.

  Returns:
    A list of source config IDs as integers.

  Raises:
    errors.Error | ValueError: If the file format is invalid or if a config ID
    is not a valid number.
  """
  source_configs_abs_path = os.path.expanduser(source_configs_file)

  with files.FileReader(source_configs_abs_path) as f:
    try:
      reader = csv.reader(f)

      source_configs_list = []
      for row_number, row in enumerate(reader):
        row = [element.strip() for element in row if element.strip()]

        if (len(row)) > 1:
          raise ValueError(
              'Row {} Should have excatly 1 column, but found {} columns'
              .format(row_number, len(row))
          )
        if any(row) and row[0].strip():
          try:
            source_configs_list.append(int(row[0].strip()))
          except ValueError:
            raise ValueError(
                'Source {} number {} is not a valid number'.format(
                    config_type.value.rstrip('s'), row[0].strip()
                )
            )
    except Exception as e:
      raise errors.Error(
          'Invalid format for file {} provided for the --source-{}-file'
          ' flag.\nError: {}'.format(source_configs_file, config_type.value, e)
      )

  return source_configs_list


def get_existing_source_config(dataset_config_relative_name, client):
  """Gets the existing source config for the dataset config."""
  dataset_config = client.get_dataset_config(dataset_config_relative_name)

  if dataset_config.organizationScope:
    return f'Organization: {dataset_config.organizationNumber}'
  elif dataset_config.sourceProjects is not None:
    return f'sourceProjects: {dataset_config.sourceProjects.projectNumbers}'
  elif dataset_config.sourceFolders is not None:
    return f'sourceFolders: {dataset_config.sourceFolders.folderNumbers}'
  return None


def get_new_source_config(
    organization_scope, source_projects_list, source_folders_list
):
  """Gets the new scope for the dataset config."""
  if organization_scope:
    return f'organizationScope: {organization_scope}'
  elif source_projects_list is not None:
    return f'sourceProjects: {source_projects_list}'
  elif source_folders_list is not None:
    return f'sourceFolders: {source_folders_list}'
  return None
