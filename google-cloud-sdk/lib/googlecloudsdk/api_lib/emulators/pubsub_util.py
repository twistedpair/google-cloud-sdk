# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Utility functions for gcloud pubsub emulator."""

import os
from googlecloudsdk.api_lib.emulators import util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.util import platforms

PUBSUB = 'pubsub'
PUBSUB_TITLE = 'Google Cloud Pub/Sub emulator'


class NoPubSubError(exceptions.Error):
  pass


class InvalidArgumentError(exceptions.Error):

  def __init__(self, msg):
    super(InvalidArgumentError, self).__init__(msg)


def ToArgsList(args):
  """Converts an argparse.Namespace to a list of arg strings."""
  args_list = []
  if args.host_port:
    if args.host_port.host is not None:
      args_list.append('--host=%s' % args.host_port.host)
    if args.host_port.port is not None:
      args_list.append('--port=%s' % args.host_port.port)
  return args_list


def GetPubSubRoot():
  pubsub_dir = os.path.join(util.GetCloudSDKRoot(), 'platform',
                            'pubsub-emulator')
  if not os.path.isdir(pubsub_dir):
    raise NoPubSubError('No pubsub directory found.')
  return pubsub_dir


def GetDataDir():
  return util.GetDataDir(PUBSUB)


def BuildStartArgs(args, current_os):
  """Builds the command for starting the pubsub emulator.

  Args:
    args: (list of str) The arguments for the pubsub emulator, excluding the
      program binary.
    current_os: (platforms.OperatingSystem)

  Returns:
    A list of command arguments.
  """
  pubsub_dir = GetPubSubRoot()
  if current_os is platforms.OperatingSystem.WINDOWS:
    pubsub_executable = os.path.join(
        pubsub_dir, r'bin\cloud-pubsub-emulator.bat')
    return execution_utils.ArgsForCMDTool(pubsub_executable, *args)

  pubsub_executable = os.path.join(pubsub_dir, 'bin/cloud-pubsub-emulator')
  return execution_utils.ArgsForExecutableTool(pubsub_executable, *args)


def GetEnv(args):
  """Returns an environment variable mapping from an argparse.Namespace."""
  return {'PUBSUB_EMULATOR_HOST': '%s:%s' %
                                  (args.host_port.host, args.host_port.port)}


def Start(args):
  pubsub_args = BuildStartArgs(
      ToArgsList(args), platforms.OperatingSystem.Current())
  log.status.Print('Executing: {0}'.format(' '.join(pubsub_args)))
  pubsub_process = util.Exec(pubsub_args)
  util.WriteEnvYaml(GetEnv(args), args.data_dir)
  util.PrefixOutput(pubsub_process, PUBSUB)
