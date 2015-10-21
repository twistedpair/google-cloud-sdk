# Copyright 2013 Google Inc. All Rights Reserved.

"""Functions to help with shelling out to other commands."""

import os
import signal
import subprocess
import sys

from googlecloudsdk.core import log


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
  if not env:
    env = dict(os.environ)
  env['CLOUDSDK_WRAPPER'] = '1'
  return env


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


def ArgsForShellTool(executable_path, *args):
  """Constructs an argument list for calling the bash interpreter.

  Args:
    executable_path: str, The full path to the shell script.
    *args: args for the command

  Returns:
    An argument list to execute the bash interpreter
  """
  shell_bin = _GetShellExecutable()
  return _GetToolArgs(shell_bin, [], executable_path, *args)


def ArgsForCMDTool(executable_path, *args):
  """Constructs an argument list for calling the cmd interpreter.

  Args:
    executable_path: str, The full path to the cmd script.
    *args: args for the command

  Returns:
    An argument list to execute the cmd interpreter
  """
  return _GetToolArgs('cmd', ['/c'], executable_path, *args)


def ArgsForBinaryTool(executable_path, *args):
  """Constructs an argument list for calling a native binary.

  Args:
    executable_path: str, The full path to the binary.
    *args: args for the command

  Returns:
    An argument list to execute the native binary
  """
  return _GetToolArgs(None, None, executable_path, *args)


class _ProcessHolder(object):
  PROCESS = None

  @staticmethod
  # pylint: disable=unused-argument
  def Handler(signum, frame):
    if _ProcessHolder.PROCESS:
      _ProcessHolder.PROCESS.terminate()
      ret_val = _ProcessHolder.PROCESS.wait()
    sys.exit(ret_val)


def Exec(args, env=None, no_exit=False, pipe_output_through_logger=False):
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

  Returns:
    int, The exit code of the child if no_exit is True, else this method does
    not return.
  """
  # We use subprocess instead of execv because windows does not support process
  # replacement.  The result of execv on windows is that a new processes is
  # started and the original is killed.  When running in a shell, the prompt
  # returns as soon as the parent is killed even though the child is still
  # running.  subprocess waits for the new process to finish before returning.
  env = _GetToolEnv(env=env)
  signal.signal(signal.SIGTERM, _ProcessHolder.Handler)
  extra_popen_kwargs = {}
  if pipe_output_through_logger:
    extra_popen_kwargs['stderr'] = subprocess.PIPE
    extra_popen_kwargs['stdout'] = subprocess.PIPE

  p = subprocess.Popen(args, env=env, **extra_popen_kwargs)
  _ProcessHolder.PROCESS = p

  if pipe_output_through_logger:
    ret_val = None
    while ret_val is None:
      stdout, stderr = p.communicate()
      log.out.write(stdout)
      log.err.write(stderr)
      ret_val = p.returncode
  else:
    ret_val = p.wait()

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
