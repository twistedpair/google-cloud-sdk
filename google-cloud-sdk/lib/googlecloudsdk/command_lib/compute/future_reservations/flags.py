# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the compute future reservations commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.instances import flags as instance_flags
from googlecloudsdk.command_lib.compute.reservations import flags as reservation_flags


def GetNamePrefixFlag():
  """Gets the --name-prefix flag."""
  help_text = """\
  User provided name prefix for system generated reservations when capacity is
  delivered at start time.
  """
  return base.Argument('--name-prefix', help=help_text)


def GetTotalCountFlag(required=True):
  """Gets the --total-count flag."""
  help_text = """\
  The total number of instances for which capacity assurance is requested at a
  future time period.
  """
  return base.Argument(
      '--total-count', required=required, type=int, help=help_text)


def GetStartTimeFlag(required=True):
  """Gets the --start-time flag."""
  return base.Argument(
      '--start-time', required=required, type=str, help=GetStartTimeHelpText())


def GetStartTimeHelpText():
  """Gets the --start-time help text."""
  help_text = """\
  Start time of the Future Reservation. The start time must be an RFC3339 valid
  string formatted by date, time, and timezone or "YYYY-MM-DDTHH:MM:SSZ"; where
  YYYY = year, MM = month, DD = day, HH = hours, MM = minutes, SS = seconds, and
  Z = timezone (i.e. 2021-11-20T07:00:00Z).
  """
  return help_text


def GetEndTimeHelpText():
  """Gets the --end-time help text."""
  help_text = """\
  End time of the Future Reservation. The end time must be an RFC3339 valid
  string formatted by date, time, and timezone or "YYYY-MM-DDTHH:MM:SSZ"; where
  YYYY = year, MM = month, DD = day, HH = hours, MM = minutes, SS = seconds, and
  Z = timezone (i.e. 2021-11-20T07:00:00Z).
  """
  return help_text


def GetDurationHelpText():
  """Gets the --duration help text."""
  help_text = """\
  Alternate way of specifying time in the number of seconds to terminate
  capacity request relative to the start time of a request.
  """
  return help_text


def GetSharedSettingFlag(custom_name=None):
  """Gets the --share-setting flag."""
  help_text = """\
  Specify if this reservation is shared, and if so, the type of sharing. If you
  omit this flag, this value is local (not shared) by default.
  """
  return base.Argument(
      custom_name if custom_name else '--share-setting',
      choices=['local', 'projects'],
      help=help_text)


def GetShareWithFlag(custom_name=None):
  """Gets the --share-with flag."""
  help_text = """\
  If this reservation is shared (--share-setting is not local), provide a list
  of all of the specific projects that this reservation is shared with. List
  must contain project IDs or project numbers.
  """
  return base.Argument(
      custom_name if custom_name else '--share-with',
      type=arg_parsers.ArgList(min_length=1),
      metavar='PROJECT',
      help=help_text)


def GetPlanningStatusFlag():
  """Gets the --planning-status flag."""
  help_text = """\
  The planning status of the future reservation. The default value is DRAFT.
  While in DRAFT, any changes to the future reservation's properties will be
  allowed. If set to SUBMITTED, the future reservation will submit and its
  procurementStatus will change to PENDING_APPROVAL. Once the future reservation
  is pending approval, changes to the future reservation's properties will not
  be allowed.
  """
  return base.Argument(
      '--planning-status',
      type=lambda x: x.upper(),
      choices={
          'DRAFT':
              'Default planning status value.',
          'SUBMITTED':
              'Planning status value to immediately submit the future reservation.'
      },
      help=help_text)


def AddCreateFlags(
    parser,
    support_location_hint=False,
    support_share_setting=False,
    support_fleet=False,
    support_instance_template=False,
    support_planning_status=False,
):
  """Adds all flags needed for the create command."""
  GetNamePrefixFlag().AddToParser(parser)
  GetTotalCountFlag().AddToParser(parser)
  reservation_flags.GetDescriptionFlag().AddToParser(parser)
  if support_planning_status:
    GetPlanningStatusFlag().AddToParser(parser)

  specific_sku_properties_group = base.ArgumentGroup(
      'Manage the instance properties for the Specific SKU reservation. You must either provide a source instance template or define the instance properties.',
      required=True,
      mutex=True)

  if support_instance_template:
    specific_sku_properties_group.AddArgument(
        reservation_flags.GetSourceInstanceTemplateFlag())

  AddTimeWindowFlags(parser, time_window_requird=True)

  instance_properties_group = base.ArgumentGroup(
      'Define individual instance properties for the specific SKU reservation.')
  instance_properties_group.AddArgument(
      reservation_flags.GetMachineType())
  instance_properties_group.AddArgument(reservation_flags.GetMinCpuPlatform())
  instance_properties_group.AddArgument(reservation_flags.GetLocalSsdFlag())
  instance_properties_group.AddArgument(reservation_flags.GetAcceleratorFlag())
  if support_location_hint:
    instance_properties_group.AddArgument(reservation_flags.GetLocationHint())
  if support_fleet:
    instance_properties_group.AddArgument(
        instance_flags.AddMaintenanceFreezeDuration())
    instance_properties_group.AddArgument(
        instance_flags.AddMaintenanceInterval())

  specific_sku_properties_group.AddArgument(instance_properties_group)
  specific_sku_properties_group.AddToParser(parser)

  if support_share_setting:
    share_group = base.ArgumentGroup(
        'Manage the properties of a shared reservation.', required=False)
    share_group.AddArgument(GetSharedSettingFlag())
    share_group.AddArgument(GetShareWithFlag())
    share_group.AddToParser(parser)


def AddUpdateFlags(parser,
                   support_location_hint=False,
                   support_fleet=False,
                   support_planning_status=False):
  """Adds all flags needed for the update command."""
  GetTotalCountFlag(required=False).AddToParser(parser)
  if support_planning_status:
    GetPlanningStatusFlag().AddToParser(parser)
  group = base.ArgumentGroup(
      'Manage the specific SKU reservation properties.',
      required=False)
  group.AddArgument(reservation_flags.GetMachineType(required=False))
  group.AddArgument(reservation_flags.GetMinCpuPlatform())
  group.AddArgument(reservation_flags.GetLocalSsdFlag())
  group.AddArgument(reservation_flags.GetAcceleratorFlag())
  if support_location_hint:
    group.AddArgument(reservation_flags.GetLocationHint())
  if support_fleet:
    group.AddArgument(instance_flags.AddMaintenanceInterval())
  group.AddToParser(parser)
  AddTimeWindowFlags(parser, time_window_requird=False)


def AddTimeWindowFlags(parser, time_window_requird=False):
  time_window_group = parser.add_group(
      help='Manage the time specific properties for requesting future capacity',
      required=time_window_requird)
  time_window_group.add_argument(
      '--start-time', required=time_window_requird, help=GetStartTimeHelpText())
  end_time_window_group = time_window_group.add_mutually_exclusive_group(
      required=time_window_requird)
  end_time_window_group.add_argument('--end-time', help=GetEndTimeHelpText())
  end_time_window_group.add_argument(
      '--duration', type=int, help=GetDurationHelpText())
