# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Wraps an Events Trigger message, making fields more convenient."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.run import k8s_object


# TODO(b/141719436): Don't hardcode v1alpha1 version
_SERVICE_API_VERSION = 'serving.knative.dev/v1alpha1'
_SERVICE_KIND = 'Service'

EVENT_TYPE_FIELD = 'type'
# k8s OwnerReference serialized to a json string
DEPENDENCY_ANNOTATION_FIELD = 'knative.dev/dependency'


class Trigger(k8s_object.KubernetesObject):
  """Wraps an Events Trigger message, making fields more convenient."""

  API_CATEGORY = 'eventing.knative.dev'
  KIND = 'Trigger'
  READY_CONDITION = 'Ready'
  TERMINAL_CONDITIONS = {
      READY_CONDITION,
  }

  @property
  def broker(self):
    return self._m.spec.broker

  @property
  def subscriber(self):
    return self._m.spec.subscriber.ref.name

  @subscriber.setter
  def subscriber(self, service_name):
    """Set the subscriber to a Cloud Run service."""
    self._m.spec.subscriber.ref.apiVersion = _SERVICE_API_VERSION
    self._m.spec.subscriber.ref.kind = _SERVICE_KIND
    self._m.spec.subscriber.ref.name = service_name

  @property
  def filter_attributes(self):
    return k8s_object.ListAsDictionaryWrapper(
        self._m.spec.filter.attributes.additionalProperties,
        self._messages.TriggerFilter.AttributesValue.AdditionalProperty,
        key_field='key',
        value_field='value')
