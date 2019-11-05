# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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

"""Library for defining Binary backed operations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import collections
import os


from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import execution_utils as exec_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import yaml
from googlecloudsdk.core.updater import update_manager
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms

import six


_DEFAULT_FAILURE_ERROR_MESSAGE = (
    'Error executing command [{}]. Process exited with code {}')


class BinaryOperationError(core_exceptions.Error):
  """Base class for binary operation errors."""


class MissingExecutableException(BinaryOperationError):
  """Raised if an executable can not be found on the path."""

  def __init__(self, exec_name):
    super(MissingExecutableException, self).__init__(
        'Executable [{}] not found.'.format(exec_name))


class ExecutionError(BinaryOperationError):
  """Raised if there is an error executing the executable."""

  def __init__(self, command, error):
    super(ExecutionError, self).__init__(
        'Error executing command [{}]: [{}]'.format(command, error))


class ArgumentError(BinaryOperationError):
  """Raised if there is an error parsing argument to a command."""


def DefaultStdOutHandler(result_holder):
  """Default processing for stdout from subprocess."""
  def HandleStdOut(stdout):
    if stdout:
      stdout.rstrip()
    result_holder.stdout = stdout
  return HandleStdOut


def DefaultStdErrHandler(result_holder):
  """Default processing for stderr from subprocess."""
  def HandleStdErr(stderr):
    if stderr:
      stderr.rstrip()
    result_holder.stderr = stderr
  return HandleStdErr


def DefaultFailureHandler(result_holder):
  """Default processing for subprocess failure status."""
  if result_holder.exit_code != 0:
    result_holder.failed = True
    log.error(_DEFAULT_FAILURE_ERROR_MESSAGE.format(
        result_holder.executed_command, result_holder.exit_code))


# Some common golang binary commands (e.g. kubectl diff) behave this way
# so this is for those known exceptional cases.
def NonZeroSuccessFailureHandler(result_holder):
  """Processing for subprocess where non-zero exit status is not always failure.

  Uses rule of thumb that defines success as:
  - a process with zero exit status OR
  - a process with non-zero exit status AND some stdout output.

  All others are considered failed.

  Args:
    result_holder: OperationResult, result of command execution

  Returns:
    None. Sets the failed attribute of the result_holder.
  """
  if result_holder.exit_code != 0 and not result_holder.stdout:
    result_holder.failed = True
    log.error(_DEFAULT_FAILURE_ERROR_MESSAGE.format(
        result_holder.executed_command, result_holder.exit_code))


def CheckBinaryComponentInstalled(component_name):
  platform = platforms.Platform.Current() if config.Paths().sdk_root else None
  manager = update_manager.UpdateManager(platform_filter=platform, warn=False)
  return component_name in manager.GetCurrentVersionsInformation()


def CheckForInstalledBinary(binary_name):
  """Check if binary is installed and return path or raise error.

  Prefer the installed component over any version found on path.

  Args:
    binary_name: str, name of binary to search for.

  Returns:
    Path to executable if found on path or installed component.

  Raises:
    MissingExecutableException: if executable can not be found and is not
     installed as a component.
  """
  is_component = CheckBinaryComponentInstalled(binary_name)

  if is_component:
    return os.path.join(config.Paths().sdk_bin_path, binary_name)

  path_executable = files.FindExecutableOnPath(binary_name)
  if path_executable:
    return path_executable

  raise MissingExecutableException(binary_name)


class BinaryBackedOperation(six.with_metaclass(abc.ABCMeta, object)):
  """Class for declarative operations implemented as external binaries."""

  class OperationResult(object):
    """Generic Holder for Operation return values and errors."""

    def __init__(self,
                 command_str,
                 output=None,
                 errors=None,
                 status=0,
                 failed=False):
      self.executed_command = command_str
      self.stdout = output
      self.stderr = errors
      self.exit_code = status
      self.failed = failed

    def __str__(self):
      output = collections.OrderedDict()
      output['executed_command'] = self.executed_command
      output['stdout'] = self.stdout
      output['stderr'] = self.stderr
      output['exit_code'] = self.exit_code
      output['failed'] = self.failed
      return yaml.dump(output)

    def __eq__(self, other):
      if isinstance(other, BinaryBackedOperation.OperationResult):
        return (self.executed_command == other.executed_command and
                self.stdout == other.stdout and
                self.stderr == other.stderr and
                self.exit_code == other.exit_code and
                self.failed == other.failed)
      return False

  def __init__(self, binary, std_out_func=None,
               std_err_func=None, failure_func=None, default_args=None):
    """Creates the Binary Operation.

    Args:
      binary: executable, the name of binary containing the underlying
        operations that this class will invoke.
      std_out_func: callable(str), function to call to process stdout from
        executable
      std_err_func: callable(str), function to call to process stderr from
        executable
      failure_func: callable(OperationResult), function to call to determine if
        the operation result is a failure. Useful for cases where underlying
        binary can exit with non-zero error code yet still succeed.
      default_args: dict{str:str}, mapping of parameter names to values
        containing default/static values that should always be passed to the
        command.
    """
    self._executable = CheckForInstalledBinary(binary)
    self._binary = binary
    self._default_args = default_args
    self.std_out_handler = std_out_func
    self.std_err_handler = std_err_func
    self.set_failure_status = failure_func

  @property
  def binary_name(self):
    return self._binary

  @property
  def executable(self):
    return self._executable

  @property
  def defaults(self):
    return self._default_args

  def _Execute(self, **kwargs):
    """Execute binary and return operation result.

     Will parse args from kwargs into a list of args to pass to underlying
     binary and then attempt to execute it. Will use configured stdout, stderr
     and failure handlers for this operation if configured or module defaults.

    Args:
      **kwargs: mapping of arguments to pass to the underlying binary

    Returns:
      OperationResult: execution result for this invocation of the binary.

    Raises:
      ArgumentError, if there is an error parsing the supplied arguments.
      BinaryOperationError, if there is an error executing the binary.
    """
    cmd = [self.executable]
    cmd.extend(self._ParseArgsForCommand(**kwargs))

    result_holder = self.OperationResult(cmd)
    std_out_handler = (self.std_out_handler or
                       DefaultStdOutHandler(result_holder))
    std_err_handler = (self.std_out_handler or
                       DefaultStdErrHandler(result_holder))
    failure_handler = (self.set_failure_status or DefaultFailureHandler)

    try:
      exit_code = exec_utils.Exec(args=cmd,
                                  no_exit=True,
                                  out_func=std_out_handler,
                                  err_func=std_err_handler,
                                  in_str=kwargs.get('stdin'))
    except (exec_utils.PermissionError, exec_utils.InvalidCommandError) as e:
      raise ExecutionError(cmd, e)
    result_holder.exit_code = exit_code
    failure_handler(result_holder)
    return result_holder

  @abc.abstractmethod
  def _ParseArgsForCommand(self, **kwargs):
    """Parse and validate kwargs into command argument list.

    Will process any default_args first before processing kwargs, overriding as
    needed. Will also perform any validation on passed arguments.

    Args:
      **kwargs: keyword arguments for the underlying command.

    Returns:
     list of arguments to pass to execution of underlying command.

    Raises:
      ArgumentError: if there is an error parsing or validating arguments.
    """
    pass

  def __call__(self, **kwargs):
    return self._Execute(**kwargs)
