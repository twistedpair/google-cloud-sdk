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
import webbrowser

from googlecloudsdk.command_lib.shell import gcloud_parser
from googlecloudsdk.core import log


# TODO(b/35395811): Remove subprocess monkeypatch.
class FakeSubprocessModule(object):

  def Popen(self, args, **kwargs):
    devnull = open(os.devnull, 'w')
    kwargs.update({'stderr': devnull, 'stdout': devnull})
    return subprocess.Popen(args, **kwargs)


def OpenReferencePage(cli, line, pos):
  url = _GetReferenceURL(line, pos)
  webbrowser.subprocess = FakeSubprocessModule()
  try:
    browser = webbrowser.get()
    browser.open_new_tab(url)
  except webbrowser.Error as e:
    cli.run_in_terminal(
        lambda: log.error('failed to open browser: %s', e))


# TODO(b/35420203): get reference page for flag, not just command/group.
def _GetReferenceURL(line, pos=None):
  """Determine the reference url of the command/group preceeding the pos.

  Args:
    line: a string with the current string directly from the shell.
    pos: the position of the cursor on the line.

  Returns:
    A string containing the URL of the reference page.
  """
  if pos is None:
    pos = len(line)

  prefix = u'https://cloud.google.com/sdk/gcloud/reference/'

  invocations = gcloud_parser.ParseLine(line)
  if not invocations:
    return prefix

  tokens = invocations[-1].tokens
  tokens = [x for x in tokens if x.start < pos]
  invocation = gcloud_parser.GcloudInvocation(tokens)

  cmd = invocation.GetCommandOrGroup()
  if not cmd:
    return prefix
  return prefix + '/'.join(cmd.tree['path'][1:])
