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
import os

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.kuberun import auth
from googlecloudsdk.command_lib.kuberun import flags
from googlecloudsdk.command_lib.kuberun import kuberuncli
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import transport
from googlecloudsdk.core.console import console_io


class KubeRunCommand(base.BinaryBackedCommand):
  """Base class to inherit kuberun command classes from.

    Child classes must implement the Command method and define a 'flags'
    attribute.
  """

  @classmethod
  def Args(cls, parser):
    if not hasattr(cls, 'flags'):
      raise AttributeError('type {} has not defined the flags attribute'.format(
          cls.__name__))
    flags.RegisterFlags(parser, cls.flags)

  def BuildKubeRunArgs(self, args):
    """Converts args to argument list for the given kuberun command.

    Args:
      args: the arguments passed to gcloud

    Returns:
      a list representing the arguments to be passed to the kuberun binary
    """
    command_args = []
    for f in self.flags:
      command_args.extend(f.FormatFlags(args))
    return command_args

  @abc.abstractmethod
  def Command(self):
    """Returns the supported kuberun command including all command groups."""
    pass

  @abc.abstractmethod
  def OperationResponseHandler(self, response, args):
    """Process the result of the operation."""
    pass

  @property
  def command_executor(self):
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

    project = properties.VALUES.core.project.Get()
    command = self.Command()
    command.extend(self.BuildKubeRunArgs(args))

    devkit_dir = ''  # '' to force Go binary to use the fdk-dir for gcloud_lite
    if config.Paths().sdk_root is not None:
      devkit_dir = os.path.join(config.Paths().sdk_root, 'lib', 'kuberun',
                                'kuberun_devkits')
    env_vars = {
        'CLOUDSDK_AUTH_TOKEN':
            auth.GetAuthToken(account=properties.VALUES.core.account.Get()),
        'CLOUDSDK_PROJECT':
            project,
        'CLOUDSDK_USER_AGENT':  # Cloud SDK prefix + user agent string
            '{} {}'.format(config.CLOUDSDK_USER_AGENT,
                           transport.MakeUserAgentString()),
        'KUBERUN_DEVKIT_DIRECTORY':
            devkit_dir,
    }

    region = properties.VALUES.compute.region.Get(
        required=False, validate=False)
    if region is not None:
      env_vars['CLOUDSDK_COMPUTE_REGION'] = region

    zone = properties.VALUES.compute.zone.Get(required=False, validate=False)
    if zone is not None:
      env_vars['CLOUDSDK_COMPUTE_ZONE'] = zone

    response = self.command_executor(
        command=command,
        env=kuberuncli.GetEnvArgsForCommand(extra_vars=env_vars),
        show_exec_error=args.show_exec_error)
    log.debug('Response: %s' % response.stdout)
    log.debug('ErrResponse: %s' % response.stderr)
    return self.OperationResponseHandler(response, args)


class KubeRunStreamingCommand(KubeRunCommand):
  """Base class for kuberun command with streaming binary executor.

    Child classes must implement BuildArgs and Command methods.
  """

  @property
  def command_executor(self):
    return kuberuncli.KubeRunStreamingCli()

  def OperationResponseHandler(self, response, args):
    if response.failed:
      raise exceptions.Error('Command execution failed')


class KubeRunCommandWithOutput(KubeRunCommand):
  """Base class for commands that return a result (on their stdout)."""

  def OperationResponseHandler(self, response, args):
    if response.stderr:
      log.status.Print(response.stderr)

    if response.failed:
      err_msg = 'Command execution failed'
      if response.stderr:
        err_msg += ': ' + response.stderr
      raise exceptions.Error(err_msg)

    return self.FormatOutput(response.stdout, args)

  @abc.abstractmethod
  def FormatOutput(self, out, args):
    """Formats the output of the kuberun command execution, typically convert to json."""
    pass


class KubeRunStreamingCommandWithResult(KubeRunCommandWithOutput):
  """Base class for streaming commands that return a result on their stdout."""

  @property
  def command_executor(self):
    return kuberuncli.KubeRunStreamingCli(std_out_func=_CaptureStreamOutHandler)


def _CaptureStreamOutHandler(result_holder, **kwargs):
  """Captures streaming stdout from subprocess for processing in OperationResponseHandler."""
  del kwargs  # we want to capture stdout regardless of other options

  def HandleStdOut(line):
    if line:
      line.rstrip()
      if not result_holder.stdout:
        result_holder.stdout = line
      else:
        result_holder.stdout += '\n' + line

  return HandleStdOut
