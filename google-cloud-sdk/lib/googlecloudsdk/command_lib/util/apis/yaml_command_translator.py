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

"""A yaml to calliope command translator."""

from apitools.base.protorpclite import messages as apitools_messages
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import command_loading
from googlecloudsdk.command_lib.util.apis import arg_marshalling
from googlecloudsdk.command_lib.util.apis import registry
from googlecloudsdk.command_lib.util.apis import yaml_command_schema
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io


class Translator(command_loading.YamlCommandTranslator):
  """Class that implements the calliope translator interface."""

  def Translate(self, path, command_data):
    spec = yaml_command_schema.CommandData(path[-1], command_data)
    c = CommandBuilder(spec)
    return c.Generate()


class CommandBuilder(object):
  """Generates calliope commands based on the yaml spec."""

  IGNORED_FLAGS = {'project'}

  def __init__(self, spec):
    self.spec = spec
    self.is_list = (self.spec.command_type ==
                    yaml_command_schema.CommandType.LIST)
    self.method = registry.GetMethod(
        self.spec.request.collection, self.spec.request.method,
        self.spec.request.api_version)
    self.arg_generator = arg_marshalling.ArgumentGenerator(
        self.method, self.spec.resource_arg.request_params,
        is_positional=self.spec.command_type.resource_arg_is_positional,
        clean_surface=True)

  def Generate(self):
    """Generates a calliope command from the yaml spec.

    Raises:
      ValueError: If we don't know how to generate the given command type (this
        is not actually possible right now due to the enum).

    Returns:
      calliope.base.Command, The command that implements the spec.
    """
    if self.spec.command_type == yaml_command_schema.CommandType.DESCRIBE:
      command = self._GenerateDescribeCommand()
    elif self.spec.command_type == yaml_command_schema.CommandType.LIST:
      command = self._GenerateListCommand()
    elif self.spec.command_type == yaml_command_schema.CommandType.DELETE:
      command = self._GenerateDeleteCommand()
    else:
      raise ValueError('Unknown command type')

    self._ConfigureGlobalAttributes(command)
    return command

  def _GenerateDescribeCommand(self):
    """Generates a Describe command."""

    # pylint: disable=no-self-argument, The class closure throws off the linter
    # a bit. We want to use the generator class, not the class being generated.
    # pylint: disable=protected-access, The linter gets confused about 'self'
    # and thinks we are accessing something protected.
    class Command(base.DescribeCommand):

      @staticmethod
      def Args(parser):
        self._CommonArgs(parser)

      def Run(self_, args):
        unused_ref, response = self._CommonRun(args)
        return response

    return Command

  def _GenerateListCommand(self):
    """Generates a List command."""

    # pylint: disable=no-self-argument, The class closure throws off the linter
    # a bit. We want to use the generator class, not the class being generated.
    # pylint: disable=protected-access, The linter gets confused about 'self'
    # and thinks we are accessing something protected.
    class Command(base.ListCommand):

      @staticmethod
      def Args(parser):
        self._CommonArgs(parser)
        # Remove the URI flag if we don't know how to generate URIs for this
        # resource.
        if not self.spec.resource_arg.response_id_field:
          base.URI_FLAG.RemoveFromParser(parser)

      def Run(self_, args):
        self._RegisterURIFunc(args)
        unused_ref, response = self._CommonRun(args)
        return response

    return Command

  def _GenerateDeleteCommand(self):
    """Generates a Delete command."""

    # pylint: disable=no-self-argument, The class closure throws off the linter
    # a bit. We want to use the generator class, not the class being generated.
    # pylint: disable=protected-access, The linter gets confused about 'self'
    # and thinks we are accessing something protected.
    class Command(base.DeleteCommand):

      @staticmethod
      def Args(parser):
        self._CommonArgs(parser)
        if self.spec.async:
          base.ASYNC_FLAG.AddToParser(parser)

      def Run(self_, args):
        ref, response = self._CommonRun(args)
        if self.spec.async and not args.async:
          poller = AsyncOperationPoller(
              self.spec, ref, extract_resource_result=False)
          operation_ref = resources.REGISTRY.Parse(
              getattr(response, self.spec.async.response_name_field),
              collection=self.spec.async.collection)
          response = waiter.WaitFor(
              poller, operation_ref,
              'Deleting resource: {name}'.format(name=ref.RelativeName()))

        # TODO(b/64147277): Include the resource 'kind' here for better UX.
        log.DeletedResource(ref.RelativeName())
        return response

    return Command

  def _CommonArgs(self, parser):
    """Performs argument actions common to all commands.

    Args:
      parser: The argparse parser.
    """
    args = self.arg_generator.GenerateArgs(include_global_list_flags=False)
    for name, arg in args.iteritems():
      if name not in CommandBuilder.IGNORED_FLAGS:
        arg.AddToParser(parser)
    if self.spec.output.format:
      parser.display_info.AddFormat(self.spec.output.format)

  def _CommonRun(self, args):
    """Performs run actions common to all commands.

    Args:
      args: The argparse parser.

    Returns:
      (resources.Resource, response), A tuple of the parsed resource reference
      and the API response from the method call.
    """
    ref = self.arg_generator.GetRequestResourceRef(args)
    if self.spec.input.confirmation_prompt:
      console_io.PromptContinue(
          self.spec.input.confirmation_prompt.format(name=ref.RelativeName()),
          throw_if_unattended=True, cancel_on_no=True)
    response = self.method.Call(self.arg_generator.CreateRequest(args),
                                limit=self.arg_generator.Limit(args),
                                page_size=self.arg_generator.PageSize(args))
    return ref, response

  def _RegisterURIFunc(self, args):
    """Generates and registers a function to create a URI from a resource.

    Args:
      args: The argparse namespace.

    Returns:
      f(resource) -> str, A function that converts the given resource payload
      into a URI.
    """
    def URIFunc(resource):
      id_value = getattr(resource, self.spec.resource_arg.response_id_field)
      ref = self.arg_generator.GetResponseResourceRef(id_value, args)
      return ref.SelfLink()
    args.GetDisplayInfo().AddUriFunc(URIFunc)

  def _ConfigureGlobalAttributes(self, command):
    """Configures top level attributes of the generated command.

    Args:
      command: The command being generated.
    """
    if self.spec.is_hidden:
      command = base.Hidden(command)
    if self.spec.release_tracks:
      command = base.ReleaseTracks(*self.spec.release_tracks)(command)
    command.detailed_help = self.spec.help_text


class AsyncOperationPoller(waiter.OperationPoller):
  """An implementation of a operation poller."""

  def __init__(self, spec, ref, extract_resource_result=True):
    """Creates the poller.

    Args:
      spec: yaml_command_schema.CommandData, the spec for the command being
        generated.
      ref: resources.Resource, The resource reference for the resource being
        operated on (not the operation itself).
      extract_resource_result: bool, True to return the original resource as
        the result or false to just return the operation response when it is
        done. You would set this to False for things like Delete where the
        resource no longer exists when the operation is done.
    """
    self.spec = spec
    self.resource_ref = ref
    self.extract_resource_result = extract_resource_result
    self.method = registry.GetMethod(
        spec.async.collection, spec.async.method,
        api_version=spec.request.api_version)

  def IsDone(self, operation):
    """Overrides."""
    result = getattr(operation, self.spec.async.state.field)
    if isinstance(result, apitools_messages.Enum):
      result = result.name
    if (result in self.spec.async.state.success_values or
        result in self.spec.async.state.error_values):
      # We found a value that means it is done.
      error = getattr(operation, self.spec.async.error.field)
      if not error and result in self.spec.async.state.error_values:
        error = 'The operation failed.'
      # If we succeeded but there is an error, or if an error was detected.
      if error:
        raise waiter.OperationError(error)
      return True

    return False

  def Poll(self, operation_ref):
    """Overrides.

    Args:
      operation_ref: googlecloudsdk.core.resources.Resource.

    Returns:
      fetched operation message.
    """
    return self.method.Call(
        self.method.GetRequestType()(**operation_ref.AsDict()))

  def GetResult(self, operation):
    """Overrides.

    Args:
      operation: api_name_messages.Operation.

    Returns:
      result of result_service.Get request.
    """
    if not self.extract_resource_result:
      return operation
    method = registry.GetMethod(
        self.spec.request.collection, self.spec.async.resource_get_method,
        api_version=self.spec.request.api_version)
    return method.Call(method.GetRequestType()(**self.resource_ref.AsDict()))
