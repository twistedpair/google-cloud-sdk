# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Common flags for some of the Looker commands.

Flags are specified with functions that take in a single argument, the parser,
and add the newly constructed flag to that parser.

Example:

def AddFlagName(parser):
  parser.add_argument(
    '--flag-name',
    ... // Other flag details.
  )
"""

from googlecloudsdk.command_lib.util import completers


class InstanceCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(InstanceCompleter, self).__init__(
        collection='looker.projects.locations.instances',
        list_command='looker instances list',
        **kwargs)


def AddInstance(parser):
  parser.add_argument(
      '--instance',
      required=True,
      completer=InstanceCompleter,
      help=(
          """ \
              ID of the instance or fully qualified identifier for the instance.
              To set the instance attribute:

              - provide the argument --instance on the command line.
          """
      ))
