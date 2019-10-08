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
"""Wraps a CRD message, making fields more convenient."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.api_lib.run import k8s_object


# Identify parameters that are used to set secret values
_SECRET_PROPERTY_PATTERN = '^.*[sS]ecret$'


def _IsSecretProperty(property_name, property_type):
  return (re.match(_SECRET_PROPERTY_PATTERN, property_name) and
          property_type == 'object')


class PropertyHolder(object):
  """Has details for a spec property of a source. Not write-through."""

  def __init__(self, name, description, type_, required):
    self.name = name
    self.description = description
    self.type = type_
    self.required = required


class SourceCustomResourceDefinition(k8s_object.KubernetesObject):
  """Wraps an Source CRD message, making fields more convenient."""

  API_CATEGORY = 'apiextensions.k8s.io'
  KIND = 'CustomResourceDefinition'
  READY_CONDITION = None  # The status field is not currently used on CRDs
  FIELD_BLACKLIST = ['openAPIV3Schema']
  # These fields should not be exposed to the user as regular parameters to be
  # set either because we'll provide another way to specify them, because
  # we'll set them ourselves, or because they're not meant to be set.
  _PRIVATE_PROPERTY_FIELDS = frozenset({'sink', 'ceOverrides'})

  @property
  def source_name(self):
    if 'registry' not in self.schema:
      return None
    return self.schema['registry'].title

  @property
  def source_kind(self):
    return self._m.spec.names.kind

  @property
  def source_kind_plural(self):
    return self._m.spec.names.plural

  @property
  def source_api_category(self):
    return self._m.spec.group

  @property
  def source_version(self):
    return self._m.spec.version

  @property
  def schema(self):
    return JsonSchemaPropsWrapper(self._m.spec.validation.openAPIV3Schema)

  @property
  def event_types(self):
    if 'registry' not in self.schema:
      return []
    return [
        EventTypeDefinition(name, et, self)
        for name, et in self.schema['registry']['eventTypes'].items()
    ]

  @property
  def secret_properties(self):
    """The properties used to define source secrets.

    Returns:
      List[PropertyHolder], modifying this list does *not* modify the underlying
        properties in the SourceCRD.
    """
    properties = []
    required_properties = self.schema['spec'].required
    for k, v in self.schema['spec'].items():
      if (k not in self._PRIVATE_PROPERTY_FIELDS and
          _IsSecretProperty(k, v.type)):
        properties.append(
            PropertyHolder(
                name=k,
                description=v.description,
                type_=v.type,
                required=k in required_properties))
    return properties

  @property
  def properties(self):
    """The user-configurable properties of the source.

    Returns:
      List[PropertyHolder], modifying this list does *not* modify the underlying
        properties in the SourceCRD.
    """
    properties = []
    required_properties = self.schema['spec'].required
    for k, v in self.schema['spec'].items():
      if (k not in self._PRIVATE_PROPERTY_FIELDS and
          not _IsSecretProperty(k, v.type)):
        properties.append(
            PropertyHolder(
                name=k,
                description=v.description,
                type_=v.type,
                required=k in required_properties))
    return properties


class EventTypeDefinition(object):
  """Wrap an event type in a source CRD with its source."""

  # These fields should not be exposed to the user as regular parameters to be
  # set either because we'll provide another way to specify them, because
  # we'll set them ourselves, or because they're not meant to be set.
  _PRIVATE_PROPERTY_FIELDS = frozenset({'type', 'schema', 'specVersion'})

  def __init__(self, name, wrapped_value, source_crd):
    """Wrap an event type and its source.

    Args:
      name: str, event type name
      wrapped_value: JsonSchemaPropsWrapper, wrapped event type json message
      source_crd: SourceCustomResourceDefinition, event type's source CRD
    """
    self._name = name
    self._wrapped_json = wrapped_value
    self._crd = source_crd

  @property
  def crd(self):
    """Source crd that produces this event type."""
    return self._crd

  @property
  def name(self):
    """Name of the event type."""
    return self._name

  @property
  def type(self):
    """Type pattern of the event type."""
    return self._wrapped_json['type'].pattern

  @property
  def description(self):
    """Description of the event type."""
    return self._wrapped_json.description

  @property
  def schema(self):
    """Build the dictionary of schema-related info."""
    return {
        'type': self.type,
        'schema': self._wrapped_json['schema'].pattern,
        'description': self.description,
        'category': self._crd.source_name
    }

  def __repr__(self):
    return '{}({})'.format(type(self).__name__, repr(self._wrapped_json))

  def __eq__(self, other):
    if isinstance(other, type(self)):
      # pylint:disable=protected-access
      return (self._name == other._name and
              self._wrapped_json == other._wrapped_json and
              self._crd == other._crd)
    return False


class JsonSchemaPropsWrapper(k8s_object.ListAsReadOnlyDictionaryWrapper):
  """Wrap a JSONSchemaProps message with properties in a dict-like manner.

  Nesting in JSONSchemaProps messages is done via lists of its own type.
  This class provides access to the underlying information in a dict-like
  manner rather than needing to handle accessing the lists directly.
  """

  def __init__(self, to_wrap):
    """Wrap the actual keys and values of a JSONSchemaProps message.

    Args:
      to_wrap: JSONSchemaProps message
    """
    super(JsonSchemaPropsWrapper, self).__init__(
        to_wrap.properties.additionalProperties, key_field='key')
    self._wrapped_json = to_wrap

  def __getattr__(self, attr):
    """Fallthrough to the underlying wrapped json to access other fields."""
    return getattr(self._wrapped_json, attr)

  def __getitem__(self, key):
    item = super(JsonSchemaPropsWrapper, self).__getitem__(key)
    value = item.value
    if value.properties is None:
      # It doesn't go any deeper, return the actual value
      return value
    return JsonSchemaPropsWrapper(value)
