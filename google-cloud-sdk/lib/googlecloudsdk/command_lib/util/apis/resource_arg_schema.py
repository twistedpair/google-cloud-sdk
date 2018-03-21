# Copyright 2017 Google Inc. All Rights Reserved.
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

"""Helpers for loading resource argument definitions from a yaml declaration."""

from __future__ import absolute_import
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.apis import registry
from googlecloudsdk.command_lib.util.apis import yaml_command_schema_util as util
from googlecloudsdk.core import properties


class Error(Exception):
  """Base class for this module's exceptions."""
  pass


class InvalidResourceArgumentLists(Error):
  """Exception for missing, extra, or out of order arguments."""

  def __init__(self, expected, actual):
    expected = [
        '[' + e + ']' if e in IGNORED_FIELDS else e
        for e in expected]
    super(InvalidResourceArgumentLists, self).__init__(
        'Invalid resource arguments: Expected [{}], Found [{}].'
        .format(', '.join(expected), ', '.join(actual)))


_DEFAULT_PROPS = {'project': properties.VALUES.core.project}
IGNORED_FIELDS = {
    'project': 'project',
    'projectId': 'project',
    'projectsId': 'project',
}


class YAMLResourceArgument(object):
  """Encapsulates the spec for the resource arg of a declarative command."""

  @classmethod
  def FromData(cls, data):
    if not data:
      return None

    return cls(
        data['spec'],
        data['help_text'],
        is_positional=data.get('is_positional', True),
        is_parent_resource=data.get('is_parent_resource', False),
        removed_flags=data.get('removed_flags'),
        disable_auto_completers=data['spec'].get(
            'disable_auto_completers', True)
    )

  def __init__(self, data, group_help, is_positional=True, removed_flags=None,
               is_parent_resource=False, disable_auto_completers=True):
    self.name = data['name']
    self.request_id_field = data.get('request_id_field')

    self.group_help = group_help
    self.is_positional = is_positional
    self.is_parent_resource = is_parent_resource
    self.removed_flags = removed_flags or []

    self._full_collection_name = data['collection']
    self._api_version = data.get('api_version')
    self._attribute_data = data['attributes']
    self._disable_auto_completers = disable_auto_completers

    attribute_names = [a['attribute_name'] for a in self._attribute_data]
    for removed in self.removed_flags:
      if removed not in attribute_names:
        raise util.InvalidSchemaError(
            'Removed flag [{}] for resource arg [{}] references an attribute '
            'that does not exist. Valid attributes are [{}]'.format(
                removed, self.name, ', '.join(attribute_names)))

  def GenerateResourceSpec(self, resource_collection=None):
    """Creates a concept spec for the resource argument.

    Args:
      resource_collection: registry.APICollection, The collection that the
        resource arg must be for. This simply does some extra validation to
        ensure that resource arg is for the correct collection and api_version.
        If not specified, the resource arg will just be loaded based on the
        collection it specifies.

    Returns:
      concepts.ResourceSpec, The generated specification that can be added to
      a parser.
    """
    if self.is_parent_resource:
      parent_collection, _, _ = resource_collection.full_name.rpartition('.')
      resource_collection = registry.GetAPICollection(
          parent_collection, api_version=self._api_version)

    if resource_collection:
      # Validate that the expected collection matches what was registered for
      # the resource argument specification.
      if resource_collection.full_name != self._full_collection_name:
        raise util.InvalidSchemaError(
            'Collection names do not match for resource argument specification '
            '[{}]. Expected [{}], found [{}]'
            .format(self.name, resource_collection.full_name,
                    self._full_collection_name))
      if (self._api_version and
          self._api_version != resource_collection.api_version):
        raise util.InvalidSchemaError(
            'API versions do not match for resource argument specification '
            '[{}]. Expected [{}], found [{}]'
            .format(self.name, resource_collection.api_version,
                    self._api_version))
    else:
      # No required collection, just load whatever the resource arg declared
      # for itself.
      resource_collection = registry.GetAPICollection(
          self._full_collection_name, api_version=self._api_version)

    return self._GenerateResourceSpec(
        resource_collection.full_name, resource_collection.api_version,
        resource_collection.detailed_params)

  def _GenerateResourceSpec(self, full_collection_name, api_version,
                            detailed_params):
    attributes = _GenerateAttributes(detailed_params, self._attribute_data)
    return concepts.ResourceSpec(
        full_collection_name, resource_name=self.name,
        api_version=api_version,
        disable_auto_completers=self._disable_auto_completers,
        **{param: attribute for param, attribute in attributes})


def _GenerateAttributes(expected_param_names, attribute_data):
  """Generate the set of concept attributes that will be part of the resource.

  This also validates that all expected attributes are provided (allowing you
  not to specify ignored fields like project) and that they are in the correct
  order to match the API method.

  Args:
    expected_param_names: [str], The names of the API parameters that the API
      method accepts.
    attribute_data: [{}], A list of attribute dictionaries representing the
      data from the yaml file.

  Raises:
    InvalidResourceArgumentLists: If the registered attributes don't match
      the expected fields in the API method.

  Returns:
    [(str, ResourceParameterAttributeConfig)], A list of tuples of the API
    parameter and corresponding attribute.
  """
  final_attributes = []
  registered_params = [_CreateAttribute(a) for a in attribute_data]
  registered_param_names = [a[0] for a in registered_params]

  for expected_name in expected_param_names:
    if registered_params and expected_name == registered_params[0][0]:
      # Attribute matches expected, add it and continue checking.
      final_attributes.append(registered_params.pop(0))
    elif expected_name in IGNORED_FIELDS:
      # Attribute doesn't match but is being ignored. Add an auto-generated
      # attribute as a substitute.
      attribute_name = IGNORED_FIELDS[expected_name]
      final_attributes.append(
          (expected_name, concepts.ResourceParameterAttributeConfig(
              name=attribute_name, help_text='', completer=None,
              fallthroughs=[
                  deps.PropertyFallthrough(_DEFAULT_PROPS.get(attribute_name))])
          ))
    else:
      # It doesn't match (or there are no more registered params) and the
      # field is not being ignored, error.
      raise InvalidResourceArgumentLists(
          expected_param_names, registered_param_names)

  if registered_params:
    # All expected fields were processed but there are still registered
    # params remaining, they must be extra.
    raise InvalidResourceArgumentLists(
        expected_param_names, registered_param_names)

  return final_attributes


def _CreateAttribute(data):
  """Creates a single resource attribute from YAML data.

  Args:
    data: {}, The dict of data from the YAML file for this single attribute.

  Returns:
    ResourceParameterAttributeConfig, the generated attribute.
  """
  attribute_name = data['attribute_name']
  help_text = data['help']

  fallthrough_data = data.get('fallthroughs', [])
  fallthroughs = [
      deps.Fallthrough(util.Hook.FromPath(f['hook']), hint=f['hint'])
      for f in fallthrough_data]

  prop_string = data.get('property')
  prop = properties.FromString(prop_string) if prop_string else None
  prop = prop or _DEFAULT_PROPS.get(attribute_name)
  if prop:
    fallthroughs.insert(0, deps.PropertyFallthrough(prop))

  completion_id_field = data.get('completion_id_field')
  completion_request_params = data.get('completion_request_params', [])
  final_params = {
      param.get('fieldName'): param.get('value')
      for param in completion_request_params}

  completer = data.get('completer')
  attribute = concepts.ResourceParameterAttributeConfig(
      name=attribute_name, help_text=help_text, completer=completer,
      fallthroughs=fallthroughs,
      completion_id_field=completion_id_field,
      completion_request_params=final_params)

  return (data['parameter_name'], attribute)
