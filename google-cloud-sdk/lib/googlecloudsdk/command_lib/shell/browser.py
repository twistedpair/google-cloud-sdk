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

"""Tools for launching a browser."""

import os
import subprocess
import sys
import webbrowser

from googlecloudsdk.command_lib.shell import parser
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files


# TODO(b/35395811): Remove subprocess monkeypatch.
class FakeSubprocessModule(object):

  def Popen(self, args, **kwargs):
    devnull = open(os.devnull, 'w')
    kwargs.update({'stderr': devnull, 'stdout': devnull})
    return subprocess.Popen(args, **kwargs)


def OpenReferencePage(cli, line, pos):
  url = _GetReferenceURL(cli, line, pos)
  if not url:
    return
  webbrowser.subprocess = FakeSubprocessModule()
  try:
    browser = webbrowser.get()
    browser.open_new_tab(url)
  except webbrowser.Error as e:
    cli.run_in_terminal(
        lambda: log.error('failed to open browser: %s', e))


# TODO(b/35420203): get reference page for flag, not just command/group.
def _GetReferenceURL(cli, line, pos=None):
  """Determine the reference url of the command/group preceding the pos.

  Args:
    cli: the prompt CLI object
    line: a string with the current string directly from the shell.
    pos: the position of the cursor on the line.

  Returns:
    A string containing the URL of the reference page.
  """
  if pos is None:
    pos = len(line)
  ref = []
  for arg in parser.ParseCommand(cli.root, line):
    if arg.start < pos and (
        not ref or
        arg.token_type in (parser.ArgTokenType.COMMAND,
                           parser.ArgTokenType.GROUP)):
      ref.append(arg.value)
  if cli.restrict and (not ref or ref[0] != cli.restrict):
    ref.insert(0, cli.restrict)
  if not ref:
    return None
  command = ref[0]

  if command == 'gcloud':
    ref[0] = 'https://cloud.google.com/sdk/gcloud/reference'

  elif command == 'bq':
    ref = ['https://cloud.google.com/bigquery/bq-command-line-tool']

  elif command == 'gsutil':
    ref = ['https://cloud.google.com/storage/docs/gsutil']
    if len(ref) > 1:
      ref.append('commands')
      ref.append(ref[1])

  elif command == 'kubectl':
    subcommand = ref[1] if len(ref) > 1 else None
    try:
      full_version = (cli.root[parser.LOOKUP_COMMANDS]['kubectl']
                      [parser.LOOKUP_CLI_VERSION])
      version = '.'.join(full_version.split('.')[0:2])
    except (IndexError, KeyError):
      version = 'v1.8'
    ref = ['https://kubernetes.io/docs/user-guide/kubectl', version]
    if subcommand:
      ref.append('#' + subcommand)

  elif files.FindExecutableOnPath(command):
    if 'darwin' in sys.platform:
      ref = ['https://developer.apple.com/legacy/library/documentation',
             'Darwin/Reference/ManPages/man1']
    else:
      ref = ['http://man7.org/linux/man-pages/man1']
    ref.append(command + '.1.html')

  else:
    return None

  return '/'.join(ref)
