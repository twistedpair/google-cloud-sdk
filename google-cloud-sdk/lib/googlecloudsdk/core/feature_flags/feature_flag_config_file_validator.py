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
"""Validates config file."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from googlecloudsdk.core import yaml
from googlecloudsdk.core import yaml_validator


SCHEMA_PATH = (os.path.join(os.path.dirname(__file__),
                            'feature_flags_config_schema.yaml'))


class Error(Exception):
  """Base exception for feature flag config file validator."""
  pass


class InvalidOrderError(Error):
  """Raised when the properties are not in alphabetical order."""
  pass


class Validator(object):
  """A class representing a config file.

  Instance is a dictionary represtantation (parsed YAML) of the config file.

  Attribute config_file_path: the path to the configuration file
  Invariant: str
  """

  def __init__(self, config_file_path):
    self.parsed_yaml = yaml.load_path(path=config_file_path, round_trip=True)

  def ValidateAlphabeticalOrder(self):
    """Validates whether the properties in the config file are in alphabetical order.

    Raises:
      InvalidOrderError: Error for when the properties are not in alphabetical
      order.
    """
    if list(
        (self.parsed_yaml).keys()) != sorted(list((self.parsed_yaml).keys())):
      raise InvalidOrderError('Properties are not in alphabetical order.')

  def ValidateSchema(self):
    """Validates the parsed_yaml against JSON schema.

    Raises:
      ValidationError: YAML data does not match the schema.
      RefError: YAML $ref path not found
    """
    yaml_validator.Validator(SCHEMA_PATH).Validate(self.parsed_yaml)
