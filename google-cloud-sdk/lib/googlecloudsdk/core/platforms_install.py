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

"""Utilities for configuring platform specific installation."""

import os
import re
import shutil

from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import platforms

# pylint:disable=superfluous-parens


# pylint:disable=unused-argument
def _UpdatePathForWindows(bin_path):
  """Update the Windows system path to include bin_path.

  Args:
    bin_path: str, The absolute path to the directory that will contain
        Cloud SDK binaries.
  """

  # pylint:disable=g-import-not-at-top, we want to only attempt these imports
  # on windows.
  try:
    import win32con
    import win32gui
    try:
      # Python 3
      import winreg
    except ImportError:
      # Python 2
      import _winreg as winreg
  except ImportError:
    print("""\
The installer is unable to automatically update your system PATH. Please add
  {path}
to your system PATH to enable easy use of the Cloud SDK Command Line Tools.
""".format(path=bin_path))
    return

  def GetEnv(name):
    root = winreg.HKEY_CURRENT_USER
    subkey = 'Environment'
    key = winreg.OpenKey(root, subkey, 0, winreg.KEY_READ)
    try:
      value, _ = winreg.QueryValueEx(key, name)
    # pylint:disable=undefined-variable, This variable is defined in windows.
    except WindowsError:
      return ''
    return value

  def SetEnv(name, value):
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0,
                         winreg.KEY_ALL_ACCESS)
    winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
    winreg.CloseKey(key)
    win32gui.SendMessage(
        win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')
    return value

  def Remove(paths, value):
    while value in paths:
      paths.remove(value)

  def PrependEnv(name, values):
    paths = GetEnv(name).split(';')
    for value in values:
      if value in paths:
        Remove(paths, value)
      paths.insert(0, value)
    SetEnv(name, ';'.join(paths))

  PrependEnv('Path', [bin_path])

  print("""\
The following directory has been added to your PATH.
  {bin_path}

Create a new command shell for the changes to take effect.
""".format(bin_path=bin_path))


def _GetRcData(comment, rc_path, rc_data, pattern=None):
  """Generates the comment and `source rc_path` lines.

  Args:
    comment: The shell comment string that precedes the source line.
    rc_path: The path of the rc file to source.
    rc_data: The current comment and source rc lines or None.
    pattern: A regex pattern that matches comment, None for exact match on
      comment.

  Returns:
    The comment and `source rc_path` lines to be inserted into a shell rc file.
  """
  if not pattern:
    pattern = re.escape(comment)
  subre = re.compile('\n' + pattern + '\n.*\n', re.MULTILINE)
  line = "{comment}\nsource '{rc_path}'\n".format(
      comment=comment, rc_path=rc_path)
  filtered_data = subre.sub('', rc_data)
  rc_data = '{filtered_data}\n{line}'.format(
      filtered_data=filtered_data, line=line)
  return rc_data


class _RcPaths(object):
  """Pathnames for the updateable rc file and files it may source."""

  def __init__(self, shell, rc_path, sdk_root):
    self.rc_path = rc_path
    self.completion = os.path.join(
        sdk_root, 'completion.{shell}.inc'.format(shell=shell))
    self.path = os.path.join(
        sdk_root, 'path.{shell}.inc'.format(shell=shell))


def _GetPreferredShell(path, default='bash'):
  """Returns the preferred shell name based on the base file name in path.

  Args:
    path: str, The file path to check.
    default: str, The default value to return if a preferred name cannot be
      determined.

  Returns:
    The preferred user shell name or default if none can be determined.
  """
  name = os.path.basename(path)
  for shell in ('bash', 'zsh', 'ksh'):
    if shell in name:
      return shell
  return default


def _GetShellRcFileName(shell, host_os):
  """Returns the RC file name for shell and host_os.

  Args:
    shell: str, The shell base name.
    host_os: str, The host os identification string.

  Returns:
    The shell RC file name, '.bashrc' by default.
  """
  if shell == 'ksh':
    return os.environ.get('ENV', None) or '.kshrc'
  elif shell != 'bash':
    return '.{shell}rc'.format(shell=shell)
  elif host_os == platforms.OperatingSystem.LINUX:
    return '.bashrc'
  elif host_os == platforms.OperatingSystem.MACOSX:
    return '.bash_profile'
  elif host_os == platforms.OperatingSystem.MSYS:
    return '.profile'
  return '.bashrc'


def _GetRcPaths(command_completion, path_update, rc_path, sdk_root, host_os):
  """Returns an _RcPaths object for the preferred user shell.

  Args:
    command_completion: bool, Whether or not to do command completion. If None,
      ask.
    path_update: bool, Whether or not to update PATH. If None, ask.
    rc_path: str, The path to the rc file to update. If None, ask.
    sdk_root: str, The path to the Cloud SDK root.
    host_os: str, The host os identification string.

  Returns:
    An _RcPaths() object for the preferred user shell.
  """

  # An initial guess on the preferred user shell based on the environment.
  preferred_shell = _GetPreferredShell(os.environ.get('SHELL', '/bin/sh'))
  if not command_completion and not path_update:
    rc_path = None
  elif not rc_path:
    file_name = _GetShellRcFileName(preferred_shell, host_os)
    rc_path = os.path.join(platforms.GetHomePath(), file_name)

    rc_path_update = console_io.PromptResponse((
        'The Google Cloud SDK installer will now prompt you to update an rc '
        'file to bring the Google Cloud CLIs into your environment.\n\n'
        'Enter a path to an rc file to update, or leave blank to use '
        '[{rc_path}]:  ').format(rc_path=rc_path))
    if rc_path_update:
      rc_path = os.path.expanduser(rc_path_update)

  if rc_path:
    # Check the rc_path for a better hint at the user preferred shell.
    preferred_shell = _GetPreferredShell(rc_path, default=preferred_shell)

  return _RcPaths(preferred_shell, rc_path, sdk_root)


def UpdateRC(command_completion, path_update, rc_path, bin_path, sdk_root):
  """Update the system path to include bin_path.

  Args:
    command_completion: bool, Whether or not to do command completion. If None,
      ask.
    path_update: bool, Whether or not to update PATH. If None, ask.
    rc_path: str, The path to the rc file to update. If None, ask.
    bin_path: str, The absolute path to the directory that will contain
      Cloud SDK binaries.
    sdk_root: str, The path to the Cloud SDK root.
  """

  host_os = platforms.OperatingSystem.Current()
  if host_os == platforms.OperatingSystem.WINDOWS:
    if path_update is None:
      path_update = console_io.PromptContinue(
          prompt_string='Update %PATH% to include Cloud SDK binaries?')
    if path_update:
      _UpdatePathForWindows(bin_path)
    return

  if command_completion is None:
    if path_update is None:  # Ask only one question if both were not set.
      path_update = console_io.PromptContinue(
          prompt_string=('\nModify profile to update your $PATH '
                         'and enable shell command completion?'))
      command_completion = path_update
    else:
      command_completion = console_io.PromptContinue(
          prompt_string=('\nModify profile to enable shell command '
                         'completion?'))
  elif path_update is None:
    path_update = console_io.PromptContinue(
        prompt_string=('\nModify profile to update your $PATH?'))

  rc_paths = _GetRcPaths(command_completion, path_update, rc_path, sdk_root,
                         host_os)

  if rc_paths.rc_path:
    if os.path.exists(rc_paths.rc_path):
      with open(rc_paths.rc_path) as rc_file:
        rc_data = rc_file.read()
        cached_rc_data = rc_data
    else:
      rc_data = ''
      cached_rc_data = ''

    if path_update:
      rc_data = _GetRcData('# The next line updates PATH for the Google Cloud'
                           ' SDK.', rc_paths.path, rc_data)

    if command_completion:
      rc_data = _GetRcData('# The next line enables shell command completion'
                           ' for gcloud.', rc_paths.completion, rc_data,
                           pattern='# The next line enables [a-z][a-z]*'
                           ' command completion for gcloud.')

    if cached_rc_data == rc_data:
      print('No changes necessary for [{rc}].'.format(rc=rc_paths.rc_path))
      return

    if os.path.exists(rc_paths.rc_path):
      rc_backup = rc_paths.rc_path + '.backup'
      print('Backing up [{rc}] to [{backup}].'.format(
          rc=rc_paths.rc_path, backup=rc_backup))
      shutil.copyfile(rc_paths.rc_path, rc_backup)

    with open(rc_paths.rc_path, 'w') as rc_file:
      rc_file.write(rc_data)

    print("""\
[{rc_path}] has been updated.
Start a new shell for the changes to take effect.
""".format(rc_path=rc_paths.rc_path))

  if not command_completion:
    print("""\
Source [{rc}]
in your profile to enable shell command completion for gcloud.
""".format(rc=rc_paths.completion))

  if not path_update:
    print("""\
Source [{rc}]
in your profile to add the Google Cloud SDK command line tools to your $PATH.
""".format(rc=rc_paths.path))
