# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Base class to inherit kuberun command classes from."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import abc

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import parser_errors
from googlecloudsdk.command_lib.kuberun import auth
from googlecloudsdk.command_lib.kuberun import flags
from googlecloudsdk.command_lib.kuberun import kuberuncli
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io


class KubeRunCommand(base.BinaryBackedCommand):
  """Base class to inherit kuberun command classes from.

    Child classes must implement BuildArgs and Command methods.
  """

  @staticmethod
  def _Flags(parser):
    base.BinaryBackedCommand._Flags(parser)
    flags.AddClusterConnectionFlags(parser)

  def _AddCommonFlags(self, command, args):
    exec_args = []
    try:
      if args.IsSpecified('all_namespaces'):
        exec_args.extend(['--all-namespaces'])
    except parser_errors.UnknownDestinationException:
      # all_namespaces is not a valid flag for this command
      pass
    if args.IsSpecified('namespace'):
      exec_args.extend(['--namespace', args.namespace])

    exec_args.extend(flags.TranslateClusterConnectionFlags(args))
    command.extend(exec_args)

  @abc.abstractmethod
  def BuildKubeRunArgs(self, args):
    """Converts args to argument list for the given kuberun command.

    Args:
      args: the arguments passed to gcloud
    """
    pass

  @abc.abstractmethod
  def Command(self):
    """Returns the supported kuberun command including all command groups."""
    pass

  def OperationResponseHandler(self, response, args):
    return self._DefaultOperationResponseHandler(response)

  def CommandExecutor(self):
    return kuberuncli.KubeRunCli()

  def Run(self, args):
    enable_experimental = (
        properties.VALUES.kuberun.enable_experimental_commands.GetBool())
    if not enable_experimental:
      # This prompt is here because our commands are not yet public and marking
      # them as hidden doesn't proclude a customer from using the command if
      # they know about it.
      console_io.PromptContinue(
          message='This command is currently under construction and not supported.',
          throw_if_unattended=True,
          cancel_on_no=True,
          default=False)

    command_executor = self.CommandExecutor()
    project = properties.VALUES.core.project.Get()
    command = self.Command()
    # TODO(b/168745545) adding commands and args to 'command' defeats the
    # purpose of BinaryBackedOperation._ParseArgsForCommand
    self._AddCommonFlags(command, args)
    command.extend(self.BuildKubeRunArgs(args))
    response = command_executor(
        command=command,
        env=kuberuncli.GetEnvArgsForCommand(
            extra_vars={
                'CLOUDSDK_AUTH_TOKEN':
                    auth.GetAuthToken(
                        account=properties.VALUES.core.account.Get()),
                'CLOUDSDK_PROJECT':
                    project
            }),
        show_exec_error=args.show_exec_error)
    log.debug('Response: %s' % response.stdout)
    log.debug('ErrResponse: %s' % response.stderr)
    return self.OperationResponseHandler(response, args)


class KubeRunStreamingCommand(KubeRunCommand):
  """Base class for kuberun command with streaming binary executor.

    Child classes must implement BuildArgs and Command methods.
  """

  def CommandExecutor(self):
    return kuberuncli.KubeRunStreamingCli()


class KubeRunCommandWithOutput(KubeRunCommand):
  """Base class for commands that return a result (on their stdout)."""

  def OperationResponseHandler(self, response, args):
    if response.stderr:
      log.status.Print(response.stderr)

    if response.failed:
      raise exceptions.Error('Command execution failed')

    return self.FormatOutput(response.stdout, args)

  @abc.abstractmethod
  def FormatOutput(self, out, args):
    """Formats the output of the kuberun command execution, typically convert to json."""
    pass
