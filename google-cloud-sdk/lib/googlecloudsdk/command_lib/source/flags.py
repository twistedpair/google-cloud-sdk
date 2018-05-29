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
"""Common arguments for `gcloud source repos` commands."""
from __future__ import absolute_import
from __future__ import unicode_literals
from googlecloudsdk.calliope import arg_parsers

REPO_NAME_VALIDATOR = arg_parsers.RegexpValidator(
    '[A-Za-z0-9_][-_A-Za-z0-9/]{0,127}',
    'repostory name may contain between 1 and 128 (inclusive) letters, digits, '
    'hyphens, underscores and slashes.')


def AddPushblockFlagsToParser(parser):
  """Add pushblock enabled/disabled flags to the parser."""
  pushblocks = parser.add_mutually_exclusive_group(required=True)

  pushblocks.add_argument(
      '--enable-pushblock',
      action='store_true',
      help="""\
Enable PushBlock for all repositories under current project.
PushBlock allows repository owners to block git push transactions containing
private key data.""")

  pushblocks.add_argument(
      '--disable-pushblock',
      action='store_true',
      help="""\
Disable PushBlock for all repositories under current project.
PushBlock allows repository owners to block git push transactions containing
private key data.""")
