# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Wrapper for JSON-based Component metadata."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.kuberun import mapobject


class Component(mapobject.MapObject):
  """Class that wraps a KubeRun Component JSON object."""

  @property
  def name(self):
    return self.props['metadata']['name']

  @property
  def type(self):
    return self.props['spec'].get('type', '')

  @property
  def devkit(self):
    return self.props['spec'].get('devkit', '')

  @classmethod
  def FromJSON(cls, json_object):
    # TODO(b/172370726) Remove handling of legacy json objects.
    if 'apiVersion' not in json_object:
      json_object = _LegacyComponentToAlpha(json_object)
    return cls(json_object)


def _LegacyComponentToAlpha(data):
  return {
      'apiVersion': 'kuberun/v1alpha1',
      'kind': 'Component',
      'metadata': {
          'name': data.get('name', ''),
      },
      'spec': {
          'devkit': data.get('devkit', ''),
          'type': data.get('type', ''),
      },
  }
