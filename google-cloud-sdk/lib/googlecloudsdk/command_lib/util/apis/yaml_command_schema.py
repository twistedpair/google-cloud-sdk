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

"""Data objects to support the yaml command schema."""


from enum import Enum

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import base
from googlecloudsdk.core import module_util


class Error(Exception):
  """Base class for module errors."""
  pass


class InvalidSchemaError(Error):
  """Error for when a yaml command is malformed."""
  pass


NAME_FORMAT_KEY = '__name__'
REL_NAME_FORMAT_KEY = '__relative_name__'
RESOURCE_TYPE_FORMAT_KEY = '__resource_type__'


class CommandData(object):

  def __init__(self, name, data):
    self.is_hidden = data.get('is_hidden', False)
    self.release_tracks = [
        base.ReleaseTrack.FromId(i) for i in data.get('release_tracks', [])]
    self.command_type = CommandType.ForName(data.get('command_type', name))
    self.help_text = data['help_text']
    self.request = Request(self.command_type, data['request'])
    self.response = Response(data.get('response', {}))
    async_data = data.get('async')
    if self.command_type == CommandType.WAIT and not async_data:
      raise InvalidSchemaError('Wait commands must include an async section.')
    self.async = Async(async_data) if async_data else None
    self.arguments = Arguments(data['arguments'])
    self.input = Input(self.command_type, data.get('input', {}))
    self.output = Output(data.get('output', {}))


class CommandType(Enum):
  """An enum for the types of commands the generator supports.

  Attributes:
    default_method: str, The name of the API method to use by default for this
      type of command.
  """
  DESCRIBE = 'get'
  LIST = 'list'
  DELETE = 'delete'
  CREATE = 'create'
  WAIT = 'get'
  # Generic commands are those that don't extend a specific calliope command
  # base class.
  GENERIC = None

  def __init__(self, default_method):
    # Set the value to a unique object so multiple enums can have the same
    # default method.
    self._value_ = object()
    self.default_method = default_method

  @classmethod
  def ForName(cls, name):
    try:
      return CommandType[name.upper()]
    except KeyError:
      return CommandType.GENERIC


class Request(object):

  def __init__(self, command_type, data):
    self.collection = data['collection']
    self.api_version = data.get('api_version')
    self.method = data.get('method', command_type.default_method)
    if not self.method:
      raise InvalidSchemaError(
          'request.method was not specified and there is no default for this '
          'command type.')
    self.resource_method_params = data.get('resource_method_params', {})
    self.static_fields = data.get('static_fields', {})
    self.modify_request_hooks = [
        Hook.FromPath(p) for p in data.get('modify_request_hooks', [])]
    self.create_request_hook = Hook.FromData(data, 'create_request_hook')
    self.issue_request_hook = Hook.FromData(data, 'issue_request_hook')


class Response(object):

  def __init__(self, data):
    self.result_attribute = data.get('result_attribute')
    self.error = ResponseError(data['error']) if 'error' in data else None


class ResponseError(object):

  def __init__(self, data):
    self.field = data.get('field', 'error')
    self.code = data.get('code')
    self.message = data.get('message')


class Async(object):

  def __init__(self, data):
    self.collection = data['collection']
    self.api_version = data.get('api_version')
    self.method = data.get('method', 'get')
    self.response_name_field = data.get('response_name_field', 'name')
    self.extract_resource_result = data.get('extract_resource_result', True)
    resource_get_method = data.get('resource_get_method')
    if not self.extract_resource_result and resource_get_method:
      raise InvalidSchemaError(
          'async.resource_get_method was specified but extract_resource_result '
          'is False')
    self.resource_get_method = resource_get_method or 'get'
    self.operation_get_method_params = data.get(
        'operation_get_method_params', {})
    self.result_attribute = data.get('result_attribute')
    self.state = AsyncStateField(data.get('state', {}))
    self.error = AsyncErrorField(data.get('error', {}))


class AsyncStateField(object):

  def __init__(self, data):
    self.field = data.get('field', 'done')
    self.success_values = data.get('success_values', [True])
    self.error_values = data.get('error_values', [])


class AsyncErrorField(object):

  def __init__(self, data):
    self.field = data.get('field', 'error')


class Arguments(object):
  """Everything about cli arguments are registered in this section."""

  def __init__(self, data):
    resource = data.get('resource')
    self.resource = Resource(resource) if resource else None
    self.additional_arguments_hook = Hook.FromData(
        data, 'additional_arguments_hook')
    self.params = [
        Argument.FromData(param_data) for param_data in data.get('params', [])]
    self.mutex_group_params = []
    for group_id, group_data in enumerate(data.get('mutex_groups', [])):
      group = MutexGroup.FromData(group_id, group_data)
      self.mutex_group_params.extend([
          Argument.FromData(param_data, group=group)
          for param_data in group_data.get('params', [])])


class Resource(object):

  def __init__(self, data):
    self.help_text = data['help_text']
    self.response_id_field = data.get('response_id_field')
    self.params = [
        Argument.FromData(param_data) for param_data in data.get('params', [])]


class MutexGroup(object):

  @classmethod
  def FromData(cls, group_id, data):
    return MutexGroup(group_id, required=data.get('required', False))

  def __init__(self, group_id, required=False):
    self.group_id = group_id
    self.required = required


class Argument(object):
  """Encapsulates data used to generate arguments.

  Most of the attributes of this object correspond directly to the schema and
  have more complete docs there.

  Attributes:
    api_field: The name of the field in the request that this argument values
      goes.
    arg_name: The name of the argument that will be generated. Defaults to the
      api_field if not set.
    help_text: The help text for the generated argument.
    metavar: The metavar for the generated argument. This will be generated
      automatically if not provided.
    completer: A completer for this argument.
    is_positional: Whether to make the argument positional or a flag.
    type: The type to use on the argparse argument.
    choices: A static map of choice to value the user types.
    default: The default for the argument.
    fallback: A function to call and use as the default for the argument.
    processor: A function to call to process the value of the argument before
      inserting it into the request.
    required: True to make this a required flag.
    hidden: True to make the argument hidden.
    action: An override for the argparse action to use for this argument.
    repeated: False to accept only one value when the request field is actually
      repeated.
    group: The MutexGroup that this argument is a part of.
    generate: False to not generate this argument. This can be used to create
      placeholder arg specs for defaults that don't actually need to be
      generated.
  """

  STATIC_ACTIONS = {'store', 'store_true'}

  @classmethod
  def FromData(cls, data, group=None):
    """Gets the arg definition from the spec data.

    Args:
      data: The spec data.
      group: MutexGroup, The group this arg is in or None.

    Returns:
      Argument, the parsed argument.

    Raises:
      InvalidSchemaError: if the YAML command is malformed.
    """
    api_field = data.get('api_field')
    arg_name = data.get('arg_name', api_field)
    if not arg_name:
      raise InvalidSchemaError(
          'An argument must have at least one of [api_field, arg_name].')
    is_positional = data.get('is_positional')

    action = data.get('action', None)
    if action and action not in Argument.STATIC_ACTIONS:
      action = Hook.FromPath(action)
    if not action:
      deprecation = data.get('deprecated')
      if deprecation:
        flag_name = arg_name if is_positional else '--' + arg_name
        action = actions.DeprecationAction(flag_name, **deprecation)

    if data.get('default') and data.get('fallback'):
      raise InvalidSchemaError(
          'An argument may have at most one of [default, fallback].')

    try:
      help_text = data['help_text']
    except KeyError:
      raise InvalidSchemaError('An argument must have help_text.')

    return Argument(
        api_field,
        arg_name,
        help_text,
        metavar=data.get('metavar'),
        completer=Hook.FromData(data, 'completer'),
        is_positional=is_positional,
        type=Hook.FromData(data, 'type'),
        choices=data.get('choices'),
        default=data.get('default'),
        fallback=Hook.FromData(data, 'fallback'),
        processor=Hook.FromData(data, 'processor'),
        required=data.get('required', False),
        hidden=data.get('hidden', False),
        action=action,
        repeated=data.get('repeated'),
        group=group
    )

  # pylint:disable=redefined-builtin, type param needs to match the schema.
  def __init__(self, api_field, arg_name, help_text, metavar=None,
               completer=None, is_positional=None, type=None, choices=None,
               default=None, fallback=None, processor=None, required=False,
               hidden=False, action=None, repeated=None, group=None,
               generate=True):
    self.api_field = api_field
    self.arg_name = arg_name
    self.help_text = help_text
    self.metavar = metavar
    self.completer = completer
    self.is_positional = is_positional
    self.type = type
    self.choices = choices
    self.default = default
    self.fallback = fallback
    self.processor = processor
    self.required = required
    self.hidden = hidden
    self.action = action
    self.repeated = repeated
    self.group = group
    self.generate = generate


class Input(object):

  def __init__(self, command_type, data):
    self.confirmation_prompt = data.get('confirmation_prompt')
    if not self.confirmation_prompt and command_type is CommandType.DELETE:
      self.confirmation_prompt = (
          'You are about to delete {{{}}} [{{{}}}]'.format(
              RESOURCE_TYPE_FORMAT_KEY, NAME_FORMAT_KEY))


class Output(object):

  def __init__(self, data):
    self.format = data.get('format')


class Hook(object):
  """Represents a Python code hook declared in the yaml spec.

  A code hook points to some python element with a module path, and attribute
  path like: package.module:class.attribute.

  If arguments are provided, first the function is called with the arguments
  and the return value of that is the hook that is used. For example:

  googlecloudsdk.calliope.arg_parsers:Duration:lower_bound=1s,upper_bound=1m
  """

  @classmethod
  def FromData(cls, data, key):
    """Gets the hook from the spec data.

    Args:
      data: The yaml spec
      key: The key to extract the hook path from.

    Returns:
      The Python element to call.
    """
    path = data.get(key)
    if path:
      return cls.FromPath(path)
    return None

  @classmethod
  def FromPath(cls, path):
    """Gets the hook from the function path.

    Args:
      path: str, The module path to the hook function.

    Returns:
      The Python element to call.
    """
    return _ImportPythonHook(path).GetHook()

  def __init__(self, attribute, kwargs=None):
    self.attribute = attribute
    self.kwargs = kwargs

  def GetHook(self):
    """Gets the Python element that corresponds to this hook.

    Returns:
      A Python element.
    """
    if self.kwargs is not None:
      return  self.attribute(**self.kwargs)
    return self.attribute


def _ImportPythonHook(path):
  """Imports the given python hook.

  Depending on what it is used for, a hook is a reference to a class, function,
  or attribute in Python code.

  Args:
    path: str, The path of the hook to import. It must be in the form of:
      package.module:attribute.attribute where the module path is separated from
      the class name and sub attributes by a ':'. Additionally, ":arg=value,..."
      can be appended to call the function with the given args and use the
      return value as the hook.

  Raises:
    InvalidSchemaError: If the given module or attribute cannot be loaded.

  Returns:
    Hook, the hook configuration.
  """
  parts = path.split(':')
  if len(parts) != 2 and len(parts) != 3:
    raise InvalidSchemaError(
        'Invalid Python hook: [{}]. Hooks must be in the format: '
        'package(.module)+:attribute(.attribute)*(:arg=value(,arg=value)*)?'
        .format(path))
  try:
    attr = module_util.ImportModule(parts[0] + ':' + parts[1])
  except module_util.ImportModuleError as e:
    raise InvalidSchemaError(
        'Could not import Python hook: [{}]. {}'.format(path, e))

  kwargs = None
  if len(parts) == 3:
    kwargs = {}
    for arg in parts[2].split(','):
      if not arg:
        continue
      arg_parts = arg.split('=')
      if len(arg_parts) != 2:
        raise InvalidSchemaError(
            'Invalid Python hook: [{}]. Args must be in the form arg=value,'
            'arg=value,...'.format(path))
      kwargs[arg_parts[0]] = arg_parts[1]

  return Hook(attr, kwargs)
