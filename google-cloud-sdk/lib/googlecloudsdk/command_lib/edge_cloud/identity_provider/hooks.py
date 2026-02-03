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
"""Argument processors for Zone Management identity provider surface arguments."""

import json

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files


def LoadConfigFromFile(config: str) -> str:
  """Reads the config from the file and populates the request body.

  Args:
    config: The path to the oidc config file.

  Returns:
    content of the config file.

  Raises:`
    exceptions.InvalidArgumentException: If file cannot be read or is not a
    valid json/yaml.
  """

  try:
    content = files.ReadFileContents(config)
  except FileNotFoundError as e:
    raise exceptions.InvalidArgumentException(
        "config", f"File not found: {config}"
    ) from e

  try:
    return json.loads(content)
  except json.JSONDecodeError as e:
    json_decode_error = e
    pass

  try:
    return yaml.load(content)
  except yaml.YAMLParseError as yaml_parse_error:
    raise exceptions.InvalidArgumentException(
        "config",
        f"Error parsing file {config}. Please provide a"
        f" valid json or yaml file. Json decode error: {json_decode_error}",
    ) from yaml_parse_error
