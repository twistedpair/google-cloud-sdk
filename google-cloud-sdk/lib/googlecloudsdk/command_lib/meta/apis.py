# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Utilities for the gcloud meta apis surface."""

import re

from apitools.base.protorpclite import messages
from apitools.base.py import  exceptions as apitools_exc
from googlecloudsdk.api_lib.util import apis_internal
from googlecloudsdk.api_lib.util import resource
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as c_exc
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.resource import resource_property
from googlecloudsdk.third_party.apis import apis_map


def APICompleter(**_):
  return [a.name for a in GetAllAPIs()]


def CollectionCompleter(**_):
  return [c.full_name for c in GetAPICollections()]


def MethodCompleter(prefix, parsed_args, **_):
  del prefix
  collection = getattr(parsed_args, 'collection', None)
  if not collection:
    return []
  return [m.name for m in GetMethods(collection)]


API_VERSION_FLAG = base.Argument(
    '--api-version',
    help='The version of the given API to use. If not provided, the default '
         'version of the API will be used.')


COLLECTION_FLAG = base.Argument(
    '--collection',
    required=True,
    completer=CollectionCompleter,
    help='The name of the collection to specify the method for.')


NAME_SEPARATOR = '.'


# TODO(b/38000796): Use the same defaults as the normal resource parser.
DEFAULT_PARAMS = {
    'project': properties.VALUES.core.project.Get,
    'projectId': properties.VALUES.core.project.Get,
    'projectsId': properties.VALUES.core.project.Get,
}


class Error(exceptions.Error):
  pass


class NoDefaultVersionError(Error):

  def __init__(self, api_name):
    super(NoDefaultVersionError, self).__init__(
        'API [{api}] does not have a default version. You must specify which '
        'version to use.'.format(api=api_name)
    )


class UnknownCollectionError(Error):

  def __init__(self, api_name, api_version, collection):
    super(UnknownCollectionError, self).__init__(
        'Collection [{collection}] does not exist for [{api}] [{version}].'
        .format(collection=collection, api=api_name, version=api_version)
    )


class UnknownMethodError(Error):

  def __init__(self, method, collection):
    super(UnknownMethodError, self).__init__(
        'Method [{method}] does not exist for collection [{collection}].'
        .format(method=method, collection=collection)
    )


class APICallError(Error):
  pass


class API(object):
  """A data holder for returning API data for display."""

  def __init__(self, name, version, is_default, base_url):
    self.name = name
    self.version = version
    self.is_default = is_default
    self.base_url = base_url


class APICollection(object):
  """A data holder for collection information for an API."""

  def __init__(self, collection_info):
    self.api_name = collection_info.api_name
    self.api_version = collection_info.api_version
    self.base_url = collection_info.base_url
    self.name = collection_info.name
    self.full_name = collection_info.full_name
    self.detailed_path = collection_info.GetPath('')
    self.detailed_params = collection_info.GetParams('')
    self.path = collection_info.path
    self.params = collection_info.params


class APIMethod(object):
  """A data holder for method information for an API collection."""

  def __init__(self, service, name, api_collection, method_config):
    self._service = service
    self._method_name = name

    self.collection = api_collection

    self.name = method_config.method_id
    dotted_path = self.collection.full_name + NAME_SEPARATOR
    if self.name.startswith(dotted_path):
      self.name = self.name[len(dotted_path):]

    self.path = _RemoveVersionPrefix(
        self.collection.api_version, method_config.relative_path)
    self.params = method_config.ordered_params
    if method_config.flat_path:
      self.detailed_path = _RemoveVersionPrefix(
          self.collection.api_version, method_config.flat_path)
      self.detailed_params = resource.GetParamsFromPath(method_config.flat_path)
    else:
      self.detailed_path = self.path
      self.detailed_params = self.params

    self.http_method = method_config.http_method
    self.request_field = method_config.request_field
    self.request_type = method_config.request_type_name
    self.response_type = method_config.response_type_name

  def GetRequestType(self):
    """Gets the apitools request class for this method."""
    return self._service.GetRequestType(self._method_name)

  def RequestCollection(self):
    """Gets the collection that should be used to parse resources for this call.

    Methods apply to elements of a collection. The resource argument is always
    of the type of that collection.  List is an exception where you are listing
    items of that collection so the argument to be provided is that of the
    parent collection. This method returns the collection that should be used
    to parse the resource for this specific method.

    Returns:
      APICollection, The collection to use or None if no parent collection could
      be found.
    """
    if self.detailed_params == self.collection.detailed_params:
      return self.collection
    collections = GetAPICollections(
        self.collection.api_name, self.collection.api_version)
    for c in collections:
      if self.detailed_params == c.detailed_params:
        return c
    return None

  def ResourceFieldNames(self):
    """Gets the field names that are part of the resource that is parsed.

    This is the detailed parameters of RequestCollection()

    Returns:
      [str], The field names.
    """
    request_collection = self.RequestCollection()
    if request_collection:
      return request_collection.detailed_params
    return []

  def RequestFieldNames(self):
    """Gets the fields that are actually a part of the request message.

    For APIs that use atomic names, this will only be the single name parameter
    (and any other message fields) but not the detailed parameters.

    Returns:
      [str], The field names.
    """
    return [f.name for f in self.GetRequestType().all_fields()]

  def GetDefaultParams(self):
    """Gets default values for parameters in the request method.

    Returns:
      {str, value}, A mapping of field name to value.
    """
    default_params = {k: v() for k, v in DEFAULT_PARAMS.iteritems()
                      if k in self.ResourceFieldNames()}
    return default_params

  def Call(self, *args, **kwargs):
    """Executes this method with the given arguments."""
    try:
      return getattr(self._service, self._method_name)(*args, **kwargs)
    except apitools_exc.InvalidUserInputError as e:
      log.debug('', exc_info=True)
      raise APICallError(e.message)


def _RemoveVersionPrefix(api_version, path):
  """Trims the version number off the front of a URL path if present."""
  if not path:
    return None
  if path.startswith(api_version):
    return path[len(api_version) + 1:]
  return path


def GetAPI(api_name, api_version=None):
  """Get a specific API definition.

  Args:
    api_name: str, The name of the API.
    api_version: str, The version string of the API.

  Returns:
    API, The API definition.
  """
  api_version = api_version or _GetDefaultVersion(api_name)
  # pylint: disable=protected-access
  api_def = apis_internal._GetApiDef(api_name, api_version)
  api_client = apis_internal._GetClientClassFromDef(api_def)
  return API(api_name, api_version,
             api_def.default_version, api_client.BASE_URL)


def GetAllAPIs():
  """Gets all registered APIs.

  Returns:
    [API], A list of API definitions.
  """
  all_apis = []
  for api_name, versions in apis_map.MAP.iteritems():
    for api_version, _ in versions.iteritems():
      all_apis.append(GetAPI(api_name, api_version))
  return all_apis


def _SplitFullCollectionName(collection):
  return tuple(collection.split(NAME_SEPARATOR, 1))


def GetAPICollections(api_name=None, api_version=None):
  """Gets the registered collections for the given API version.

  Args:
    api_name: str, The name of the API or None for all apis.
    api_version: str, The version string of the API or None to use the default
      version.

  Returns:
    [APICollection], A list of the registered collections.
  """
  if api_name:
    all_apis = {api_name: api_version or _GetDefaultVersion(api_name)}
  else:
    all_apis = {x.name: x.version for x in GetAllAPIs() if x.is_default}

  collections = []
  for n, v in all_apis.iteritems():
    # pylint:disable=protected-access
    collections.extend(
        [APICollection(c) for c in apis_internal._GetApiCollections(n, v)])
  return collections


def GetAPICollection(full_collection_name, api_version=None):
  """Gets the given collection for the given API version.

  Args:
    full_collection_name: str, The collection to get including the api name.
    api_version: str, The version string of the API or None to use the default
      for this API.

  Returns:
    APICollection, The requested API collection.

  Raises:
    UnknownCollectionError: If the collection does not exist for the given API
    and version.
  """
  api_name, collection = _SplitFullCollectionName(full_collection_name)
  api_version = api_version or _GetDefaultVersion(api_name)
  collections = GetAPICollections(api_name, api_version)
  for c in collections:
    if c.name == collection:
      return c
  raise UnknownCollectionError(api_name, api_version, collection)


def _GetDefaultVersion(api_name):
  """Gets the default version for the given api."""
  # pylint:disable=protected-access
  api_version = apis_internal._GetDefaultVersion(api_name)
  if not api_version:
    raise NoDefaultVersionError(api_name)
  log.warning('Using default version [{}] for api [{}].'
              .format(api_version, api_name))
  return api_version


def GetMethod(full_collection_name, method, api_version=None, no_http=True):
  """Gets the specification for the given API method.

  Args:
    full_collection_name: str, The collection including the api name.
    method: str, The name of the method.
    api_version: str, The version string of the API or None to use the default
      for this API.
    no_http: bool, True to not create an authenticated http object for this
      API Client.

  Returns:
    APIMethod, The method specification.

  Raises:
    UnknownMethodError: If the method does not exist on the collection.
  """
  methods = GetMethods(full_collection_name, api_version=api_version,
                       no_http=no_http)
  for m in methods:
    if m.name == method:
      return m
  raise UnknownMethodError(method, full_collection_name)


def GetMethods(full_collection_name, api_version=None, no_http=True):
  """Gets all the methods available on the given collection.

  Args:
    full_collection_name: str, The collection including the api name.
    api_version: str, The version string of the API or None to use the default
      for this API.
    no_http: bool, True to not create an authenticated http object for this
      API Client.

  Returns:
    [APIMethod], The method specifications.
  """
  api_name, collection = _SplitFullCollectionName(full_collection_name)
  api_version = api_version or _GetDefaultVersion(api_name)
  # pylint:disable=protected-access
  client = apis_internal._GetClientInstance(api_name, api_version,
                                            no_http=no_http)
  api_collection = GetAPICollection(full_collection_name,
                                    api_version=api_version)
  service = getattr(client, collection.replace(NAME_SEPARATOR, '_'))

  method_names = service.GetMethodsList()
  method_configs = [(name, service.GetMethodConfig(name))
                    for name in method_names]
  return [APIMethod(service, name, api_collection, config)
          for name, config in method_configs]


class MethodDynamicPositionalAction(parser_extensions.DynamicPositionalAction):
  """A DynamicPositionalAction that adds flags for a given method to the parser.

  Based on the value given for method, it looks up the valid fields for that
  method call and adds those flags to the parser.
  """

  def GenerateArgs(self, namespace, method_name):
    # Get the collection from the existing parsed args.
    full_collection_name = getattr(namespace, 'collection', None)
    api_version = getattr(namespace, 'api_version', None)
    if not full_collection_name:
      raise c_exc.RequiredArgumentException(
          '--collection',
          'The collection name must be specified before the API method.')

    # Look up the method and get all the args for it.
    # TODO(b/38000796): It's possible that api_version hasn't been parsed yet
    # so we are generating the wrong args.
    method = GetMethod(full_collection_name, method_name,
                       api_version=api_version)
    arg_generator = ArgumentGenerator(method)
    args = arg_generator.MessageFieldFlags()
    args.update(arg_generator.ResourceFlags())
    args.update(arg_generator.ResourceArg())
    # Remove any args that didn't actually get generated.
    return args

  def Completions(self, prefix, parsed_args, **kwargs):
    return MethodCompleter(prefix, parsed_args, **kwargs)


class ArgumentGenerator(object):
  """Class to generate argparse flags from apitools message fields."""

  TYPES = {
      messages.Variant.DOUBLE: float,
      messages.Variant.FLOAT: float,

      messages.Variant.INT64: long,
      messages.Variant.UINT64: long,
      messages.Variant.SINT64: long,

      messages.Variant.INT32: int,
      messages.Variant.UINT32: int,
      messages.Variant.SINT32: int,

      messages.Variant.BOOL: bool,
      messages.Variant.STRING: str,

      # TODO(b/38000796): Do something with bytes.
      messages.Variant.BYTES: None,
      messages.Variant.ENUM: None,
      messages.Variant.MESSAGE: None,
  }

  def __init__(self, method):
    """Creates a new Argument Generator.

    Args:
      method: APIMethod, The method to generate arguments for.
    """
    self.method = method

  def ResourceArg(self):
    """Gets the positional argument that represents the resource.

    Returns:
      {str, calliope.base.Argument}, The argument.
    """
    if not self.method.RequestCollection():
      log.warning('Not generating resource arg')
      return {}
    return {
        'resource': base.Argument(
            'resource',
            nargs='?',
            help='The GRI for the resource being operated on.')}

  def ResourceFlags(self):
    """Get the arguments to add to the parser that appear in the method path.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    message = self.method.GetRequestType()
    field_helps = self._FieldHelpDocs(message)
    default_help = 'For substitution into: ' + self.method.detailed_path

    args = {}
    for param in set(self.method.ResourceFieldNames()):
      args[param] = base.Argument(
          # TODO(b/38000796): Consider not using camel case for flags.
          '--' + param,
          metavar=resource_property.ConvertToAngrySnakeCase(param),
          category='RESOURCE',
          type=str,
          help=field_helps.get(param, default_help))
    return args

  def MessageFieldFlags(self):
    """Get the arguments to add to the parser that appear in the method body.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    return self._MessageFieldFlags('', self.method.GetRequestType())

  def _MessageFieldFlags(self, prefix, message):
    """Get the arguments to add to the parser that appear in the method body.

    Args:
      prefix: str, A string to prepend to the name of the flag. This is used
        for flags representing fields of a submessage.
      message: The apitools message to generate the flags for.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    args = {}
    field_helps = self._FieldHelpDocs(message)
    for field in message.all_fields():
      name = prefix + field.name
      if field.variant == messages.Variant.MESSAGE:
        if (name == self.method.request_field and
            name.lower().endswith('request')):
          name = 'request'
        field_help = field_helps.get(field.name, None)
        group = base.ArgumentGroup(
            name, description=(name + ': ' + field_help) if field_help else '')
        for arg in self._MessageFieldFlags(name + '.', field.type).values():
          group.AddArgument(arg)
        args[name] = group
      else:
        args[name] = self._FlagForMessageField(name, field, field_helps)
    return {k: v for k, v in args.iteritems() if v is not None}

  def _FlagForMessageField(self, name, field, field_helps):
    """Gets a flag for a single field in a message.

    Args:
      name: The name of the field.
      field: The apitools field object.
      field_helps: {str: str}, A mapping of field name to help text.

    Returns:
      {str: str}, A mapping of field name to help text.
    """
    help_text = field_helps.get(field.name, None)
    if self._IsOutputField(help_text):
      return None
    variant = field.variant
    t = ArgumentGenerator.TYPES.get(variant, None)
    choices = None
    if variant == messages.Variant.ENUM:
      choices = field.type.names()
    return base.Argument(
        # TODO(b/38000796): Consider not using camel case for flags.
        '--' + name,
        metavar=resource_property.ConvertToAngrySnakeCase(field.name),
        category='MESSAGE',
        action='store',
        type=t,
        choices=choices,
        help=help_text,
    )

  def _FieldHelpDocs(self, message):
    """Gets the help text for the fields in the request message.

    Args:
      message: The apitools message.

    Returns:
      {str: str}, A mapping of field name to help text.
    """
    field_helps = {}
    current_field = None

    match = re.search(r'^\s+Fields:.*$', message.__doc__, re.MULTILINE)
    if not match:
      # Couldn't find any fields at all.
      return field_helps

    for line in message.__doc__[match.end():].splitlines():
      match = re.match(r'^\s+(\w+): (.*)$', line)
      if match:
        # This line is the start of a new field.
        current_field = match.group(1)
        field_helps[current_field] = match.group(2).strip()
      elif current_field:
        # Append additional text to the in progress field.
        current_text = field_helps.get(current_field, '')
        field_helps[current_field] = current_text + ' ' + line.strip()

    return field_helps

  def _IsOutputField(self, help_text):
    """Determines if the given field is output only based on help text."""
    return help_text and help_text.startswith('[Output Only]')

