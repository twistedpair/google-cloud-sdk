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

"""Feature flag config file loading and parsing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import hashlib
import logging

from googlecloudsdk.core import config
from googlecloudsdk.core import yaml


class Property:
  """A Python Object that stores the value and weight of Property."""

  def __init__(self, yaml_prop):
    self.values = []
    self.weights = []

    for attribute in yaml_prop:
      if all(key in attribute for key in ('value', 'weight')):
        self.values.append(attribute['value'])
        self.weights.append(attribute['weight'])


_FEATURE_FLAG_YAML_URL = 'http://www.gstatic.com/cloudsdk/feature_flag_config_file.yaml'


def Cache(func):
  """Caches the result of a function."""
  cached_results = {}
  @functools.wraps(func)
  def ReturnCachedOrCallFunc(*args):
    try:
      return cached_results[args]
    except KeyError:
      result = func(*args)
      cached_results[args] = result
      return result
  ReturnCachedOrCallFunc.__wrapped__ = func
  return ReturnCachedOrCallFunc


@Cache
def GetFeatureFlagsConfig():
  # pylint: disable=g-import-not-at-top
  from googlecloudsdk.core import requests
  yaml_request = requests.GetSession()
  yaml_data = yaml_request.get(_FEATURE_FLAG_YAML_URL)

  return FeatureFlagsConfig(yaml_data)


class FeatureFlagsConfig:
  """Stores all Property Objects for a given FeatureFlagsConfig."""

  def __init__(self, feature_flags_config_yaml):
    self.properties = _ParseFeatureFlagsConfig(feature_flags_config_yaml)

  def Get(self, prop):
    """Returns the value for the given property."""
    prop_str = str(prop)
    if prop_str not in self.properties:
      return None

    total_weight = sum(self.properties[prop_str].weights)
    prop_client_id = prop_str + config.GetCID()
    project_hash = int(
        hashlib.sha256(prop_client_id.encode('utf-8')).hexdigest(),
        16) % total_weight
    list_of_weights = self.properties[prop_str].weights
    sum_of_weights = 0
    for i in range(len(list_of_weights)):
      sum_of_weights += list_of_weights[i]
      if project_hash < sum_of_weights:
        return self.properties[prop_str].values[i]


def _ParseFeatureFlagsConfig(feature_flags_config_yaml):
  """Converts feature flag config file into a dictionary of Property objects.

  Args:
   feature_flags_config_yaml: str, feature flag config.

  Returns:
   property_dict: A dictionary of Property objects.
  """
  try:
    yaml_dict = yaml.load(feature_flags_config_yaml)
  except yaml.YAMLParseError as e:
    logging.debug('Unable to parse config: %s', e)
    return {}

  property_dict = {}
  for prop in yaml_dict or {}:
    yaml_prop = yaml_dict[prop]
    property_dict[prop] = Property(yaml_prop)
  return property_dict
