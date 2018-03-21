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

"""The local coshell module.

A coshell is an interactive non-login /bin/bash running as a coprocess. It has
the same stdin, stdout and stderr as the caller and reads command lines from a
pipe. Only one command runs at a time. ^C interrupts and kills the currently
running command but does not kill the coshell. The coshell process exits when
the shell 'exit' command is executed. State is maintained by the coshell across
commands, including the current working directory and local and environment
variables. The "$ENV" file, if it exists, is sourced into the coshell at
startup. This gives the caller the opportunity to set up aliases and default
'set -o ...' shell modes.

Usage:
  cosh = coshell.Coshell()
  while True:
    command = <the next command line to run>
    try:
      command_exit_status = cosh.Run(command)
    except coshell.CoshellExitException:
      break
  coshell_exit_status = cosh.Close()

This module contains three Coshell implementations:
  * _UnixCoshell using /bin/bash
  * _MinGWCoshell using MinGW bash or git bash
  * _WindowsCoshell using cmd.exe, does not support state across commands
On the first instantiation Coshell.__init__() determines what implementation to
use.  All subsequent instantiations will use the same implementation.
"""

from __future__ import unicode_literals

import abc
import os
import re
import signal
import subprocess


_GET_COMPLETIONS_SHELL_FUNCTION = r"""
__get_completions__() {
  # prints the completions for the (partial) command line "$@" followed by
  # a blank line

  local command completion_function
  local COMP_CWORD COMP_LINE COMP_POINT COMP_WORDS COMPREPLY=()

  (( $# )) || {
    printf '\n'
    return
  }

  command=$1
  shift
  COMP_WORDS=("$@")

  # load bash-completion if necessary
  declare -F _completion_loader &>/dev/null || {
    source /usr/share/bash-completion/bash_completion 2>/dev/null || {
      _completion_loader() {
        return 1
      }
      return
    }
  }

  # get the command specific completion function
  set -- $(complete -p "$command" 2>/dev/null)
  if (( $# )); then
    shift $(( $# - 2 ))
    completion_function=$1
  else
    # check the _completion_loader
    (( $# )) || {
      # load the completion function for the command
      _completion_loader "$command"

      # get the command specific completion function
      set -- $(complete -p "$command" 2>/dev/null)
      (( $# )) || {
        printf '\n'
        return
      }
      shift $(( $# - 2 ))
      completion_function=$1
    }
  fi

  # set up the completion call stack -- really, this is the api?
  COMP_LINE=${COMP_WORDS[*]}
  COMP_POINT=${#COMP_LINE}

  # add '' to COMP_WORDS if the last character of the command line is a space
  [[ ${COMP_LINE[@]: -1} = ' ' ]] && COMP_WORDS+=('')

  # index of the last word
  COMP_CWORD=$(( ${#COMP_WORDS[@]} - 1 ))

  # execute the completion function
  $completion_function

  # print the completions to stdout
  printf '%s\n' "${COMPREPLY[@]}" ''
}
"""


class CoshellExitException(Exception):
  """The coshell exited."""

  def __init__(self, message, status=None):
    super(CoshellExitException, self).__init__(message)
    self.status = status


class _CoshellBase(object):
  """The local coshell base class.

  Attributes:
    _edit_mode: The coshell edit mode, one of {'emacs', 'vi'}.
    _ignore_eof: True if the coshell should ignore EOF on stdin and not exit.
    _state_is_preserved: True if shell process state is preserved across Run().
  """

  __metaclass__ = abc.ABCMeta

  def __init__(self, state_is_preserved=True):
    # Immutable coshell object properties.
    self._state_is_preserved = state_is_preserved
    # Mutable shell modes controlled by `set -o ...` and `set +o ...`.
    self._edit_mode = 'emacs'
    self._ignore_eof = False

  @property
  def edit_mode(self):
    return self._edit_mode

  @property
  def ignore_eof(self):
    return self._ignore_eof

  @property
  def state_is_preserved(self):
    return self._state_is_preserved

  @staticmethod
  def _ShellStatus(status):
    """Returns the shell $? status given a python Popen returncode."""
    if status is None:
      status = 0
    elif status < 0:
      status = 256 - status
    return status

  def Close(self):
    """Closes the coshell connection and release any resources."""
    pass

  @abc.abstractmethod
  def Run(self, command, check_modes=True):
    """Runs command in the coshell and waits for it to complete.

    Args:
      command: The command line string to run. Must be a sytactically complete
        shell statement. Nothing is executed if there is a syntax error.
      check_modes: If True runs self._GetModes() after command has executed if
        command contains `set -o ...` or `set +o ...`.
    """
    pass

  @abc.abstractmethod
  def Interrupt(self, sig):
    """Sends the interrupt signal to the coshell."""
    pass

  def GetCompletions(self, args):
    """Returns the list of completion choices for args.

    Args:
      args: The list of command line argument strings to complete.
    """
    del args
    return None

  def Communicate(self, args):
    """Runs args and returns the list of output lines, up to first empty one.

    Args:
      args: The list of command line arguments.

    Returns:
      The list of output lines from command args up to the first empty line.
    """
    del args
    return []


class _UnixCoshellBase(_CoshellBase):
  """The unix local coshell base class.

  Attributes:
    _shell: The coshell subprocess object.
  """

  __metaclass__ = abc.ABCMeta

  SHELL_STATUS_EXIT = 'x'
  SHELL_STATUS_FD = 9
  SHELL_STDIN_FD = 8

  def __init__(self):
    super(_UnixCoshellBase, self).__init__()
    self.status = None  # type: int
    self._status_fd = None  # type: int
    self._shell = None  # type: subprocess.Popen

  @staticmethod
  def _Quote(command):
    """Quotes command in single quotes so it can be eval'd in coshell."""
    return "'{}'".format(command.replace("'", r"'\''"))

  def _Exited(self):
    """Raises the coshell exit exception."""
    try:
      self._shell.communicate(':')
    except (IOError, OSError, ValueError):
      # Yeah, ValueError for IO on a closed file.
      pass
    status = self._ShellStatus(self._shell.returncode)
    raise CoshellExitException(
        'The coshell exited [status={}].'.format(status),
        status=status)

  def _SendCommand(self, command):
    """Sends command to the coshell for execution."""
    try:
      self._shell.stdin.write(command + '\n')
    except (IOError, OSError, ValueError):
      # Yeah, ValueError for IO on a closed file.
      self._Exited()

  def _GetStatus(self):
    """Gets the status of the last command sent to the coshell."""
    status_string = ''
    while True:
      c = os.read(self._status_fd, 1)
      if c in (None, '\n', self.SHELL_STATUS_EXIT):
        break
      status_string += c
    if not status_string.isdigit() or c == self.SHELL_STATUS_EXIT:
      self._Exited()
    return int(status_string)

  def _GetModes(self):
    """Syncs the user settable modes of interest to the Coshell."""

    # Get the caller $ENV emacs/vi mode.
    if self.Run('set -o | grep -q "^vi.*on"', check_modes=False) == 0:
      self._edit_mode = 'vi'
    else:
      self._edit_mode = 'emacs'

    # Get the caller $ENV ignoreeof setting.
    self._ignore_eof = self.Run(
        'set -o | grep -q "^ignoreeof.*on"', check_modes=False) == 0

  def _GetUserConfigDefaults(self):
    """Consults the user shell config for defaults."""

    self._SendCommand(
        # Set $? to $1.
        '_status() {{ return $1; }};'
        # The $ENV file configures aliases and set -o modes.
        '[ -f "$ENV" ] && . "$ENV";'
        # The exit command hits this trap, reaped by _GetStatus() in Run().
        "trap 'echo $?{exit} >&{fdstatus}' 0;"
        # This catches interrupts so commands die while the coshell stays alive.
        'trap ":" 2;{get_completions}'
        .format(exit=self.SHELL_STATUS_EXIT,
                fdstatus=self.SHELL_STATUS_FD,
                get_completions=_GET_COMPLETIONS_SHELL_FUNCTION))

    # Enable job control if supported.
    self._SendCommand('set -o monitor 2>/dev/null')

    # Enable alias expansion if supported.
    self._SendCommand('shopt -s expand_aliases 2>/dev/null')

    # Sync the user settable modes to the coshell.
    self._GetModes()

    # Set $? to 0.
    self._SendCommand('true')

  @abc.abstractmethod
  def _Run(self, command, check_modes=True):
    """Runs command in the coshell and waits for it to complete."""
    pass

  def Run(self, command, check_modes=True):
    """Runs command in the coshell and waits for it to complete."""
    status = 130  # assume the worst: 128 (had signal) + 2 (it was SIGINT)
    sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
      status = self._Run(command, check_modes=check_modes)
    except KeyboardInterrupt:
      pass
    finally:
      signal.signal(signal.SIGINT, sigint)
    return status

  def Interrupt(self):
    """Sends the interrupt signal to the coshell."""
    self._shell.send_signal(signal.SIGINT)


class _UnixCoshell(_UnixCoshellBase):
  """The unix local coshell implementation.

  This implementation preserves coshell process state across Run().

  Attributes:
    _status_fd: The read side of the pipe where the coshell write 1 char status
      lines. The status line is used to mark the exit of the currently running
      command.
  """

  SHELL_PATH = '/bin/bash'

  def __init__(self):
    super(_UnixCoshell, self).__init__()

    # The dup/close/dup dance preserves caller fds that collide with SHELL_*_FD.

    try:
      caller_shell_status_fd = os.dup(self.SHELL_STATUS_FD)
    except OSError:
      caller_shell_status_fd = -1
    os.dup2(1, self.SHELL_STATUS_FD)

    try:
      caller_shell_stdin_fd = os.dup(self.SHELL_STDIN_FD)
    except OSError:
      caller_shell_stdin_fd = -1
    os.dup2(0, self.SHELL_STDIN_FD)

    self._status_fd, w = os.pipe()
    os.dup2(w, self.SHELL_STATUS_FD)
    os.close(w)

    self._shell = subprocess.Popen(
        [self.SHELL_PATH], stdin=subprocess.PIPE, close_fds=False)

    if caller_shell_status_fd >= 0:
      os.dup2(caller_shell_status_fd, self.SHELL_STATUS_FD)
      os.close(caller_shell_status_fd)
    else:
      os.close(self.SHELL_STATUS_FD)

    if caller_shell_stdin_fd >= 0:
      os.dup2(caller_shell_stdin_fd, self.SHELL_STDIN_FD)
      os.close(caller_shell_stdin_fd)
    else:
      os.close(self.SHELL_STDIN_FD)

    self._GetUserConfigDefaults()

  def Close(self):
    """Closes the coshell connection and release any resources."""
    if self._status_fd >= 0:
      os.close(self._status_fd)
      self._status_fd = -1
    try:
      self._shell.communicate('exit')  # This closes internal fds.
    except (IOError, ValueError):
      # Yeah, ValueError for IO on a closed file.
      pass
    return self._ShellStatus(self._shell.returncode)

  def _Run(self, command, check_modes=True):
    """Runs command in the coshell and waits for it to complete."""
    self._SendCommand(
        'command eval {command} <&{fdin} && echo 0 >&{fdstatus} || '
        '{{ status=$?; echo $status 1>&{fdstatus}; _status $status; }}'.format(
            command=self._Quote(command),
            fdstatus=self.SHELL_STATUS_FD,
            fdin=self.SHELL_STDIN_FD))
    status = self._GetStatus()

    # Re-check shell shared modes.
    if check_modes and re.search(r'\bset\s+[-+]o\s+\w', command):
      self._GetModes()

    return status

  def Communicate(self, args):
    """Runs args and returns the list of output lines, up to first empty one.

    Args:
      args: The list of command line arguments.

    Returns:
      The list of output lines from command args up to the first empty line.
    """
    self._SendCommand('{command} >&{fdstatus}\n'.format(
        command=' '.join([self._Quote(arg) for arg in args]),
        fdstatus=self.SHELL_STATUS_FD))
    lines = []
    line = []
    while True:
      try:
        c = os.read(self._status_fd, 1)
      except (IOError, OSError, ValueError):
        # Yeah, ValueError for IO on a closed file.
        self._Exited()
      if c in (None, '\n'):
        if not line:
          break
        lines.append(''.join(line).rstrip())
        line = []
      else:
        line.append(c)
    return lines

  def GetCompletions(self, args):
    """Returns the list of completion choices for args.

    Args:
      args: The list of command line argument strings to complete.

    Returns:
      The list of completions for args.
    """
    return sorted(self.Communicate(['__get_completions__'] + args))


class _MinGWCoshell(_UnixCoshellBase):
  """The MinGW local coshell implementation.

  This implementation preserves coshell process state across Run().

  NOTE: The Windows subprocess module passes fds 0,1,2 to the child process and
  no others. It is possble to pass handles that can be converted to/from fds,
  but the child process needs to know what handles to convert back to fds. Until
  we figure out how to reconstitute handles as fds >= 3 we are stuck with
  restricting fds 0,1,2 to be /dev/tty. Luckily this works for the shell
  interactive prompt. Unfortunately this fails for the test environment.
  """

  SHELL_PATH = None  # Determined by the Coshell dynamic class below.
  STDIN_PATH = '/dev/tty'
  STDOUT_PATH = '/dev/tty'

  def __init__(self):
    super(_MinGWCoshell, self).__init__()
    self._shell = self._Popen()
    self._GetUserConfigDefaults()

  def _Popen(self):
    """Mockable popen+startupinfo so we can test on Unix."""
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dWflags = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen([self.SHELL_PATH],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            startupinfo=startupinfo)

  def Close(self):
    """Closes the coshell connection and release any resources."""
    try:
      self._shell.communicate('exit')  # This closes internal fds.
    except (IOError, ValueError):
      # Yeah, ValueError for IO on a closed file.
      pass
    return self._ShellStatus(self._shell.returncode)

  def _GetStatus(self):
    """Gets the status of the last command sent to the coshell."""
    status_string = self._shell.stdout.readline().strip()
    if status_string.endswith(self.SHELL_STATUS_EXIT):
      c = self.SHELL_STATUS_EXIT
      status_string = status_string[:-1]
    else:
      c = ''
    if not status_string.isdigit() or c == self.SHELL_STATUS_EXIT:
      self._Exited()
    return int(status_string)

  def _Run(self, command, check_modes=True):
    """Runs command in the coshell and waits for it to complete."""
    self._SendCommand(
        "command eval {command} <'{stdin}' >>'{stdout}' && echo 0 || "
        "{{ status=$?; echo 1; (exit $status); }}".format(
            command=self._Quote(command),
            stdin=self.STDIN_PATH,
            stdout=self.STDOUT_PATH,
        ))
    status = self._GetStatus()

    # Re-check shell shared modes.
    if check_modes and re.search(r'\bset\s+[-+]o\s+\w+', command):
      self._GetModes()

    return status

  def Interrupt(self):
    """Sends the interrupt signal to the coshell."""
    self._shell.send_signal(signal.CTRL_C_EVENT)  # pytype: disable=module-attr


class _WindowsCoshell(_CoshellBase):
  """The windows local coshell implementation.

  This implementation does not preserve shell coprocess state across Run().
  """

  def __init__(self):
    super(_WindowsCoshell, self).__init__(state_is_preserved=False)

  def Run(self, command, check_modes=False):
    """Runs command in the coshell and waits for it to complete."""
    del check_modes
    return subprocess.call(command, shell=True)

  def Interrupt(self):
    """Sends the interrupt signal to the coshell."""
    pass


def _RunningOnWindows():
  """Lightweight mockable Windows check."""
  try:
    return bool(WindowsError)  # pytype: disable=name-error
  except NameError:
    return False


class Coshell(object):
  """The local coshell implementation shim.

  This shim class delays os specific checks until the first instantiation. The
  checks are memoized in the shim class for subsequent instantiations.
  """

  _IMPLEMENTATION = None

  def __new__(cls, *args, **kwargs):
    if not cls._IMPLEMENTATION:
      if _RunningOnWindows():
        cls._IMPLEMENTATION = _WindowsCoshell
        # We do an explicit search rather than PATH lookup because:
        # (1) It's not clear that a git or MinGW installation automatically
        #     sets up PATH to point to sh.exe.
        # (2) Picking up any old sh.exe on PATH on a Windows system is dicey.
        for shell in [r'C:\MinGW\bin\sh.exe',
                      r'C:\Program Files\Git\bin\sh.exe']:
          if os.path.isfile(shell):
            cls._IMPLEMENTATION = _MinGWCoshell
            cls._IMPLEMENTATION.SHELL_PATH = shell
            break
      else:
        cls._IMPLEMENTATION = _UnixCoshell
    obj = cls._IMPLEMENTATION.__new__(cls._IMPLEMENTATION, *args, **kwargs)
    obj.__init__()  # The docs say this is unnecessary.
    return obj
