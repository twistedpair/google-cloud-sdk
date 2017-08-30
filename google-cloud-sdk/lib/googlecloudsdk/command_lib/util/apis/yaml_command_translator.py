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

"""A yaml to calliope command translator.

Calliope allows you to register a hook that converts a yaml command spec into
a calliope command class. The Translator class in this module implements that
interface and provides generators for a yaml command spec. The schema for the
spec can be found in yaml_command_schema.yaml.
"""

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
    self.method = registry.GetMethod(
        self.spec.request.collection, self.spec.request.method,
        self.spec.request.api_version)
    arg_info = dict(self.spec.message_params)
    arg_info.update(self.spec.resource_arg.request_params)
    self.arg_generator = arg_marshalling.ArgumentGenerator(
        self.method, arg_info, builtin_args=CommandBuilder.IGNORED_FLAGS,
        clean_surface=True)
    self.resource_type = self.arg_generator.resource_arg_name

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
    elif self.spec.command_type == yaml_command_schema.CommandType.GENERIC:
      command = self._GenerateGenericCommand()
    else:
      raise ValueError('Unknown command type')

    self._ConfigureGlobalAttributes(command)
    return command

  def _GenerateDescribeCommand(self):
    """Generates a Describe command.

    A describe command has a single resource argument and an API method to call
    to get the resource. The result is returned using the default output format.

    Returns:
      calliope.base.Command, The command that implements the spec.
    """

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
    """Generates a List command.

    A list command operates on a single resource and has flags for the parent
    collection of that resource. Because it extends the calliope base List
    command, it gets flags for things like limit, filter, and page size. A
    list command should register a table output format to display the result.
    If resource_arg.response_id_field is specified, a --uri flag will also be
    enabled.

    Returns:
      calliope.base.Command, The command that implements the spec.
    """

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
    """Generates a Delete command.

    A delete command has a single resource argument and an API to call to
    perform the delete. If the async section is given in the spec, an --async
    flag is added and polling is automatically done on the response. For APIs
    that adhere to standards, no further configuration is necessary. If the API
    uses custom operations, you may need to provide extra configuration to
    describe how to poll the operation.

    Returns:
      calliope.base.Command, The command that implements the spec.
    """

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
        if self.spec.async:
          response = self._HandleAsync(
              args, ref, response,
              async_string='Delete request issued for: [{{{}}}]'
              .format(yaml_command_schema.NAME_FORMAT_KEY),
              sync_string='Deleting resource: [{{{}}}]'
              .format(yaml_command_schema.NAME_FORMAT_KEY),
              extract_resource_result=False)
          if args.async:
            return response

        log.DeletedResource(ref.Name(), kind=self.resource_type)
        return response

    return Command

  def _GenerateGenericCommand(self):
    """Generates a generic command.

    A generic command has a resource argument, additional fields, and calls an
    API method. It supports async if the async configuration is given. Any
    fields is message_params will be generated as arguments and inserted into
    the request message.

    Returns:
      calliope.base.Command, The command that implements the spec.
    """

    # pylint: disable=no-self-argument, The class closure throws off the linter
    # a bit. We want to use the generator class, not the class being generated.
    # pylint: disable=protected-access, The linter gets confused about 'self'
    # and thinks we are accessing something protected.
    class Command(base.Command):

      @staticmethod
      def Args(parser):
        self._CommonArgs(parser)
        if self.spec.async:
          base.ASYNC_FLAG.AddToParser(parser)

      def Run(self_, args):
        ref, response = self._CommonRun(args)
        if self.spec.async:
          response = self._HandleAsync(
              args, ref, response,
              async_string='Request issued for: [{{{}}}]'
              .format(yaml_command_schema.NAME_FORMAT_KEY),
              sync_string='Performing operation on resource: [{{{}}}]'
              .format(yaml_command_schema.NAME_FORMAT_KEY),
              extract_resource_result=True)
        return response

    return Command

  def _CommonArgs(self, parser):
    """Performs argument actions common to all commands.

    Adds all generated arguments to the parser
    Sets the command output format if specified

    Args:
      parser: The argparse parser.
    """
    args = self.arg_generator.GenerateArgs(include_global_list_flags=False)
    for arg in args.values():
      arg.AddToParser(parser)
    if self.spec.output.format:
      parser.display_info.AddFormat(self.spec.output.format)

  def _CommonRun(self, args):
    """Performs run actions common to all commands.

    Parses the resource argument into a resource reference
    Prompts the user to continue (if applicable)
    Calls the API method with the request generated from the parsed arguments

    Args:
      args: The argparse parser.

    Returns:
      (resources.Resource, response), A tuple of the parsed resource reference
      and the API response from the method call.
    """
    ref = self.arg_generator.GetRequestResourceRef(args)
    if self.spec.input.confirmation_prompt:
      console_io.PromptContinue(
          self._Format(self.spec.input.confirmation_prompt, ref),
          throw_if_unattended=True, cancel_on_no=True)

    if self.spec.request.issue_request_hook:
      # Making the request is overridden, just call into the custom code.
      return ref, self.spec.request.issue_request_hook(ref, args)

    if self.spec.request.create_request_hook:
      # We are going to make the request, but there is custom code to create it.
      request = self.spec.request.create_request_hook(ref, args)
    else:
      request = self.arg_generator.CreateRequest(args)

    response = self.method.Call(request,
                                limit=self.arg_generator.Limit(args),
                                page_size=self.arg_generator.PageSize(args))
    return ref, response

  def _HandleAsync(self, args, resource_ref, operation,
                   async_string, sync_string, extract_resource_result):
    """Handles polling for operations if the async flag is provided.

    Args:
      args: argparse.Namespace, The parsed args.
      resource_ref: resources.Resource, The resource reference for the resource
        being operated on (not the operation itself)
      operation: The operation message response.
      async_string: The format string to print when in async mode. It should
        have a single {__name__} parameter.
      sync_string: The format string to print when in sync mode. It should
        have a single {__name__} parameter.
      extract_resource_result: bool, True to return the original resource as
        the result or false to just return the operation response when it is
        done. You would set this to False for things like Delete where the
        resource no longer exists when the operation is done.

    Returns:
      The response (either the operation or the original resource).
    """
    operation_ref = resources.REGISTRY.Parse(
        getattr(operation, self.spec.async.response_name_field),
        collection=self.spec.async.collection)
    if args.async:
      log.status.Print(self._Format(async_string, resource_ref))
      log.status.Print(self._Format(
          'Check operation [{{{}}}] for status.'
          .format(yaml_command_schema.NAME_FORMAT_KEY), operation_ref))
      return operation

    poller = AsyncOperationPoller(
        self.spec, resource_ref,
        extract_resource_result=extract_resource_result)
    return waiter.WaitFor(
        poller, operation_ref, self._Format(sync_string, resource_ref))

  def _Format(self, format_string, resource_ref):
    """Formats a string with all the attributes of the given resource ref.

    Args:
      format_string: str, The format string.
      resource_ref: resources.Resource, The resource reference to extract
        attributes from.

    Returns:
      str, The formatted string.
    """
    d = resource_ref.AsDict()
    d[yaml_command_schema.NAME_FORMAT_KEY] = resource_ref.Name()
    d[yaml_command_schema.REL_NAME_FORMAT_KEY] = resource_ref.RelativeName()
    d[yaml_command_schema.RESOURCE_TYPE_FORMAT_KEY] = self.resource_type
    return format_string.format(**d)

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

  def __init__(self, spec, resource_ref, extract_resource_result=True):
    """Creates the poller.

    Args:
      spec: yaml_command_schema.CommandData, the spec for the command being
        generated.
      resource_ref: resources.Resource, The resource reference for the resource
        being operated on (not the operation itself).
      extract_resource_result: bool, True to return the original resource as
        the result or false to just return the operation response when it is
        done. You would set this to False for things like Delete where the
        resource no longer exists when the operation is done.
    """
    self.spec = spec
    self.resource_ref = resource_ref
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
