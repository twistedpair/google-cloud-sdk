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

"""The edit module allows you to edit a text blob without leaving the shell.

When a user needs to edit a blob of text and you don't want to save to
some location, tell them about it, and have the user re-upload the file, this
module can be used to do a quick inline edit.

It will inspect the environment variable EDITOR to see what tool to use
for editing, defaulting to vi. Then, the EDITOR will be opened in the current
terminal; when it exits, the file will be reread and returned with any edits
that the user may have saved while in the EDITOR.
"""


import os
import tempfile

from googlecloudsdk.third_party.py27 import py27_subprocess as subprocess


class Error(Exception):
  """Exceptions for this module."""


class NoSaveException(Error):
  """NoSaveException is thrown when the user did not save the file."""


def OnlineEdit(text):
  """Edit will edit the provided text.

  Args:
    text: The initial text blob to provide for editing.

  Returns:
    The edited text blob.

  Raises:
    NoSaveException: If the user did not save the temporary file.
    subprocess.CalledProcessError: If the process running the editor has a
        problem.
  """
  fname = tempfile.NamedTemporaryFile(suffix='.txt').name

  with open(fname, 'w') as f_out:
    f_out.write(text)

  # Get the mod time, so we can check if anything was actually done.
  start_mtime = os.stat(fname).st_mtime

  if os.name == 'nt':
    subprocess.check_call([fname], shell=True)
  else:
    editor = os.getenv('EDITOR', 'vi')
    # We use shell=True and manual smashing of the args to permit users to set
    # EDITOR="emacs -nw", or similar things.
    subprocess.check_call('{editor} {file}'.format(editor=editor, file=fname),
                          shell=True)

  end_mtime = os.stat(fname).st_mtime
  if start_mtime == end_mtime:
    raise NoSaveException('edit aborted by user')

  with open(fname) as f_done:
    return f_done.read()
