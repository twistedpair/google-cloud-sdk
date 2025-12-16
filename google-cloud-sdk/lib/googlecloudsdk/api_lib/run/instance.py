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
"""Wraps a Cloud Run Instance message with convenience methods."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.run import container_resource
from googlecloudsdk.api_lib.run import k8s_object


# TODO: b/456195460 - Add ready and status conditions.
class Instance(container_resource.ContainerResource):
  """Wraps a Cloud Run instance message, making fields more convenient."""

  API_CATEGORY = 'run.googleapis.com'
  KIND = 'Instance'
  READY_CONDITION = 'ContainerReady'

  def _EnsureNodeSelector(self):
    if self.spec.nodeSelector is None:
      self.spec.nodeSelector = k8s_object.InitializedInstance(
          self._messages.InstanceSpec.NodeSelectorValue
      )

  @property
  def node_selector(self):
    """The node selector as a dictionary { accelerator_type: value}."""
    self._EnsureNodeSelector()
    return k8s_object.KeyValueListAsDictionaryWrapper(
        self.spec.nodeSelector.additionalProperties,
        self._messages.InstanceSpec.NodeSelectorValue.AdditionalProperty,
        key_field='key',
        value_field='value',
    )
