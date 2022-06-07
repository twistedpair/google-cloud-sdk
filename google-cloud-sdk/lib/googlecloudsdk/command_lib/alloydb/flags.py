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


"""Common flags for some of the AlloyDB commands.

Flags are specified with functions that take in a single argument, the parser,
and add the newly constructed flag to that parser.

Example:

def AddFlagName(parser):
  parser.add_argument(
    '--flag-name',
    ... // Other flag details.
  )
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.calliope import arg_parsers


def AddAvailabilityType(parser):
  """Adds an '--availability-type' flag to the parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--availability-type',
      required=False,
      choices={
          'REGIONAL': 'Provides high availability and is recommended for '
                      'production instances; instance automatically fails over '
                      'to another zone within your selected region.',
      },
      help='Specifies level of availability.')


def AddBackup(parser, positional=True):
  """Adds a positional backup argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    positional: whether or not --backup is positional.
  """
  if positional:
    parser.add_argument(
        'backup',
        type=str,
        help='AlloyDB backup ID')
  else:
    parser.add_argument(
        '--backup',
        required=True,
        type=str,
        help='AlloyDB backup ID')


def AddCluster(parser, positional=True):
  """Adds a positional cluster argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    positional: whether or not --cluster is positional.
  """
  if positional:
    parser.add_argument(
        'cluster',
        type=str,
        help='AlloyDB cluster ID')
  else:
    parser.add_argument(
        '--cluster',
        required=True,
        type=str,
        help='AlloyDB cluster ID')


def AddDatabaseFlags(parser, update=False):
  """Adds a `--database-flags` flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    update: Whether or not database flags were provided as part of an update.
  """
  help_ = ('Comma-separated list of database flags to set on the '
           'instance. Use an equals sign to separate flag name and value. '
           'Flags without values, like skip_grant_tables, can be written '
           'out without a value after, e.g., `skip_grant_tables=`. Use '
           'on/off for booleans. View the Instance Resource API for allowed '
           'flags. (e.g., `--database-flags max_allowed_packet=55555,'
           'skip_grant_tables=,log_output=1`)')
  if update:
    help_ += (
        '\n\nThe value given for this argument *replaces* the existing list.')
  parser.add_argument(
      '--database-flags',
      type=arg_parsers.ArgDict(min_length=1),
      metavar='FLAG=VALUE',
      required=False,
      help=help_)


def AddInstance(parser):
  """Adds a positional instance argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      'instance',
      type=str,
      help='AlloyDB instance ID')


def AddInstanceType(parser, required=True):
  """Adds an --instance-type flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --instance-type is required.
  """
  parser.add_argument(
      '--instance-type',
      type=str,
      required=required,
      choices={
          'PRIMARY': 'PRIMARY instances support read and write operations.',
          'READ_POOL':
              'READ_POOL instances support read operations only. Each '
              'read pool instance consists of one or more homogeneous '
              'nodes. '
              '  * Read pool of size 1 can only have zonal availability. '
              '  * Read pools with node count of 2 or more can have  '
              '    regional availability (nodes are present in 2 or  '
              '    more zones in a region).'
      },
      help='Specifies instance type.')


def AddOperation(parser):
  """Adds a positional operation argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      'operation',
      type=str,
      help='AlloyDB operation ID')


def AddNetwork(parser):
  """Adds the `--network` flag to the parser."""
  parser.add_argument(
      '--network',
      required=False,
      type=str,
      help=('Network in the current project that the instance will be part '
            'of. To specify using a network with a shared VPC, use the full '
            'URL of the network. For an example host project, \'testproject\', '
            'and shared network, \'testsharednetwork\', this would be of the '
            'form:'
            '`--network`=`projects/testproject/global/networks/'
            'testsharednetwork`'))


def AddReadPoolNodeCount(parser):
  """Adds a --node-count flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--read-pool-node-count',
      required=False,
      type=int,
      help='Read capacity, i.e. number of nodes in a read pool instance.')


def AddRegion(parser, required=True):
  """Adds a --region flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --region is required.
  """
  parser.add_argument(
      '--region',
      required=required,
      type=str,
      help='Regional location (e.g. asia-east1, us-east1). See the full '
            'list of regions at '
            'https://cloud.google.com/sql/docs/instance-locations.')


def AddZone(parser):
  """Adds a --zone flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--zone',
      required=False,
      type=str,
      help=('Primary Compute Engine zone '
            '(e.g. us-central1, us-central1, etc.'))


def AddForce(parser):
  """Adds a --force flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--force',
      required=False,
      action='store_true',
      help=('Default value is false.'
            '\n\nIf flag is specified, deletes instances (if any) within this '
            'cluster, before deleting the cluster.'
            '\n\nIf flag is not specified, cluster delete will fail if there '
            'are instances present in the cluster.'))


def AddCPUCount(parser, required=True):
  """Adds a --cpu-count flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --cpu-count is required.
  """
  parser.add_argument(
      '--cpu-count',
      required=required,
      type=int,
      choices=[4, 8, 16, 32, 64],
      help=(
          'Whole number value indicating how many vCPUs the machine should '
          'contain. Each vCPU count corresponds to a N2 high-mem machine: '
          '(https://cloud.google.com/compute/docs/general-purpose-machines#n2_'
          'machines).'))


def AddPassword(parser):
  """Adds a --password flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--password',
      required=True,
      type=str,
      help=('Initial postgres user password to set up during cluster creation.')
      )


def _GetDayOfWeekArgList(alloydb_messages):
  """Returns an ArgList accepting days of the week."""
  day_of_week_enum = (
      alloydb_messages.WeeklySchedule.DaysOfWeekValueListEntryValuesEnum)
  choices = [day_of_week_enum.lookup_by_number(i) for i in range(1, 8)]
  visible_choices = [c.name for c in choices]
  visible_choices_set = set(visible_choices)
  def _ParseDayOfWeek(value):
    value_upper = value.upper()
    if value_upper not in visible_choices_set:
      raise arg_parsers.ArgumentTypeError(
          '{value} must be one of [{choices}]'.format(
              value=value, choices=', '.join(visible_choices)))
    return day_of_week_enum.lookup_by_name(value_upper)
  return arg_parsers.ArgList(
      element_type=_ParseDayOfWeek,
      choices=choices,
      visible_choices=visible_choices)


def _GetTimeOfDayArgList(alloydb_messages):
  """Returns an ArgList accepting start times of the form `HH:00`."""
  def _ParseTimeOfDay(value):
    m = re.match(r'^(\d?\d):00$', value)
    if m:
      hour = int(m.group(1))
      if hour <= 23 and hour >= 0:
        return alloydb_messages.GoogleTypeTimeOfDay(hours=hour)
    raise arg_parsers.ArgumentTypeError(
        'Failed to parse time of day: {0}, expected format: HH:00.'.format(
            value))
  return arg_parsers.ArgList(element_type=_ParseTimeOfDay)


def AddAutomatedBackupFlags(parser, alloydb_messages, update=False):
  """Adds automated backup flags.

  Args:
    parser: argparse.ArgumentParser: Parser object for command line inputs.
    alloydb_messages: Message module.
    update: If True, adds update specific flags.
  """
  group = parser.add_group(mutex=True, help='Automated backup policy.')

  policy_group = group.add_group(help='Enable automated backup policy.')
  policy_group.add_argument(
      '--automated-backup-days-of-week',
      metavar='DAYS_OF_WEEK',
      required=True,
      type=_GetDayOfWeekArgList(alloydb_messages),
      help=('Comma-separated list of days of the week to perform a backup. '
            'At least one day of the week must be provided. '
            '(e.g., --automated-backup-days-of-week=MONDAY,WEDNESDAY,SUNDAY)'))

  policy_group.add_argument(
      '--automated-backup-start-times',
      metavar='START_TIMES',
      required=True,
      type=_GetTimeOfDayArgList(alloydb_messages),
      help=('Comma-separated list of times during the day to start a backup. '
            'At least one start time must be provided. '
            'The start times are assumed to be in UTC and required to be '
            'an exact hour in the format HH:00. (e.g., '
            '`--automated-backup-start-times=01:00,13:00`)'))

  retention_group = policy_group.add_group(
      mutex=True,
      help=('Retention policy. If no retention policy is provided, '
            'all automated backups will be retained.'))
  retention_group.add_argument(
      '--automated-backup-retention-period',
      metavar='RETENTION_PERIOD',
      type=arg_parsers.Duration(parsed_unit='s'),
      help=('Retention period of the backup relative to creation time.  See '
            '`$ gcloud topic datetimes` for information on duration formats.'))
  retention_group.add_argument(
      '--automated-backup-retention-count',
      metavar='RETENTION_COUNT',
      type=int,
      help=('Number of most recent successful backups retained.'))

  policy_group.add_argument(
      '--automated-backup-window',
      metavar='TIMEOUT_PERIOD',
      type=arg_parsers.Duration(lower_bound='5m', parsed_unit='s'),
      help=('The length of the time window beginning at start time during '
            'which a backup can be taken. If a backup does not succeed within '
            'this time window, it will be canceled and considered failed. '
            'The backup window must be at least 5 minutes long. '
            'There is no upper bound on the window. If not set, '
            'it will default to 1 hour.'))

  if update:
    group.add_argument(
        '--clear-automated-backup',
        action='store_true',
        help=('Clears the automated backup policy on the cluster. '
              'The default automated backup policy will be used.'))

  group.add_argument(
      '--disable-automated-backup',
      action='store_true',
      help='Disables automated backups on the cluster.')
