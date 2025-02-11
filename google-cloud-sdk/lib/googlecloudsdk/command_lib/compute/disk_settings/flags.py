# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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

"""Flags and helpers for the compute disk-settings commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import completers as compute_completers


def AddDiskSettingArg(parser):
  group = parser.add_group(
      mutex=True, required=True, help='Scope for disk settings.'
  )

  group.add_argument(
      '--zone',
      help='Zone for disk settings',
      completer=compute_completers.ZonesCompleter,
  )

  group.add_argument(
      '--region',
      help='region for disk settings',
      completer=compute_completers.RegionsCompleter,
  )


POLICY_OPTIONS = {
    'all-regions': 'All regions will be allowed to access the source disk.',
    'specific-regions': (
        'Only the specified regions will be allowed to access the source disk.'
    ),
}


def AddUpdateDiskSettingsFlags(parser):
  """Add flags for updating disk settings."""
  parser.add_argument(
      '--add-access-locations',
      help='Access locations to add to disk settings',
      metavar='ADD_ACCESS_LOCATIONS',
      type=arg_parsers.ArgList(),
  )
  parser.add_argument(
      '--remove-access-locations',
      help='Access locations to remove from disk settings',
      metavar='REMOVE_ACCESS_LOCATIONS',
      type=arg_parsers.ArgList(),
  )

  parser.add_argument(
      '--access-location-policy',
      help="""The access location policy for disk settings""",
      metavar='ACCESS_LOCATION_POLICY',
      choices=POLICY_OPTIONS,
  )
