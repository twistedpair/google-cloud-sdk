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
"""Utility functions for gcloud emulators datastore group."""

import atexit
import errno
import os
import random
import re
import subprocess

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.resource import resource_printer
from googlecloudsdk.core.updater import local_state
from googlecloudsdk.core.updater import update_manager
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms
import yaml


class NoCloudSDKError(exceptions.Error):
  """The module was unable to find Cloud SDK."""

  def __init__(self):
    super(NoCloudSDKError, self).__init__(
        'Unable to find a Cloud SDK installation.')


class NoEnvYamlError(exceptions.Error):
  """Unable to find a env.yaml file."""

  def __init__(self, data_dir):
    super(NoEnvYamlError, self).__init__(
        'Unable to find env.yaml in the data_dir [{0}]. Please ensure you have'
        ' started the appropriate emulator.'.format(data_dir))


class Java7Error(exceptions.Error):

  def __init__(self, msg):
    super(Java7Error, self).__init__(msg)


class NoEmulatorError(exceptions.Error):
  pass


def EnsureComponentIsInstalled(component_id, for_text):
  """Ensures that the specified component is installed.

  Args:
    component_id: str, the name of the component
    for_text: str, the text explaining what the component is necessary for

  Raises:
    NoCloudSDKError: If a Cloud SDK installation is not found.
  """
  msg = ('You need the [{0}] component to use the {1}.'
         .format(component_id, for_text))
  try:
    update_manager.UpdateManager.EnsureInstalledAndRestart([component_id],
                                                           msg=msg)
  except local_state.InvalidSDKRootError:
    raise NoCloudSDKError()


def GetCloudSDKRoot():
  """Gets the directory of the root of the Cloud SDK, error if it doesn't exist.

  Raises:
    NoCloudSDKError: If there is no SDK root.

  Returns:
    str, The path to the root of the Cloud SDK.
  """
  sdk_root = config.Paths().sdk_root
  if not sdk_root:
    raise NoCloudSDKError()
  log.debug('Found Cloud SDK root: %s', sdk_root)
  return sdk_root


def CheckIfJava7IsInstalled(for_text):
  """Checks if Java 7+ is installed.

  Args:
    for_text: str, the text explaining what Java 7 is necessary for

  Raises:
    Java7Error: if Java 7+ is not found on the path or is not executable.
  """
  java_path = files.FindExecutableOnPath('java')
  if not java_path:
    raise Java7Error('To use the {for_text}, a Java 7+ JRE must be installed '
                     'and on your system PATH'.format(for_text=for_text))
  try:
    output = subprocess.check_output([java_path, '-version'],
                                     stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError:
    raise Java7Error('Unable to execute the java that was found on your PATH.'
                     ' The {for_text} requires a Java 7+ JRE installed and on '
                     'your system PATH'.format(for_text=for_text))

  match = re.search('version "1.([0-9]).', output)
  if not match or int(match.group(1)) < 7:
    raise Java7Error('The java executable on your PATH is not a Java 7+ JRE.'
                     ' The {for_text} requires a Java 7+ JRE installed and on '
                     'your system PATH'.format(for_text=for_text))


def IsJavaInstalledForTest():
  """Use this to use Java 7+ as a boolean precondition."""
  try:
    CheckIfJava7IsInstalled('test')
    return True
  except Java7Error:
    return False


def WriteEnvYaml(env, output_dir):
  """Writes the given environment values into the output_dir/env.yaml file.

  Args:
    env: {str: str}, Dictonary of environment values.
    output_dir: str, Path of directory to which env.yaml file should be written.
  """
  env_file_path = os.path.join(output_dir, 'env.yaml')
  with open(env_file_path, 'w') as env_file:
    resource_printer.Print([env], print_format='yaml', out=env_file)


def ReadEnvYaml(output_dir):
  """Reads and returns the environment values in output_dir/env.yaml file.

  Args:
    output_dir: str, Path of directory containing the env.yaml to be read.

  Returns:
    env: {str: str}
  """
  env_file_path = os.path.join(output_dir, 'env.yaml')
  try:
    with open(env_file_path, 'r') as env_file:
      return yaml.safe_load(env_file)
  except IOError as err:
    if err.errno == errno.ENOENT:
      raise NoEnvYamlError(output_dir)
    else:
      raise err


def PrintEnvExport(env):
  """Print OS specific export commands for the given environment values.

  Args:
    env: {str: str}, Dictonary of environment values.
  """
  current_os = platforms.OperatingSystem.Current()
  export_command = 'export'
  if current_os is platforms.OperatingSystem.WINDOWS:
    export_command = 'set'
  for var, value in env.iteritems():
    if ' ' in value:
      value = '"{value}"'.format(value=value)
    log.Print('{export_command} {var}={value}'.format(
        export_command=export_command,
        var=var,
        value=value))


def PrintEnvUnset(env):
  """Print OS specific unset commands for the given environment variables.

  Args:
    env: {str: str}, Dictionary of environment values, the value is ignored.
  """
  current_os = platforms.OperatingSystem.Current()
  export_command = 'unset {var}'
  if current_os is platforms.OperatingSystem.WINDOWS:
    export_command = 'set {var}='
  for var in env.iterkeys():
    log.Print(export_command.format(var=var))


def GetDataDir(prefix):
  """If present, returns the configured data dir, else returns the default.

  Args:
    prefix: str, The prefix for the *-emulator property group to look up.

  Returns:
    str, The configured or default data_dir path.
  """
  configured = _GetEmulatorProperty(prefix, 'data_dir')
  if configured: return configured

  config_root = config.Paths().global_config_dir
  default_data_dir = os.path.join(config_root, 'emulators', prefix)
  files.MakeDir(default_data_dir)
  return default_data_dir


def GetHostPort(prefix):
  """If present, returns the configured host port, else returns the default.

  Args:
    prefix: str, The prefix for the *-emulator property group to look up.

  Returns:
    str, The configured or default host_port
  """
  configured = _GetEmulatorProperty(prefix, 'host_port')
  if configured: return configured

  return 'localhost:8{rand:03d}'.format(rand=random.randint(0, 999))


def _GetEmulatorProperty(prefix, prop_name):
  """Returns the value of the given property in the given emulator group.

  Args:
    prefix: str, The prefix for the *_emulator property group to look up.
    prop_name: str, The name of the property to look up.

  Returns:
    str, The the value of the given property in the specified emulator group.
  """
  property_group = '{prefix}_emulator'.format(prefix=prefix)
  for section in properties.VALUES:
    if section.name == property_group:
      return section.Property(prop_name).Get()
  return None


def Exec(args):
  """Starts subprocess with given args and ensures its termination upon exit.

  This starts a subprocess with the given args. The stdout and stderr of the
  subprocess are piped. The subprocess is terminated upon exit.

  Args:
    args: [str], The arguments to execute.  The first argument is the command.

  Returns:
    process, The process handle of the subprocess that has been started.
  """
  process = subprocess.Popen(args,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)

  def Terminate():
    if process.poll() is None:
      process.terminate()
      process.wait()
  atexit.register(Terminate)

  return process


def PrefixOutput(process, prefix):
  """Prepends the given prefix to each line of the given process's output.

  Args:
    process: process, The handle to the process whose output should be prefixed
    prefix: str, The prefix to be prepended to the process's output.
  """
  output_line = process.stdout.readline()
  while output_line:
    log.status.Print('[{0}] {1}'.format(prefix, output_line.rstrip()))
    log.status.flush()
    output_line = process.stdout.readline()


def BuildArgsList(args):
  """Converts an argparse.Namespace to a list of arg strings."""
  args_list = []
  if args.host_port:
    if args.host_port.host is not None:
      args_list.append('--host={0}'.format(args.host_port.host))
    if args.host_port.port is not None:
      args_list.append('--port={0}'.format(args.host_port.port))
  return args_list


def GetEmulatorRoot(emulator):
  emulator_dir = os.path.join(GetCloudSDKRoot(),
                              'platform', '{0}-emulator'.format(emulator))
  if not os.path.isdir(emulator_dir):
    raise NoEmulatorError('No {0} directory found.'.format(emulator))
  return emulator_dir
