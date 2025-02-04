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

"""Flags and helpers for the compute snapshot-settings commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute import completers as compute_completers


def AddSnapshotSettingArg(parser):
  parser.add_argument(
      '--region',
      help='region for regional snapshot settings',
      completer=compute_completers.RegionsCompleter,
  )


def AddUpdateSnapshotSettingsStorageLocationFlags(parser):
  """Add flags for updating snapshot settings storage location.

  Args:
    parser: argparse.ArgumentParser.
  """
  parser.add_argument(
      '--storage-location-policy',
      help="""The storage location policy. For more information, refer to the
        snapshot settings documentation at
        https://cloud.google.com/compute/docs/disks/snapshot-settings.
        STORAGE_LOCATION_POLICY must be one of: local-region,
        nearest-multi-region, specific-locations.""",
      metavar='STORAGE_LOCATION_POLICY',
  )

  parser.add_argument(
      '--storage-location-names',
      help="""The custom storage location that you specify for the project's
        snapshots. You can specify only a single location. Use this flag only
        when you use the specific-locations value for the
        `--storage-location-policy` flag. For more information, refer to the
        snapshot settings documentation at
        https://cloud.google.com/compute/docs/disks/snapshot-settings.""",
      metavar='STORAGE_LOCATION_NAMES',
      type=arg_parsers.ArgList(),
  )

  modified_async_flag = base.Argument(
      '--async',
      action='store_true',
      dest='async_',
      help=(
          'Return immediately, without waiting for the operation in progress to'
          ' complete.'
      ),
  )
  modified_async_flag.AddToParser(parser)


def AddUpdateSnapshotSettingsAccessLocationFlags(parser):
  """Add flags for updating snapshot settings access location.

  Args:
    parser: argparse.ArgumentParser.
  """
  parser.add_argument(
      '--add-access-locations',
      help='Access locations to add to snapshot settings',
      metavar='ADD_ACCESS_LOCATIONS',
      type=arg_parsers.ArgList(),
  )
  parser.add_argument(
      '--remove-access-locations',
      help='Access locations to remove from snapshot settings',
      metavar='REMOVE_ACCESS_LOCATIONS',
      type=arg_parsers.ArgList(),
  )
  parser.add_argument(
      '--access-location-policy',
      help="""The access location policy. ACCESS_LOCATION_POLICY must be one of: all-regions, specific-regions.""",
      metavar='ACCESS_LOCATION_POLICY',
  )
