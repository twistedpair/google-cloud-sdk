# Copyright 2015 Google Inc. All Rights Reserved.
"""Utility functions for gcloud emulators datastore group."""

import atexit
import errno
import os
import random
import subprocess

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resource_printer
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


def WriteEnvYaml(env, output_dir):
  """Writes the given environment values into the output_dir/env.yaml file.

  Args:
    env: {str: str}, Dictonary of environment values.
    output_dir: str, Path of directory to which env.yaml file should be written.
  """
  env_file_path = os.path.join(output_dir, 'env.yaml')
  with files.Context(open(env_file_path, 'w')) as env_file:
    resource_printer.YamlPrinter(env_file).AddRecord(env)


def ReadEnvYaml(output_dir):
  """Reads and returns the environment values in output_dir/env.yaml file.

  Args:
    output_dir: str, Path of directory containing the env.yaml to be read.

  Returns:
    env: {str: str}
  """
  env_file_path = os.path.join(output_dir, 'env.yaml')
  try:
    with files.Context(open(env_file_path, 'r')) as env_file:
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
