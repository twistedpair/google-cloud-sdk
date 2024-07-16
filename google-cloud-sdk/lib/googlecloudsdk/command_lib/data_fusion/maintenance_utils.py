# -*- coding: utf-8 -*- #
# Copyright 2024 Google Inc. All Rights Reserved.
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
"""Command utilities for maintenance."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.data_fusion import datafusion as df
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions

CLEAR_MAINTENANCE_WINDOW_FLAG = base.Argument(
    '--clear-maintenance-window',
    action='store_true',
    help="""\
    Clear the maintenance window for this Data Fusion instance.
    """)

MAINTENANCE_WINDOW_START = base.Argument(
    '--maintenance-window-start',
    type=arg_parsers.Datetime.Parse,
    help="""\
    The start time of the maintenance window. Only the time of the day is
    used as a reference for a starting time of the window with a provided
    recurrence. This flag must be specified if any of the other arguments in
    this group are specified. For example:
      --maintenance_window_start=2024-01-01T01:00:00Z.
    See $ gcloud topic datetimes for information on time formats.
    """)

MAINTENANCE_WINDOW_END = base.Argument(
    '--maintenance-window-end',
    type=arg_parsers.Datetime.Parse,
    help="""\
    The end time of the maintenance window. Only the time of the day is
    used as a reference for an ending time of the window with a provided
    recurrence. This will be used in conjunction with start time, and
    the difference will determine the length of a single maintenance
    window. This flag must be specified if any of the other arguments in this
    group are specified. For example:
      --maintenance_window_end=2024-01-02T01:00:00Z.
    See $ gcloud topic datetimes for information on time formats.
    """)

MAINTENANCE_WINDOW_RECURRENCE = base.Argument(
    '--maintenance-window-recurrence',
    type=str,
    help="""\
    An RFC 5545 RRULE, specifying how the maintenance window will recur.
    Only FREQ=WEEKLY format is supported. This flag must be specified if
    any of the other arguments in this group are specified. For example:
      --maintenance_window_recurrence="FREQ=WEEKLY;BYDAY=FR,SA,SU".
    """)

MAINTENANCE_WINDOW_GROUP_DESCRIPTION = (
    'Group of arguments for setting the maintenance window value.')


def CreateArgumentsGroup(parser):
  """Adds argument group for creating maintenance window.

  Args:
    parser: parser to which the group of flags should be added.
  """
  group = parser.add_group(MAINTENANCE_WINDOW_GROUP_DESCRIPTION)
  MAINTENANCE_WINDOW_START.AddToParser(group)
  MAINTENANCE_WINDOW_END.AddToParser(group)
  MAINTENANCE_WINDOW_RECURRENCE.AddToParser(group)


def UpdateArgumentsGroup(parser):
  """Adds argument group for updating maintenance window.

  Args:
    parser: parser to which the group of flags should be added.
  """
  update_group = parser.add_mutually_exclusive_group()
  maintenance_window_group = update_group.add_group(
      MAINTENANCE_WINDOW_GROUP_DESCRIPTION)
  MAINTENANCE_WINDOW_START.AddToParser(maintenance_window_group)
  MAINTENANCE_WINDOW_END.AddToParser(maintenance_window_group)
  MAINTENANCE_WINDOW_RECURRENCE.AddToParser(maintenance_window_group)
  CLEAR_MAINTENANCE_WINDOW_FLAG.AddToParser(update_group)


def SetMaintenanceWindow(args, instance):
  """Validates maintenance window flags and sets the maintenance window value.
  """
  maintenance_window_start = args.maintenance_window_start
  maintenance_window_end = args.maintenance_window_end
  maintenance_window_recurrence = args.maintenance_window_recurrence
  if (maintenance_window_start or
      maintenance_window_end or
      maintenance_window_recurrence):
    if not maintenance_window_start:
      raise exceptions.RequiredArgumentException(
          '--maintenance-window-start',
          'must be specified.')
    if not maintenance_window_end:
      raise exceptions.RequiredArgumentException(
          '--maintenance-window-end',
          'must be specified.')
    if not maintenance_window_recurrence:
      raise exceptions.RequiredArgumentException(
          '--maintenance-window-recurrence',
          'must be specified.')

    datafusion = df.Datafusion()
    instance.maintenancePolicy = datafusion.messages.MaintenancePolicy(
        maintenanceWindow=datafusion.messages.MaintenanceWindow(
            recurringTimeWindow=datafusion.messages.RecurringTimeWindow(
                window=datafusion.messages.TimeWindow(
                    startTime=maintenance_window_start.isoformat().
                    replace('+00:00', 'Z'),
                    endTime=maintenance_window_end.isoformat().
                    replace('+00:00', 'Z'),
                ),
                recurrence=maintenance_window_recurrence,
            ),
        )
    )


def UpdateMaintenanceWindow(args, instance):
  """Validates maintenance window flags and sets the maintenance window value.
  """
  if args.clear_maintenance_window:
    instance.maintenancePolicy = None
  else:
    SetMaintenanceWindow(args, instance)
