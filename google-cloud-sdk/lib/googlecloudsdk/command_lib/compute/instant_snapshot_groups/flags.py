# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the compute instant snapshot groups commands."""


from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags

_SOURCE_CONSISTENCY_GROUP_DETAILED_HELP = """\
      Source consistency group used to create the instant snapshot group.
"""

MULTISCOPE_LIST_FORMAT = """
    table(
      name,
      location(),
      location_scope(),
      status
      )"""


def MakeInstantSnapshotGroupArg(plural=False):
  return compute_flags.ResourceArgument(
      resource_name='instant snapshot group',
      completer=compute_completers.InstantSnapshotGroupsCompleter,
      plural=plural,
      name='INSTANT_SNAPSHOT_GROUP_NAME',
      zonal_collection='compute.instantSnapshotGroups',
      regional_collection='compute.regionInstantSnapshotGroups',
      zone_explanation=compute_flags.ZONE_PROPERTY_EXPLANATION,
      region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION,
  )


def AddSourceConsistencyGroupArg(parser):
  """Adds instant snapshot group source specific arguments to parser."""
  parser.add_argument(
      '--source-consistency-group',
      help="""
      URL of the source consistency group resource policy. The resource policy
      is always in the same region as the source disks.
      """,
      # This argument is required because instant snapshot group can only be
      # created from a consistency group.
      required=True,
  )
