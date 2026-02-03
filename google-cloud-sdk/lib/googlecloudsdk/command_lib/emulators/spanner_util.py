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
"""Utility functions for gcloud spanner emulator."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import ipaddress
import os

from googlecloudsdk.command_lib.emulators import util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.util import platforms
import six

SPANNER_EMULATOR_PROPERTY_PREFIX = 'spanner'
SPANNER_EMULATOR_COMPONENT_ID = 'cloud-spanner-emulator'
SPANNER_EMULATOR_TITLE = 'Google Cloud Spanner Emulator'
SPANNER_EMULATOR_EXECUTABLE_DIR = 'cloud_spanner_emulator'
SPANNER_EMULATOR_EXECUTABLE_FILE = 'gateway_main'
SPANNER_EMULATOR_DOCKER_IMAGE = 'gcr.io/cloud-spanner-emulator/emulator:1.5.28'
SPANNER_EMULATOR_DEFAULT_GRPC_PORT = 9010
SPANNER_EMULATOR_DEFAULT_REST_PORT = 9020


class InvalidHostPortFormat(exceptions.Error):
  pass


def GetDataDir():
  return util.GetDataDir(SPANNER_EMULATOR_PROPERTY_PREFIX)


def _BuildStartArgsForDocker(args):
  """Builds arguments for starting the spanner emulator under docker."""

  # We use -p on Docker to enforce the specified hostname, but -p requires
  # ip addresses. We handle the localhost case specifically as it is the
  # common case.
  host_ip = args.host_port.host
  if host_ip == 'localhost':
    host_ip = '127.0.0.1'
  try:
    ipaddress.ip_address(host_ip)
  except ValueError:
    raise InvalidHostPortFormat(
        'When using docker, hostname specified via --host-port '
        'must be an IPV4 or IPV6 address, found ' + host_ip)

  docker_args = [
      'docker', 'run', '-p',
      '{}:{}:{}'.format(host_ip, args.host_port.port,
                        SPANNER_EMULATOR_DEFAULT_GRPC_PORT), '-p',
      '{}:{}:{}'.format(host_ip, args.rest_port,
                        SPANNER_EMULATOR_DEFAULT_REST_PORT),
      SPANNER_EMULATOR_DOCKER_IMAGE
  ]

  gateway_args = []
  # Some arguments must be specified after the image name.
  # If any are specified, we must specify the executable.
  enable_fault_injection = getattr(args, 'enable_fault_injection', False)
  print_notices = getattr(args, 'print_notices', False)
  if enable_fault_injection or print_notices:
    gateway_args.extend(['./gateway_main', '--hostname', '0.0.0.0'])
    if enable_fault_injection:
      gateway_args.append('--enable_fault_injection')
    if print_notices:
      gateway_args.append('--notices')

  return execution_utils.ArgsForExecutableTool(*(docker_args + gateway_args))


def _BuildStartArgsForNativeExecutable(args):
  """Builds arguments for starting the spanner emulator as a native executable.

  Args:
    args: An argparse.Namespace object containing the command line arguments.

  Returns:
    A list of strings representing the command and its arguments.

  Raises:
    InvalidHostPortFormat: If the host_port is missing the port.
  """
  spanner_executable = os.path.join(util.GetCloudSDKRoot(), 'bin',
                                    SPANNER_EMULATOR_EXECUTABLE_DIR,
                                    SPANNER_EMULATOR_EXECUTABLE_FILE)
  if args.host_port.port is None:
    raise InvalidHostPortFormat(
        'Invalid value for --host-port. Must be in the format host:port')
  native_args = [
      spanner_executable, '--hostname', args.host_port.host, '--grpc_port',
      args.host_port.port, '--http_port',
      six.text_type(args.rest_port)
  ]
  if getattr(args, 'enable_fault_injection', False):
    native_args.append('--enable_fault_injection')
  if getattr(args, 'print_notices', False):
    native_args.append('--notices')
  return execution_utils.ArgsForExecutableTool(*native_args)


def _BuildStartArgs(args):
  current_os = platforms.OperatingSystem.Current()
  if (
      current_os is platforms.OperatingSystem.LINUX
      or current_os is platforms.OperatingSystem.MACOSX
  ) and not args.use_docker:
    return _BuildStartArgsForNativeExecutable(args)
  else:
    return _BuildStartArgsForDocker(args)


def GetEnv(args):
  """Returns an environment variable mapping from an argparse.Namespace."""
  return {
      'SPANNER_EMULATOR_HOST':
          '{}:{}'.format(args.host_port.host, args.host_port.port)
  }


def Start(args):
  spanner_args = _BuildStartArgs(args)
  log.status.Print('Executing: {0}'.format(' '.join(spanner_args)))
  with util.Exec(spanner_args) as spanner_process:
    util.WriteEnvYaml(GetEnv(args), GetDataDir())
    util.PrefixOutput(spanner_process, SPANNER_EMULATOR_COMPONENT_ID)
