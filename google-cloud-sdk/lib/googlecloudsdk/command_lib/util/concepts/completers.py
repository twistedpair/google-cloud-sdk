# Copyright 2018 Google Inc. All Rights Reserved.
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
"""completers for resource library."""

from __future__ import absolute_import
from apitools.base.protorpclite import messages

from googlecloudsdk.api_lib.util import resource as resource_lib  # pylint: disable=unused-import
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util import completers
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.apis import registry
from googlecloudsdk.command_lib.util.concepts import resource_parameter_info
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

import six
import typing  # pylint: disable=unused-import

DEFAULT_ID_FIELD = 'name'
_PROJECTS_COLLECTION = 'cloudresourcemanager.projects'
_PROJECTS_STATIC_PARAMS = {
    'filter': 'lifecycleState:ACTIVE'}
_PROJECTS_ID_FIELD = 'projectId'


class Error(exceptions.Error):
  """Base error class for this module."""


class ResourceArgumentCompleter(completers.ResourceCompleter):
  """A completer for an argument that's part of a resource argument."""

  def __init__(self, resource_spec, collection_info, method,
               static_params=None, id_field=None, param=None, **kwargs):
    """Initializes."""
    self.resource_spec = resource_spec  # type: concepts.ResourceSpec
    self._method = method  # type: registry.APIMethod
    self._static_params = static_params or {}  # type: dict
    self.id_field = id_field or DEFAULT_ID_FIELD  # type: str
    collection_name = collection_info.full_name
    api_version = collection_info.api_version
    super(ResourceArgumentCompleter, self).__init__(
        collection=collection_name,
        api_version=api_version,
        param=param,
        parse_all=True,
        **kwargs)

  @property
  def method(self):
    """Gets the list method for the collection.

    Returns:
      googlecloudsdk.command_lib.util.apis.registry.APIMethod, the method.
    """
    return self._method

  def _GetUpdaters(self):
    # type: (...) -> dict
    """Helper function to build dict of updaters."""
    # Find the attribute that matches the final param of the collection for this
    # completer.
    final_param = self.collection_info.GetParams('')[-1]
    for i, attribute in enumerate(self.resource_spec.attributes):
      if self.resource_spec.ParamName(attribute.name) == final_param:
        attribute_idx = i
        break
    else:
      attribute_idx = 0

    updaters = {}
    for i, attribute in enumerate(
        self.resource_spec.attributes[:attribute_idx]):
      completer = CompleterForAttribute(self.resource_spec, attribute.name)
      if completer:
        updaters[self.resource_spec.ParamName(attribute.name)] = (completer,
                                                                  True)
      else:
        updaters[self.resource_spec.ParamName(attribute.name)] = (None,
                                                                  False)
    return updaters

  def ParameterInfo(self, parsed_args, argument):
    # type: (...) -> resource_parameter_info.ResourceParameterInfo
    """Builds a ResourceParameterInfo object.

    Args:
      parsed_args: the namespace.
      argument: unused.

    Returns:
      ResourceParameterInfo, the parameter info for runtime information.
    """
    resource_info = parsed_args.CONCEPTS.ArgNameToConceptInfo(argument.dest)

    updaters = self._GetUpdaters()

    return resource_parameter_info.ResourceParameterInfo(
        resource_info, parsed_args, argument, updaters=updaters,
        collection=self.collection)

  def Update(self, parameter_info, aggregations):
    # type: (...) -> typing.Optional[list[list[str]]]
    if self.method is None:
      return None
    log.info(
        'Cache query parameters={} aggregations={}'
        'resource info={}'.format(
            [(p, parameter_info.GetValue(p))
             for p in self.collection_info.GetParams('')],
            [(p.name, p.value) for p in aggregations],
            parameter_info.resource_info.attribute_to_args_map))
    try:
      query = self.BuildListQuery(parameter_info, aggregations)
    except Exception as e:  # pylint: disable=broad-except
      if properties.VALUES.core.print_completion_tracebacks.GetBool():
        raise
      log.info(six.text_type(e).rstrip())
      raise Error(u'Could not build query to list completions: {} {}'.format(
          type(e), six.text_type(e).rstrip()))
    try:
      response = self.method.Call(query)
      response_collection = self.method.collection
      items = [self._ParseResponse(r, response_collection,
                                   parameter_info=parameter_info,
                                   aggregations=aggregations)
               for r in response]
      log.info('cache items={}'.format(
          [i.RelativeName() for i in items]))
    except Exception as e:  # pylint: disable=broad-except
      if properties.VALUES.core.print_completion_tracebacks.GetBool():
        raise
      log.info(six.text_type(e).rstrip())
      # Give user more information if they hit an apitools validation error,
      # which probably means that they haven't provided enough information
      # for us to complete.
      if isinstance(e, messages.ValidationError):
        raise Error(u'Update query failed, may not have enough information to '
                    u'list existing resources: {} {}'.format(
                        type(e), six.text_type(e).rstrip()))
      raise Error(u'Update query [{}]: {} {}'.format(
          query, type(e), six.text_type(e).rstrip()))

    return [self.StringToRow(item.RelativeName()) for item in items]

  def _ParseResponse(self, response, response_collection,
                     parameter_info=None, aggregations=None):
    # type: (...) -> typing.Optional[resources.Resource]
    """Gets a resource ref from a single item in a list response."""
    params = {}
    parent_ref = self.GetParentRef(parameter_info, aggregations=aggregations)
    if parent_ref:
      params = parent_ref.AsDict()
    param_names = response_collection.detailed_params
    for param in param_names:
      val = getattr(response, param, None)
      if val is not None:
        params[param] = val

    line = getattr(response, self.id_field, '')
    return resources.REGISTRY.Parse(
        line, collection=response_collection.full_name, params=params)

  def _GetAggregationsValuesDict(self, aggregations):
    # type: (...) -> dict
    """Build a {str: str} dict of name to value for aggregations."""
    aggregations_dict = {}
    aggregations = [] if aggregations is None else aggregations
    for aggregation in aggregations:
      if aggregation.value:
        aggregations_dict[aggregation.name] = aggregation.value
    return aggregations_dict

  def BuildListQuery(self, parameter_info, aggregations=None):
    # type: (...) -> typing.Optional[messages.Message]
    """Builds a list request to list values for the given argument.

    Args:
      parameter_info: the runtime ResourceParameterInfo object.
      aggregations: a list of _RuntimeParameter objects.

    Returns:
      The apitools request.
    """
    method = self.method
    if method is None:
      return None
    message = method.GetRequestType()()
    for field, value in six.iteritems(self._static_params):
      arg_utils.SetFieldInMessage(message, field, value)
    parent = self.GetParentRef(parameter_info,
                               aggregations=aggregations)
    if not parent:
      return message
    arg_utils.ParseResourceIntoMessage(parent, method, message)
    return message

  def GetParentRef(self, parameter_info, aggregations=None):
    # type: (...) -> typing.Optional[resources.Resource]
    """Gets the parent reference of the parsed parameters.

    Args:
      parameter_info: the runtime ResourceParameterInfo object.
      aggregations: a list of _RuntimeParameter objects.

    Returns:
      googlecloudsdk.core.resources.Resource, the parent reference | None, if
        no parent could be parsed.
    """
    param_values = {
        p: parameter_info.GetValue(p)
        for p in self.collection_info.GetParams('')[:-1]
    }
    aggregations_dict = self._GetAggregationsValuesDict(aggregations)
    for name, value in six.iteritems(aggregations_dict):
      if value and not param_values.get(name, None):
        param_values[name] = value
    final_param = self.collection_info.GetParams('')[-1]
    if param_values.get(final_param, None) is None:
      param_values[final_param] = 'fake'  # Stripped by resource.Parent() below.
    try:
      resource = resources.Resource(
          resources.REGISTRY,
          collection_info=self.collection_info,
          subcollection='',
          param_values=param_values,
          endpoint_url=None)
      return resource.Parent()
    except resources.Error:
      return None

  def __eq__(self, other):
    """Overrides."""
    # Not using type(self) because the class is created programmatically.
    if not isinstance(other, ResourceArgumentCompleter):
      return False
    return (self.resource_spec == other.resource_spec and
            self.collection == other.collection and
            self.method == other.method)


def _MatchCollection(resource_spec, attribute):
  # type: (concepts.ResourceSpec, concepts.Attribute) -> typing.Optional[str]
  """Gets the collection for an attribute in a resource."""
  resource_collection_info = resource_spec._collection_info  # pylint: disable=protected-access
  resource_collection = registry.APICollection(
      resource_collection_info)
  if resource_collection is None:
    return None
  if attribute == resource_spec.attributes[-1]:
    return resource_collection.name
  attribute_idx = resource_spec.attributes.index(attribute)
  api_name = resource_collection_info.api_name
  collections = registry.GetAPICollections(
      api_name,
      resource_collection_info.api_version)
  params = resource_collection.detailed_params[:attribute_idx + 1]
  for c in collections:
    if c.detailed_params == params:
      return c.name


def _GetCompleterCollectionInfo(resource_spec, attribute):
  # type: (concepts.ResourceSpec, concepts.Attribute) ->  typing.Optional[resource_lib.CollectionInfo]  # pylint: disable=line-too-long
  """Gets collection info for an attribute in a resource."""
  collection = _MatchCollection(resource_spec, attribute)
  if collection:
    full_collection_name = (resource_spec._collection_info.api_name + '.'  # pylint: disable=protected-access
                            + collection)
  # The CloudResourceManager projects collection can be used for "synthetic"
  # project resources that don't have their own method.
  elif attribute.name == 'project':
    full_collection_name = 'cloudresourcemanager.projects'
  else:
    return None
  return resources.REGISTRY.GetCollectionInfo(full_collection_name)


def _GetCollectionAndMethod(resource_spec, attribute_name):
  # type: (concepts.ResourceSpec, str) -> typing.Tuple[typing.Optional[dict], typing.Optional[str], typing.Optional[resource_lib.CollectionInfo], typing.Optional[registry.APIMethod]]  # pylint: disable=line-too-long
  """Gets static params, name, collection, method of attribute in resource."""
  for a in resource_spec.attributes:
    if a.name == attribute_name:
      attribute = a
      break
  else:
    raise AttributeError(
        'Attribute [{}] not found in resource.'.format(attribute_name))
  static_params = attribute.completion_request_params
  id_field = attribute.completion_id_field
  collection_info = _GetCompleterCollectionInfo(resource_spec, attribute)
  if not collection_info:
    return static_params, id_field, None, None
  # If there is no appropriate list method for the collection, we can't auto-
  # create a completer.
  try:
    method = registry.GetMethod(
        collection_info.full_name, 'list',
        api_version=collection_info.api_version)
  except registry.UnknownMethodError:
    if (collection_info.full_name != _PROJECTS_COLLECTION
        and collection_info.full_name.split('.')[-1] == 'projects'):
      # The CloudResourceManager projects methods can be used for "synthetic"
      # project resources that don't have their own method.
      # This is a bit of a hack, so if any resource arguments come up for
      # which this doesn't work, a toggle should be added to the
      # ResourceSpec class to disable this.
      method = registry.GetMethod(_PROJECTS_COLLECTION, 'list')
      static_params = _PROJECTS_STATIC_PARAMS
      id_field = _PROJECTS_ID_FIELD
    else:
      method = None
  except registry.Error:
    method = None
  return static_params, id_field, collection_info, method


def _GetMethod(resource_spec, attribute_name):
  # type: (concepts.ResourceSpec, str) -> typing.Optional[registry.APIMethod]
  """Get the APIMethod for an attribute in a resource."""
  _, _, _, method = _GetCollectionAndMethod(resource_spec, attribute_name)
  return method


def CompleterForAttribute(resource_spec, attribute_name):
  """Gets a resource argument completer for a specific attribute."""

  class Completer(ResourceArgumentCompleter):
    """A specific completer for this attribute and resource."""

    def __init__(self, resource_spec=resource_spec,
                 attribute_name=attribute_name, **kwargs):
      params, id_field, collection_info, method = _GetCollectionAndMethod(
          resource_spec, attribute_name)

      super(Completer, self).__init__(
          resource_spec,
          collection_info,
          method,
          static_params=params,
          id_field=id_field,
          param=resource_spec.ParamName(attribute_name),
          **kwargs)

    @classmethod
    def validate(cls):
      """Checks whether the completer is valid (has a list method)."""
      return bool(_GetMethod(resource_spec, attribute_name))

  if not Completer.validate():
    return None

  return Completer

