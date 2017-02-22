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


# TODO(b/35395811): Remove subprocess monkeypatch.
class FakeSubprocessModule(object):

  def Popen(self, args, **kwargs):
    devnull = open(os.devnull, 'w')
    kwargs.update({'stderr': devnull, 'stdout': devnull})
    return subprocess.Popen(args, **kwargs)


def OpenReferencePage(line, pos):
  tokens = gcloud_parser.ParseLine(line)
  tokens = [x for x in tokens if x.start < pos]
  url = _GetReferenceURL(tokens)
  browser = webbrowser.get()
  webbrowser.subprocess = FakeSubprocessModule()
  browser.open_new_tab(url)


def _GetReferenceURL(tokens):
  prefix = 'https://cloud.google.com/sdk/gcloud/reference/'
  invocation = gcloud_parser.GcloudInvocation(tokens)
  cmd = invocation.GetCommandOrGroup()
  if not cmd:
    return prefix
  return prefix + '/'.join(cmd.tree['path'][1:])
