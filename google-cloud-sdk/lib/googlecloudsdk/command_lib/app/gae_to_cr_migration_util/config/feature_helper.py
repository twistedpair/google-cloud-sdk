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

"""Helper module to access data in the features.yaml file as dataclass types."""

import dataclasses
import enum
from os import path as os_path
import re
from typing import Mapping, Sequence

from googlecloudsdk.core.util import files
from googlecloudsdk.core.yaml import yaml


_CONFIG_PATH = os_path.join(
    os_path.dirname(__file__), "../config/features.yaml"
)


class FeatureType(enum.Enum):
  """Enum of feature types."""

  UNSUPPORTED = "unsupported"
  RANGE_LIMITED = "range-limited"


class InputType(enum.Enum):
  """Enum of input types."""

  APP_YAML = "app_yaml"
  ADMIN_API = "admin_api"


@dataclasses.dataclass(frozen=True)
class Range:
  """Range limit of a RangeLimitFeature.

  Attributes:
    min: The minimum value of the range.
    max: The maximum value of the range.
  """

  min: int
  max: int

  def __post_init__(self):
    """Check if the range is valid.

    Raises:
      ValueError: If the range is invalid.
    """
    if self.min is not None and self.max is not None and self.min > self.max:
      raise ValueError("min must be less than or equal to max")


@dataclasses.dataclass(frozen=True)
class Path:
  """Path variants for appyaml and api input data.

  Attributes:
    app_yaml: The path of the feature in app.yaml.
    admin_api: The path of the feature in admin api.
  """

  admin_api: str
  app_yaml: str


@dataclasses.dataclass
class Feature:
  """Contains common fields for all features."""

  path: Path


@dataclasses.dataclass
class SupportedFeature(Feature):
  """Supported feature with 1:1 mappings between App Engine and Cloud Run features."""

  flags: Sequence[str]


@dataclasses.dataclass
class UnsupportedFeature(Feature):
  """Contains common fields for all unsupported features."""

  severity: str
  reason: str


@dataclasses.dataclass
class RangeLimitFeature(UnsupportedFeature):
  """Contains common fields for all range limited features.

  It extends UnsupportedFeature and adds additional field of range limit.
  """

  range: Range
  flags: Sequence[str] = None

  def validate(self, val: int) -> bool:
    """Check if the given value is within range limit."""
    return self.range.min <= val <= self.range.max


@dataclasses.dataclass
class ValueLimitFeature(UnsupportedFeature):
  """ValueLmimtFeature presents a value_limited Features, it extends UnsupportedFeature and adds additional fields to validate compatible value."""

  allowed_values: Sequence[str] = None
  known_values: Sequence[str] = None
  valid_format: str = None
  flags: Sequence[str] = None

  def validate(self, val: str) -> bool:
    """Check if the given value is valid, either by regex or set of known/allowed values."""
    if self.valid_format is not None:
      # validate by regex only when valid_format is present.
      return re.search(self.valid_format, val) is not None
    if self.known_values is not None and val not in self.known_values:
      reason = f"'{val}' is not a known value."
      self.reason = reason
      return False
    return self.allowed_values is not None and val in self.allowed_values


@dataclasses.dataclass
class FeatureConfig:
  """FeatureConfig represents the incompatible features configuration."""

  unsupported: Sequence[UnsupportedFeature]
  range_limited: Sequence[RangeLimitFeature]
  value_limited: Sequence[ValueLimitFeature]
  supported: Sequence[SupportedFeature]

  def __post_init__(self):
    """Convert the data into dataclass types."""
    unsupported_data = [UnsupportedFeature(**f) for f in self.unsupported]
    self.unsupported = unsupported_data
    range_limited_data = [RangeLimitFeature(**f) for f in self.range_limited]
    self.range_limited = range_limited_data
    value_limited_data = [ValueLimitFeature(**f) for f in self.value_limited]
    self.value_limited = value_limited_data
    supported_data = [SupportedFeature(**f) for f in self.supported]
    self.supported = supported_data


def get_feature_config() -> FeatureConfig:
  """Read config data from features yaml and convert data into dataclass types."""
  read_yaml = _read_yaml_file()
  parsed_yaml_dict = _parse_yaml_file(read_yaml)
  return _dict_to_features(parsed_yaml_dict)


def get_feature_list_by_input_type(
    input_type: InputType, features: UnsupportedFeature
) -> Mapping[str, UnsupportedFeature]:
  """Construct a dictionary of feature list by input type.

  With path as key and the Feature as the value based on the input type. e.g:

  input:
    input_type: appyaml
    features:[
        {
            path: {
                app_yaml: 'inbound_services',
                admin_api: 'inboundServices',
            },
            severity: 'major',
            reason: 'CR does not support GAE bundled services.'
        }
    ]

    output:
    {
        'inbound_services':{
            path: {
                app_yaml: 'inbound_services',
                admin_api: 'inboundServices'
            },
            severity: 'major',
            reason: 'CR does not support GAE bundled services.'
        }
    }

  Args:
    input_type: InputType enum to indicate the type of input data.
    features: List of UnsupportedFeature to be converted.

  Returns:
    A dictionary with path as key and Feature as value.

  Raises:
    KeyError: If the input_type is not a valid enum value.

  Example:
      >>> get_feature_list_by_input_type(InputType.APP_YAML, features)
      {
          'inbound_services':{
              path: {
                  app_yaml: 'inbound_services',
                  admin_api: 'inboundServices'
              },
              severity: 'major',
              reason: 'CR does not support GAE bundled services.'
          }
      }
  """
  return {i.path[input_type.value]: i for i in features}


def _read_yaml_file() -> str:
  """Read the config yaml file of incompatible features."""
  with files.FileReader(_CONFIG_PATH) as incompatible_features_yaml_file:
    return incompatible_features_yaml_file.read()


def _parse_yaml_file(yaml_string: str) -> Mapping[str, any]:
  """Parse the input string as yaml file.

  Args:
    yaml_string: Input string to be parsed as yaml.

  Returns:
    A dictionary of the parsed yaml content.
  """
  return yaml.safe_load(yaml_string)


def _dict_to_features(parsed_yaml: Mapping[str, any]) -> FeatureConfig:
  """Convert the input dictionary into  FeatureConfig type."""
  return FeatureConfig(**parsed_yaml)
