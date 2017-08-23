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

from googlecloudsdk.calliope import base


class CommandData(object):

  def __init__(self, name, data):
    self.is_hidden = data.get('is_hidden', False)
    self.release_tracks = [
        base.ReleaseTrack.FromId(i) for i in data.get('release_tracks', [])]
    self.command_type = CommandType[data.get('command_type', name).upper()]
    self.help_text = data['help_text']
    self.request = Request(self.command_type, data['request'])
    async_data = data.get('async', None)
    self.async = Async(async_data) if async_data else None
    self.resource_arg = ResourceArg(data['resource_arg'])
    self.input = Input(data.get('input', {}))
    self.output = Output(data.get('output', {}))


class CommandType(Enum):
  DESCRIBE = ('get', True)
  LIST = ('list', False)
  DELETE = ('delete', True)

  def __init__(self, default_method, resource_arg_is_positional):
    self.default_method = default_method
    self.resource_arg_is_positional = resource_arg_is_positional


class Request(object):

  def __init__(self, command_type, data):
    self.collection = data['collection']
    self.api_version = data.get('api_version', None)
    self.method = data.get('method', command_type.default_method)
    # TODO(b/64147277) There will eventually be a 'generic' command that doesn't
    # have a default method. Add a test for this then.
    if not self.method:
      raise ValueError('request.method was not specified and there is no '
                       'default for this command type.')


class Async(object):

  def __init__(self, data):
    self.collection = data['collection']
    self.method = data.get('method', 'get')
    self.response_name_field = data.get('response_name_field', 'name')
    self.resource_get_method = data.get('resource_get_method', 'get')
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


class ResourceArg(object):

  def __init__(self, data):
    self.help_text = data['help_text']
    self.response_id_field = data.get('response_id_field', None)
    self.request_params = {
        param: Argument(param, param_data)
        for param, param_data in data.get('request_params', {}).iteritems()}


class Argument(object):

  def __init__(self, param, data):
    self.help_text = data['help_text']
    self.arg_name = data.get('arg_name', param)
    self.completer = data.get('completer', None)


class Input(object):

  def __init__(self, data):
    self.confirmation_prompt = data.get('confirmation_prompt', None)


class Output(object):

  def __init__(self, data):
    self.format = data.get('format')
