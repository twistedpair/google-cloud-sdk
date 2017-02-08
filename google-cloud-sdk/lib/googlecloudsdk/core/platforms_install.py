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


# TODO(user): b/34807345 -- print to stderr
def _TraceAction(action):
  """Prints action to the standard output -- not really standard practice."""
  print action


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
    _TraceAction("""\
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

  _TraceAction("""\
The following directory has been added to your PATH.
  {bin_path}

Create a new command shell for the changes to take effect.
""".format(bin_path=bin_path))


def _GetRcContents(comment, rc_path, rc_contents, pattern=None):
  """Generates the RC file contents with new comment and `source rc_path` lines.

  Args:
    comment: The shell comment string that precedes the source line.
    rc_path: The path of the rc file to source.
    rc_contents: The current contents.
    pattern: A regex pattern that matches comment, None for exact match on
      comment.

  Returns:
    The comment and `source rc_path` lines to be inserted into a shell rc file.
  """
  if not pattern:
    pattern = re.escape(comment)
  # This pattern handles all three variants that we have injected in user RC
  # files. All have the same sentinel comment line followed by:
  #   1. a single 'source ...' line
  #   2. a 3 line if-fi (a bug because this pattern was previously incorrect)
  #   3. finally a single if-fi line.
  # If you touch this code ONLY INJECT ONE LINE AFTER THE SENTINEL COMMENT LINE.
  #
  # At some point we can drop the alternate patterns and only search for the
  # sentinel comment line and assume the next line is ours too (that was the
  # original intent before th 3-line form was added).
  subre = re.compile('\n' + pattern + '\n('
                     "source '.*'"
                     '|'
                     'if .*; then\n  source .*\nfi'
                     '|'
                     'if .*; then source .*; fi'
                     ')\n', re.MULTILINE)
  # script checks that the rc_path currently exists before sourcing the file
  line = ("\n{comment}\nif [ -f '{rc_path}' ]; then source '{rc_path}'; fi\n"
          .format(comment=comment, rc_path=rc_path))
  filtered_contents = subre.sub('', rc_contents)
  rc_contents = '{filtered_contents}{line}'.format(
      filtered_contents=filtered_contents, line=line)
  return rc_contents


class _RcUpdater(object):
  """Updates the RC file completion and PATH code injection."""

  def __init__(self, completion_update, path_update, shell, rc_path, sdk_root):
    self.completion_update = completion_update
    self.path_update = path_update
    self.rc_path = rc_path
    self.completion = os.path.join(
        sdk_root, 'completion.{shell}.inc'.format(shell=shell))
    self.path = os.path.join(
        sdk_root, 'path.{shell}.inc'.format(shell=shell))

  def Update(self):
    """Creates or updates the RC file."""
    if self.rc_path:

      if os.path.isfile(self.rc_path):
        with open(self.rc_path) as rc_file:
          rc_contents = rc_file.read()
          original_rc_contents = rc_contents
      else:
        rc_contents = ''
        original_rc_contents = ''

      if self.path_update:
        rc_contents = _GetRcContents(
            '# The next line updates PATH for the Google Cloud SDK.',
            self.path, rc_contents)

      if self.completion_update:
        rc_contents = _GetRcContents(
            '# The next line enables shell command completion for gcloud.',
            self.completion, rc_contents,
            pattern=('# The next line enables [a-z][a-z]*'
                     ' command completion for gcloud.'))

      if rc_contents == original_rc_contents:
        _TraceAction('No changes necessary for [{rc}].'.format(rc=self.rc_path))
        return

      if os.path.exists(self.rc_path):
        rc_backup = self.rc_path + '.backup'
        _TraceAction('Backing up [{rc}] to [{backup}].'.format(
            rc=self.rc_path, backup=rc_backup))
        shutil.copyfile(self.rc_path, rc_backup)

      with open(self.rc_path, 'w') as rc_file:
        rc_file.write(rc_contents)

      _TraceAction('[{rc_path}] has been updated.'.format(rc_path=self.rc_path))
      _TraceAction(console_io.FormatRequiredUserAction(
          'Start a new shell for the changes to take effect.'))

    if not self.completion_update:
      _TraceAction(console_io.FormatRequiredUserAction(
          'Source [{rc}]in your profile to enable shell command completion for '
          'gcloud.'.format(rc=self.completion)))

    if not self.path_update:
      _TraceAction(console_io.FormatRequiredUserAction(
          'Source [{rc}] in your profile to add the Google Cloud SDK command '
          'line tools to your $PATH.'.format(rc=self.path)))


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


def _GetRcUpdater(completion_update, path_update, rc_path, sdk_root, host_os):
  """Returns an _RcUpdater object for the preferred user shell.

  Args:
    completion_update: bool, Whether or not to do command completion.
    path_update: bool, Whether or not to update PATH.
    rc_path: str, The path to the rc file to update. If None, ask.
    sdk_root: str, The path to the Cloud SDK root.
    host_os: str, The host os identification string.

  Returns:
    An _RcUpdater() object for the preferred user shell.
  """

  # An initial guess on the preferred user shell based on the environment.
  preferred_shell = _GetPreferredShell(os.environ.get('SHELL', '/bin/sh'))
  if not completion_update and not path_update:
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

  return _RcUpdater(completion_update, path_update, preferred_shell, rc_path,
                    sdk_root)


def UpdateRC(completion_update, path_update, rc_path, bin_path, sdk_root):
  """Update the system path to include bin_path.

  Args:
    completion_update: bool, Whether or not to do command completion. If None,
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

  if completion_update is None:
    if path_update is None:  # Ask only one question if both were not set.
      path_update = console_io.PromptContinue(
          prompt_string=('\nModify profile to update your $PATH '
                         'and enable shell command completion?'))
      completion_update = path_update
    else:
      completion_update = console_io.PromptContinue(
          prompt_string=('\nModify profile to enable shell command '
                         'completion?'))
  elif path_update is None:
    path_update = console_io.PromptContinue(
        prompt_string=('\nModify profile to update your $PATH?'))

  _GetRcUpdater(
      completion_update, path_update, rc_path, sdk_root, host_os).Update()
