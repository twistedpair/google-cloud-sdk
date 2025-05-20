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
"""Flags and helpers for the compute snapshot groups commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags


def MakeSnapshotGroupArg(plural=False):
  return compute_flags.ResourceArgument(
      resource_name='snapshot-group',
      name='snapshot_group_name',
      completer=compute_completers.RoutesCompleter,
      plural=plural,
      global_collection='compute.snapshotGroups',
  )

SOURCE_INSTANT_SNAPSHOT_GROUP_ARG = compute_flags.ResourceArgument(
    resource_name='source instant snapshot group',
    name='--source-instant-snapshot-group',
    completer=compute_completers.InstantSnapshotGroupsCompleter,
    short_help="""
    The name or URL of the source instant snapshot group. If the name is provided, the instant snapshot group's zone
    or region must be specified with --source-instant-snapshot-group-zone or
    --source-instant-snapshot-group-region accordingly.
    To create a snapshot group from an instant snapshot group in a different project, specify the full path to the instant snapshot group.
    If the URL is provided, format should be:
    https://www.googleapis.com/compute/v1/projects/MY-PROJECT/zones/MY-ZONE/instantSnapshotGroups/MY-INSTANT-SNAPSHOT-GROUP
    """,
    zonal_collection='compute.instantSnapshotGroups',
    regional_collection='compute.regionInstantSnapshotGroups',
    required=True,
)

