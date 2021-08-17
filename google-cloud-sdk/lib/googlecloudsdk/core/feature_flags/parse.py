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

"""Parse feature flag config file and store data into python objects."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import yaml


class Error(exceptions.Error):
  """A base exception for all user recoverable errors."""


class UnknownPropertyError(Error):
  """Errors when specified property does not exist."""

  def __init__(self, error):
    super(UnknownPropertyError, self).__init__(
        '{err}\nProperty does not exist'.format(err=error))


class Property:
  """A Python Object that stores the value and weight of Property."""

  def __init__(self, yaml_prop):
    self.values = []
    self.weights = []

    for attribute in yaml_prop:
      self.values.append(attribute['value'])
      self.weights.append(attribute['weight'])


class FeatureFlagsConfig:
  """Stores all Property Objects for a given FeatureFlagsConfig."""

  def __init__(self, path):
    self.properties = _ParseFeatureFlagsConfig(path)

  def Get(self, prop):
    """Returns the value for the given property."""
    try:
      return self.RandomValue(prop)
    except KeyError as err:
      raise UnknownPropertyError(err)

  def RandomValue(self, prop):
    """Returns random value in the given property."""
    total_weight = sum(self.properties[prop].weights)
    prop_client_id = prop + config.GetCID()
    project_hash = int(
        hashlib.sha256(prop_client_id.encode('utf-8')).hexdigest(),
        16) % total_weight
    list_of_weights = self.properties[prop].weights
    sum_of_weights = 0
    for i in range(len(list_of_weights)):
      sum_of_weights += list_of_weights[i]
      if project_hash < sum_of_weights:
        return self.properties[prop].values[i]


def _ParseFeatureFlagsConfig(path):
  """Converts feature flag config file into a dictionary of Property objects.

  Args:
   path: str, The absolute path to the feature flag config file.

  Returns:
   property_dict: A dictionary of Property objects.
  """
  property_dict = {}
  yaml_dict = yaml.load(path)
  for prop in yaml_dict:
    yaml_prop = yaml_dict[prop]
    property_dict[prop] = Property(yaml_prop)
  return property_dict
