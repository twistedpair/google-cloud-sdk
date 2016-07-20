# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Functions to help with shelling out to other commands."""

import cStringIO
import errno
import os
import re
import signal
import sys
import time

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.configurations import named_configs
from googlecloudsdk.core.util import platforms
from googlecloudsdk.third_party.py27 import py27_subprocess as subprocess


class PermissionError(exceptions.Error):
  """User does not have execute permissions."""

  def __init__(self, error):
    super(PermissionError, self).__init__(
        '{err}\nPlease verify that you have execute permission for all'
        'files in your CLOUD SDK bin folder'.format(err=error))


def GetPythonExecutable():
  """Gets the path to the Python interpreter that should be used."""
  cloudsdk_python = os.environ.get('CLOUDSDK_PYTHON')
  if cloudsdk_python:
    return cloudsdk_python
  python_bin = sys.executable
  if not python_bin:
    raise ValueError('Could not find Python executable.')
  return python_bin


# From https://en.wikipedia.org/wiki/Unix_shell#Bourne_shell_compatible
# Many scripts that we execute via execution_utils are bash scripts, and we need
# a compatible shell to run them.
# zsh, was initially on this list, but it doesn't work 100% without running it
# in `emulate sh` mode.
_BORNE_COMPATIBLE_SHELLS = [
    'ash',
    'bash',
    'busybox'
    'dash',
    'ksh',
    'mksh',
    'pdksh',
    'sh',
]


def _GetShellExecutable():
  """Gets the path to the Shell that should be used.

  First tries the current environment $SHELL, if set, then `bash` and `sh`. The
  first of these that is found is used.

  The shell must be Borne-compatible, as the commands that we execute with it
  are often bash/sh scripts.

  Returns:
    str, the path to the shell

  Raises:
    ValueError: if no Borne compatible shell is found
  """
  shells = ['/bin/bash', '/bin/sh']

  user_shell = os.getenv('SHELL')
  if user_shell and os.path.basename(user_shell) in _BORNE_COMPATIBLE_SHELLS:
    shells.insert(0, user_shell)

  for shell in shells:
    if os.path.isfile(shell):
      return shell

  raise ValueError("You must set your 'SHELL' environment variable to a "
                   "valid Borne-compatible shell executable to use this tool.")


def _GetToolArgs(interpreter, interpreter_args, executable_path, *args):
  tool_args = []
  if interpreter:
    tool_args.append(interpreter)
  if interpreter_args:
    tool_args.extend(interpreter_args)
  tool_args.append(executable_path)
  tool_args.extend(list(args))
  return tool_args


def _GetToolEnv(env=None):
  """Generate the environment that should be used for the subprocess.

  Args:
    env: {str, str}, An existing environment to augment.  If None, the current
      environment will be cloned and used as the base for the subprocess.

  Returns:
    The modified env.
  """
  if env is None:
    env = dict(os.environ)
  env['CLOUDSDK_WRAPPER'] = '1'

  # Flags can set properties which override the properties file and the existing
  # env vars.  We need to propagate them to children processes through the
  # environment so that those commands will use the same settings.
  for s in properties.VALUES:
    for p in s:
      _AddOrRemoveVar(
          env, p.EnvironmentName(), p.Get(required=False, validate=False))

  # Configuration needs to be handled separately because it's not a real
  # property (although it behaves like one).
  _AddOrRemoveVar(env,
                  config.CLOUDSDK_ACTIVE_CONFIG_NAME,
                  named_configs.ConfigurationStore.ActiveConfig().name)

  return env


def _AddOrRemoveVar(d, name, value):
  if value is None:
    d.pop(name, None)
  else:
    d[name] = value


def ArgsForPythonTool(executable_path, *args, **kwargs):
  """Constructs an argument list for calling the Python interpreter.

  Args:
    executable_path: str, The full path to the Python main file.
    *args: args for the command
    **kwargs: python: str, path to Python executable to use (defaults to
      automatically detected)

  Returns:
    An argument list to execute the Python interpreter

  Raises:
    TypeError: if an unexpected keyword argument is passed
  """
  unexpected_arguments = set(kwargs) - set(['python'])
  if unexpected_arguments:
    raise TypeError(("ArgsForPythonTool() got unexpected keyword arguments "
                     "'[{0}]'").format(', '.join(unexpected_arguments)))
  python_executable = kwargs.get('python') or GetPythonExecutable()
  python_args_str = os.environ.get('CLOUDSDK_PYTHON_ARGS', '')
  python_args = python_args_str.split()
  return _GetToolArgs(
      python_executable, python_args, executable_path, *args)


def ArgsForCMDTool(executable_path, *args):
  """Constructs an argument list for calling the cmd interpreter.

  Args:
    executable_path: str, The full path to the cmd script.
    *args: args for the command

  Returns:
    An argument list to execute the cmd interpreter
  """
  return _GetToolArgs('cmd', ['/c'], executable_path, *args)


def ArgsForExecutableTool(executable_path, *args):
  """Constructs an argument list for an executable.

   Can be used for calling a native binary or shell executable.

  Args:
    executable_path: str, The full path to the binary.
    *args: args for the command

  Returns:
    An argument list to execute the native binary
  """
  return _GetToolArgs(None, None, executable_path, *args)


class _ProcessHolder(object):

  def __init__(self):
    self.process = None

  # pylint: disable=unused-argument
  def Handler(self, signum, frame):
    if self.process:
      self.process.terminate()
      ret_val = self.process.wait()
      sys.exit(ret_val)


def Exec(args, env=None, no_exit=False, pipe_output_through_logger=False,
         file_only_logger=False):
  """Emulates the os.exec* set of commands, but uses subprocess.

  This executes the given command, waits for it to finish, and then exits this
  process with the exit code of the child process.

  Args:
    args: [str], The arguments to execute.  The first argument is the command.
    env: {str: str}, An optional environment for the child process.
    no_exit: bool, True to just return the exit code of the child instead of
      exiting.
    pipe_output_through_logger: bool, True to feed output from the called
      command through the standard logger instead of raw stdout/stderr.
    file_only_logger: bool, If piping through the logger, log to the file only
      instead of log.out and log.err.

  Returns:
    int, The exit code of the child if no_exit is True, else this method does
    not return.

  Raises:
    PermissionError: if user that not have execute permission for cloud sdk bin
    files.
  """
  log.debug('Executing command: %s', args)
  # We use subprocess instead of execv because windows does not support process
  # replacement.  The result of execv on windows is that a new processes is
  # started and the original is killed.  When running in a shell, the prompt
  # returns as soon as the parent is killed even though the child is still
  # running.  subprocess waits for the new process to finish before returning.
  env = _GetToolEnv(env=env)
  process_holder = _ProcessHolder()

  old_handler = signal.signal(signal.SIGTERM, process_holder.Handler)

  try:
    extra_popen_kwargs = {}
    if pipe_output_through_logger:
      extra_popen_kwargs['stderr'] = subprocess.PIPE
      extra_popen_kwargs['stdout'] = subprocess.PIPE
    try:
      p = subprocess.Popen(args, env=env, **extra_popen_kwargs)
      process_holder.process = p
    except OSError as err:
      if err.errno == errno.EACCES:
        raise PermissionError(err.strerror)
      else:
        # Raise stack trace.
        raise
    if pipe_output_through_logger:
      if file_only_logger:
        out = cStringIO.StringIO()
        err = cStringIO.StringIO()
      else:
        out = log.out
        err = log.err

      ret_val = None
      while ret_val is None:
        stdout, stderr = p.communicate()
        out.write(stdout)
        err.write(stderr)
        ret_val = p.returncode

      if file_only_logger:
        log.file_only_logger.debug(out.getvalue())
        log.file_only_logger.debug(err.getvalue())

    else:
      ret_val = p.wait()

  finally:
    # Restore the original signal handler.
    signal.signal(signal.SIGTERM, old_handler)

  if no_exit:
    return ret_val
  sys.exit(ret_val)


class UninterruptibleSection(object):
  """Run a section of code with CTRL-C disabled.

  When in this context manager, the ctrl-c signal is caught and a message is
  printed saying that the action cannot be cancelled.
  """

  def __init__(self, stream, message=None):
    self.__old_handler = None
    self.__message = '\n\n{message}\n\n'.format(
        message=(message or 'This operation cannot be cancelled.'))
    self.__stream = stream

  def __enter__(self):
    self.__old_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, self._Handler)
    return self

  def __exit__(self, typ, value, traceback):
    signal.signal(signal.SIGINT, self.__old_handler)

  def _Handler(self, unused_signal, unused_frame):
    self.__stream.write(self.__message)


def KillSubprocess(p):
  """Kills a subprocess using an OS specific method when python can't do it.

  This also kills all processes rooted in this process.

  Args:
    p: the Popen or multiprocessing.Process object to kill

  Raises:
    RuntimeError: if it fails to kill the process
  """

  # This allows us to kill a Popen object or a multiprocessing.Process object
  code = None
  if hasattr(p, 'returncode'):
    code = p.returncode
  elif hasattr(p, 'exitcode'):
    code = p.exitcode

  if code is not None:
    # already dead
    return

  if platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS:
    # Consume stdout so it doesn't show in the shell
    taskkill_process = subprocess.Popen(
        ['taskkill', '/F', '/T', '/PID', str(p.pid)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    (stdout, stderr) = taskkill_process.communicate()
    if taskkill_process.returncode != 0 and _IsTaskKillError(stderr):
      # Sometimes taskkill does things in the wrong order and the processes
      # disappear before it gets a chance to kill it.  This is exposed as an
      # error even though it's the outcome we want.
      raise RuntimeError(
          'Failed to call taskkill on pid {0}\nstdout: {1}\nstderr: {2}'
          .format(p.pid, stdout, stderr))

  else:
    # Create a mapping of ppid to pid for all processes, then kill all
    # subprocesses from the main process down
    get_pids_process = subprocess.Popen(['ps', '-e',
                                         '-o', 'ppid=', '-o', 'pid='],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
    (stdout, stderr) = get_pids_process.communicate()
    if get_pids_process.returncode != 0:
      raise RuntimeError('Failed to get subprocesses of process: {0}'
                         .format(p.pid))

    # Create the process map
    pid_map = {}
    for line in stdout.strip().split('\n'):
      (ppid, pid) = re.match(r'\s*(\d+)\s+(\d+)', line).groups()
      ppid = int(ppid)
      pid = int(pid)
      children = pid_map.get(ppid)
      if not children:
        pid_map[ppid] = [pid]
      else:
        children.append(pid)

    # Expand all descendants of the main process
    all_pids = [p.pid]
    to_process = [p.pid]
    while to_process:
      current = to_process.pop()
      children = pid_map.get(current)
      if children:
        to_process.extend(children)
        all_pids.extend(children)

    # Kill all the subprocesses we found
    for pid in all_pids:
      _KillPID(pid)

    # put this in if you need extra info from the process itself
    # print p.communicate()


def _IsTaskKillError(stderr):
  """Returns whether the stderr output of taskkill indicates it failed.

  Args:
    stderr: the string error output of the taskkill command

  Returns:
    True iff the stderr is considered to represent an actual error.
  """
  # The taskkill "reason" string indicates why it fails. We consider the
  # following reasons to be acceptable. Reason strings differ among different
  # versions of taskkill. If you know a string is specific to a version, feel
  # free to document that here.
  non_error_reasons = (
      # The process might be in the midst of exiting.
      'Access is denied.',
      'The operation attempted is not supported.',
      'There is no running instance of the task.',
      'There is no running instance of the task to terminate.')
  non_error_patterns = (
      re.compile(r'The process "\d+" not found\.'),)
  for reason in non_error_reasons:
    if reason in stderr:
      return False
  for pattern in non_error_patterns:
    if pattern.search(stderr):
      return False

  return True


def _KillPID(pid):
  """Kills the given process with SIGTERM, then with SIGKILL if it doesn't stop.

  Args:
    pid: The process id of the process to check.
  """
  try:
    # Try sigterm first.
    os.kill(pid, signal.SIGTERM)

    # If still running, wait a few seconds to see if it dies.
    deadline = time.time() + 3
    while time.time() < deadline:
      if not _IsStillRunning(pid):
        return
      time.sleep(0.1)

    # No luck, just force kill it.
    os.kill(pid, signal.SIGKILL)
  except OSError as error:
    # Raise original stack trace.
    if 'No such process' not in error.strerror:
      (_, i, st) = sys.exc_info()
      raise i, None, st


def _IsStillRunning(pid):
  """Determines if the given pid is still running.

  Args:
    pid: The process id of the process to check.

  Returns:
    bool, True if it is still running.
  """
  try:
    (actual_pid, code) = os.waitpid(pid, os.WNOHANG)
    if (actual_pid, code) == (0, 0):
      return True
  except OSError as error:
    # Raise original stack trace.
    if 'No child processes' not in error.strerror:
      (_, i, st) = sys.exc_info()
      raise i, None, st
  return False
