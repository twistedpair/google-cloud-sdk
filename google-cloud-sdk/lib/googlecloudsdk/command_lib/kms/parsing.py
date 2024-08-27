# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Helpers for parsing config files."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import yaml


def ReadAutokeyConfigFromConfigFile(file_path):
  """Fetches the AutokeyConfig from the config file."""
  try:
    parsed_yaml = yaml.load_path(file_path)
  except yaml.Error as error:
    raise exceptions.Error('unable to load kubeconfig for {0}: {1}'.format(
        file_path, error))
  if 'name' not in parsed_yaml:
    raise exceptions.Error('AutokeyConfig file must contain a name.')
  if 'keyProject' not in parsed_yaml:
    raise exceptions.Error('AutokeyConfig file must contain a keyProject.')
  return parsed_yaml['name'], parsed_yaml['keyProject']
