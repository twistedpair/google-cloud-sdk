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

import argparse
import datetime
import re

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.kms import resource_args as kms_resource_args
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def AddAvailabilityType(parser):
  """Adds an '--availability-type' flag to the parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  choices_arg = {
      'REGIONAL': (
          'Provide high availability instances. Recommended for '
          'production instances; instances automatically fail over '
          'to another zone within your selected region.'
      ),
      'ZONAL': (
          'Provide zonal availability instances. Not '
          'recommended for production instances; instance '
          'does not automatically fail over to another zone.'
      ),
  }

  parser.add_argument(
      '--availability-type',
      required=False,
      choices=choices_arg,
      help='Specifies level of availability.',
  )


def AddBackup(parser):
  """Adds a positional backup argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument('backup', type=str, help='AlloyDB backup ID')


def AddEnforcedRetention(parser):
  """Adds the `--enforced-retention` flag to the parser."""
  parser.add_argument(
      '--enforced-retention',
      action='store_true',
      required=False,
      hidden=True,
      help=(
          'If set, enforces the retention period for this backup. Backups'
          ' with enforced retention cannot be deleted before they are out of'
          ' retention.'
      ),
  )


def AddCluster(parser, positional=True, required=True):
  """Adds a positional cluster argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    positional: whether or not --cluster is positional.
    required: whether or not the argument is required. Only relevant if the
      argument is non-positional.
  """
  if positional:
    parser.add_argument('cluster', type=str, help='AlloyDB cluster ID')
  else:
    parser.add_argument(
        '--cluster', required=required, type=str, help='AlloyDB cluster ID'
    )


def AddPrimaryCluster(parser, required=True):
  """Adds a positional cluster argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --primary-cluster is required.
  """
  parser.add_argument(
      '--primary-cluster',
      required=required,
      type=str,
      help='AlloyDB primary cluster ID',
  )


def AddDatabaseFlags(parser, update=False):
  """Adds a `--database-flags` flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    update: Whether or not database flags were provided as part of an update.
  """
  help_ = (
      'Comma-separated list of database flags to set on the '
      'instance. Use an equals sign to separate flag name and value. '
      'Flags without values, like skip_grant_tables, can be written '
      'out without a value after, e.g., `skip_grant_tables=`. Use '
      'on/off for booleans. View the Instance Resource API for allowed '
      'flags. (e.g., `--database-flags max_allowed_packet=55555,'
      'skip_grant_tables=,log_output=1`)'
  )
  if update:
    help_ += (
        '\n\nThe value given for this argument *replaces* the existing list.'
    )
  parser.add_argument(
      '--database-flags',
      type=arg_parsers.ArgDict(min_length=1),
      metavar='FLAG=VALUE',
      required=False,
      help=help_,
  )


def AddInstance(parser):
  """Adds a positional instance argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument('instance', type=str, help='AlloyDB instance ID')


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
          'READ_POOL': (
              'READ_POOL instances support read operations only. Each '
              'read pool instance consists of one or more homogeneous '
              'nodes. '
              '  * Read pool of size 1 can only have zonal availability. '
              '  * Read pools with node count of 2 or more can have  '
              '    regional availability (nodes are present in 2 or  '
              '    more zones in a region).'
          ),
      },
      help='Specifies instance type.',
  )


def AddFaultType(parser, required=True):
  """Adds a --fault-type flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --fault-type is required.
  """
  parser.add_argument(
      '--fault-type',
      type=str,
      required=required,
      choices={'stop-vm': 'stop-vm fault type supports stopping the VM.'},
      help='Specifies fault type.',
  )


def GetInjectFaultTypeFlagMapper(alloydb_messages):
  return arg_utils.ChoiceEnumMapper(
      '--fault-type',
      alloydb_messages.InjectFaultRequest.FaultTypeValueValuesEnum,
      required=False,
      custom_mappings={
          'STOP_VM': 'stop-vm',
      },
      help_str='Type of fault to inject in an instance.',
  )


def AddOperation(parser):
  """Adds a positional operation argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument('operation', type=str, help='AlloyDB operation ID')


def AddEnableConnectionPooling(parser):
  """Adds --enable-connection-pooling flag.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--enable-connection-pooling',
      required=False,
      help='Enable connection pooling for the instance.',
      action=arg_parsers.StoreTrueFalseAction,
  )


def AddConnectionPoolingPoolMode(parser):
  """Adds --connection-pooling-pool-mode flag.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--connection-pooling-pool-mode',
      choices={
          'SESSION': 'Session mode for managed connection pooling.',
          'TRANSACTION': 'Transaction mode for managed connection pooling.',
      },
      required=False,
      default=None,
      help='The pool mode for managed connection pooling.',
  )


def AddConnectionPoolingMinPoolSize(parser):
  """Adds --connection-pooling-min-pool-size flag.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--connection-pooling-min-pool-size',
      type=str,
      required=False,
      default=None,
      help='The min pool size for managed connection pooling.',
  )


def AddConnectionPoolingMaxPoolSize(parser):
  """Adds --connection-pooling-max-pool-size flag.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--connection-pooling-max-pool-size',
      type=str,
      required=False,
      default=None,
      help='The max pool size for managed connection pooling.',
  )


def AddConnectionPoolingMaxClientConnections(parser):
  """Adds --connection-pooling-max-client-connections flag.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--connection-pooling-max-client-connections',
      type=str,
      required=False,
      default=None,
      help='The max client connections for managed connection pooling.',
  )


def AddConnectionPoolingServerIdleTimeout(parser):
  """Adds --connection-pooling-server-idle-timeout flag.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--connection-pooling-server-idle-timeout',
      type=str,
      required=False,
      default=None,
      help='The server idle timeout for managed connection pooling.',
  )


def AddConnectionPoolingQueryWaitTimeout(parser):
  """Adds --connection-pooling-query-wait-timeout flag.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--connection-pooling-query-wait-timeout',
      type=str,
      required=False,
      default=None,
      help='The query wait timeout for managed connection pooling.',
  )


def AddConnectionPoolingStatsUsers(parser):
  """Adds --connection-pooling-stats-users flag.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--connection-pooling-stats-users',
      required=False,
      type=arg_parsers.ArgList(),
      metavar='STATS_USERS',
      help=(
          'Comma-separated list of database users to access connection pooling'
          ' stats.'
      ),
  )


def AddConnectionPoolingIgnoreStartupParameters(parser):
  """Adds --connection-pooling-ignore-startup-parameters flag.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--connection-pooling-ignore-startup-parameters',
      required=False,
      type=arg_parsers.ArgList(),
      metavar='STARTUP_PARAMETERS',
      help=(
          'Comma-separated list of startup parameters that should be ignored by'
          ' the connection pool.'
      ),
  )


def AddEnablePrivateServiceConnect(parser):
  """Adds the `--enable-private-service-connect` flag to the parser."""
  parser.add_argument(
      '--enable-private-service-connect',
      required=False,
      action='store_true',
      help='Enable Private Service Connect (PSC) connectivity for the cluster.',
  )


def AddAllowedPSCProjects(parser):
  """Adds the `--allowed-psc-projects` flag to the parser."""
  parser.add_argument(
      '--allowed-psc-projects',
      required=False,
      type=arg_parsers.ArgList(),
      metavar='ALLOWED_PSC_PROJECTS',
      help=(
          'Comma-separated list of allowed consumer projects to create'
          ' endpoints for Private Service Connect (PSC) connectivity for the'
          ' instance. Only instances in PSC-enabled clusters are allowed to set'
          ' this field.(e.g.,'
          ' `--allowed-psc-projects=project1,12345678,project2)'
      ),
  )


def AddPSCNetworkAttachmentUri(parser):
  """Adds the `--psc-network-attachment-uri` flag to the parser."""
  parser.add_argument(
      '--psc-network-attachment-uri',
      required=False,
      type=str,
      help=(
          'Full URI of the network attachment that is configured to '
          'support outbound connectivity from an AlloyDB instance which '
          'uses Private Service Connect (PSC). '
          'For example, this would be of the form:'
          '`psc-network-attachment-uri=projects/test-project/regions/us-central1/networkAttachments/my-na`'
      ),
  )


def ClearPSCNetworkAttachmentUri(parser):
  parser.add_argument(
      '--clear-psc-network-attachment-uri',
      action='store_true',
      help="""Disable outbound connectivity from an AlloyDB instance which uses Private Service Connect (PSC).""",
  )


def AddPSCAutoConnections(parser):
  """Adds the `--psc-auto-connections` flag to the parser."""
  parser.add_argument(
      '--psc-auto-connections',
      required=False,
      type=arg_parsers.ArgObject(
          spec={
              'project': str,
              'network': str,
          },
          required_keys=['project', 'network'],
      ),
      action=arg_parsers.FlattenAction(),
      help=(
          'Comma-separated list of consumer project and consumer network pairs'
          ' to create endpoints for Private Service Connect (PSC) connectivity'
          ' for the instance. Only instances in PSC-enabled clusters are'
          ' allowed to set this field. Both project and network must be'
          ' specified. (e.g.,'
          ' `--psc-auto-connections=project=project1,network=projects/vpc-host-project1/global/networks/network1`'
          ' `--psc-auto-connections=project=project2,network=projects/vpc-host-project2/global/networks/network2`)'
      ),
  )


def ClearPSCAutoConnections(parser):
  """Adds the `--clear-psc-auto-connections` flag to the parser."""
  parser.add_argument(
      '--clear-psc-auto-connections',
      action='store_true',
      help="""Remove all PSC auto connections for an AlloyDB instance.""",
  )


def AddPSCAutoConnectionGroup(parser):
  """Adds PSC auto connection flags to the parser."""
  psc_auto_connection_group = parser.add_group(
      mutex=True,
      required=False,
      help='PSC auto connection options for an AlloyDB instance.',
  )

  AddPSCAutoConnections(psc_auto_connection_group)
  ClearPSCAutoConnections(psc_auto_connection_group)


def AddNetwork(parser):
  """Adds the `--network` flag to the parser."""
  parser.add_argument(
      '--network',
      required=False,
      type=str,
      help=(
          'Network in the current project that the instance will be part '
          'of. To specify using a network with a shared VPC, use the full '
          'URL of the network. For an example host project, `testproject`, '
          'and shared network, `testsharednetwork`, this would be of the '
          'form:'
          '`--network=projects/testproject/global/networks/'
          'testsharednetwork`'
      ),
  )


def AddAllocatedIPRangeName(parser):
  """Adds the `--allocated-ip-range-name` flag to the parser."""
  parser.add_argument(
      '--allocated-ip-range-name',
      required=False,
      type=str,
      help=(
          'Name of the allocated IP range for the private IP AlloyDB '
          'cluster, for example: "google-managed-services-default". If set, '
          'the instance IPs for this cluster will be created in the '
          'allocated range. The range name must comply with RFC 1035. '
          'Specifically, the name must be 1-63 characters long and match the '
          'regular expression [a-z]([-a-z0-9]*[a-z0-9])?.'
      ),
  )


def AddReadPoolNodeCount(parser):
  """Adds a --node-count flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--read-pool-node-count',
      required=False,
      type=int,
      help='Read capacity, i.e. number of nodes in a read pool instance.',
  )


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
      help=(
          'Regional location (e.g. `asia-east1`, `us-east1`). See the full '
          'list of regions at '
          'https://cloud.google.com/sql/docs/instance-locations.'
      ),
  )


def AddZone(parser):
  """Adds a --zone flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--zone',
      required=False,
      type=str,
      help=(
          'Primary Compute Engine zone (e.g. `us-central1-a`, `us-central1-b`,'
          ' etc.'
      ),
  )


def AddForce(parser):
  """Adds a --force flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--force',
      required=False,
      action='store_true',
      help=(
          'Default value is false.'
          '\n\nIf flag is specified, deletes instances (if any) within this '
          'cluster, before deleting the cluster.'
          '\n\nIf flag is not specified, cluster delete will fail if there '
          'are instances present in the cluster.'
      ),
  )


def AddCPUCount(parser, required):
  """Adds a --cpu-count flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --cpu-count is required.
  """
  parser.add_argument(
      '--cpu-count',
      required=required,
      type=int,
      choices=[1, 2, 4, 8, 16, 32, 48, 64, 72, 96, 128],
      help=(
          'Whole number value indicating how many vCPUs the machine should'
          ' contain. If the instance does not have a machine-type, the vCPU'
          ' count will be used to determine the machine type where each vCPU'
          ' corresponds to an N2  high-mem machine: '
          ' (https://cloud.google.com/compute/docs/general-purpose-machines#n2_machine_types).'
          ' where CPU_COUNT can be one of: 2, 4, 8, 16, 32, 64, 96, 128. If the'
          ' instance has a machine-type, cpu-count must have the same value as'
          ' the vCPU count in the machine-type. Eg: if machine-type is'
          ' c4a-highmem-4-lssd, cpu-count must be 4.'
      ),
  )


def AddActivationPolicy(parser, alloydb_messages, required=False):
  """Adds a --activation-policy flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --activation-policy is required.
  """
  parser.add_argument(
      '--activation-policy',
      required=required,
      choices=[
          alloydb_messages.Instance.ActivationPolicyValueValuesEnum.ALWAYS,
          alloydb_messages.Instance.ActivationPolicyValueValuesEnum.NEVER
      ],
      type=alloydb_messages.Instance.ActivationPolicyValueValuesEnum,
      help=(
          'Activation Policy for the instance. '
          'Required to START or STOP an instance. '
          'ALWAYS - The instance is up and running. '
          'NEVER - The instance is stopped.'
      ),
  )


def AddMachineType(parser, required=False):
  """Adds a --machine-type flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --machine-type is required.
  """
  parser.add_argument(
      '--machine-type',
      required=required,
      type=str,
      choices=[
          'n2-highmem-2',
          'n2-highmem-4',
          'n2-highmem-8',
          'n2-highmem-16',
          'n2-highmem-32',
          'n2-highmem-64',
          'n2-highmem-96',
          'n2-highmem-128',
          'c4a-highmem-1',
          'c4a-highmem-4-lssd',
          'c4a-highmem-8-lssd',
          'c4a-highmem-16-lssd',
          'c4a-highmem-32-lssd',
          'c4a-highmem-48-lssd',
          'c4a-highmem-64-lssd',
          'c4a-highmem-72-lssd',
      ],
      help='Specifies machine type for the instance.',
  )


def AddDBRoles(parser, required=False):
  """Adds a --db-roles flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --db-roles is required.
  """
  parser.add_argument(
      '--db-roles',
      required=required,
      type=arg_parsers.ArgList(),
      metavar='ROLE',
      help=(
          'Comma separated list of database roles this new user will be granted'
          ' upon creation.'
      ),
  )


def AddUserType(parser):
  """Adds a --type flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--type',
      type=str,
      choices={
          'BUILT_IN': (
              'This database user can authenticate via password-based'
              ' authentication'
          ),
          'IAM_BASED': (
              'This database user can authenticate via IAM-based authentication'
          ),
          # 'ALLOYDB_IAM_GROUP': Not implemented until IAM auth phase 2.,
      },
      default='BUILT_IN',
      help='Type corresponds to the user type.',
  )


def AddKeepExtraRoles(parser):
  """Adds a --keep-extra-roles flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--keep-extra-roles',
      type=arg_parsers.ArgBoolean(),
      default=False,
      help='If the user already exists and has extra roles, keep them.',
  )


def AddCreateSuperuser(parser):
  """Adds a --superuser flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--superuser',
      type=arg_parsers.ArgBoolean(),
      default=False,
      help=(
          'If true, new user will have AlloyDB superuser privileges. Default'
          ' value is false.'
      ),
  )


def AddSetSuperuser(parser):
  """Adds a --superuser flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--superuser',
      type=arg_parsers.ArgBoolean(),
      default=False,
      required=True,
      help='If true, user will have AlloyDB superuser privileges',
  )


def AddUsername(parser):
  """Adds a positional username argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument('username', type=str, help='AlloyDB username')


def AddPassword(parser):
  """Adds a --password flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--password',
      required=True,
      type=str,
      help='Initial postgres user password to set up during cluster creation.',
  )


def AddUserPassword(parser, required=False):
  """Adds a --password flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --password is required.
  """
  parser.add_argument(
      '--password',
      required=required,
      type=str,
      help='Password for this database user.',
  )


def _GetDayOfWeekArgList(alloydb_messages):
  """Returns an ArgList accepting days of the week."""
  day_of_week_enum = (
      alloydb_messages.WeeklySchedule.DaysOfWeekValueListEntryValuesEnum
  )
  choices = [day_of_week_enum.lookup_by_number(i) for i in range(1, 8)]
  visible_choices = [c.name for c in choices]
  visible_choices_set = set(visible_choices)

  def _ParseDayOfWeek(value):
    value_upper = value.upper()
    if value_upper not in visible_choices_set:
      raise arg_parsers.ArgumentTypeError(
          '{value} must be one of [{choices}]'.format(
              value=value, choices=', '.join(visible_choices)
          )
      )
    return day_of_week_enum.lookup_by_name(value_upper)

  return arg_parsers.ArgList(
      element_type=_ParseDayOfWeek,
      choices=choices,
      visible_choices=visible_choices,
  )


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
            value
        )
    )

  return arg_parsers.ArgList(element_type=_ParseTimeOfDay)


def AddAutomatedBackupFlags(
    parser, alloydb_messages, release_track, update=False
):
  """Adds automated backup flags.

  Args:
    parser: argparse.ArgumentParser: Parser object for command line inputs.
    alloydb_messages: Message module.
    release_track: The command version being used - GA/BETA/ALPHA.
    update: If True, adds update specific flags.
  """
  automated_backup_help = 'Automated backup policy.'
  if not update:
    automated_backup_help += ' If unspecified, automated backups are disabled.'
  group = parser.add_group(mutex=True, help=automated_backup_help)

  policy_group = group.add_group(help='Enable automated backup policy.')
  policy_group.add_argument(
      '--automated-backup-days-of-week',
      metavar='DAYS_OF_WEEK',
      required=not update,  # required for create, not for update
      type=_GetDayOfWeekArgList(alloydb_messages),
      help=(
          'Comma-separated list of days of the week to perform a backup. '
          'At least one day of the week must be provided. '
          '(e.g., --automated-backup-days-of-week=MONDAY,WEDNESDAY,SUNDAY)'
      ),
  )

  policy_group.add_argument(
      '--automated-backup-start-times',
      metavar='START_TIMES',
      required=not update,  # required for create, not for update
      type=_GetTimeOfDayArgList(alloydb_messages),
      help=(
          'Comma-separated list of times during the day to start a backup. '
          'At least one start time must be provided. '
          'The start times are assumed to be in UTC and required to be '
          'an exact hour in the format HH:00. (e.g., '
          '`--automated-backup-start-times=01:00,13:00`)'
      ),
  )

  retention_group = policy_group.add_group(
      mutex=True,
      help=(
          'Retention policy. If no retention policy is provided, '
          'all automated backups will be retained.'
      ),
  )
  retention_group.add_argument(
      '--automated-backup-retention-period',
      metavar='RETENTION_PERIOD',
      type=arg_parsers.Duration(parsed_unit='s'),
      help=(
          'Retention period of the backup relative to creation time.  See '
          '`$ gcloud topic datetimes` for information on duration formats.'
      ),
  )
  retention_group.add_argument(
      '--automated-backup-retention-count',
      metavar='RETENTION_COUNT',
      type=int,
      help='Number of most recent successful backups retained.',
  )

  policy_group.add_argument(
      '--automated-backup-window',
      metavar='TIMEOUT_PERIOD',
      type=arg_parsers.Duration(lower_bound='5m', parsed_unit='s'),
      help=(
          'Length of the time window beginning at start time during '
          'which a backup can be taken. If a backup does not succeed within '
          'this time window, it will be canceled and considered failed. '
          'The backup window must be at least 5 minutes long. '
          'There is no upper bound on the window. If not set, '
          'it will default to 1 hour.'
      ),
  )
  if (
      release_track == base.ReleaseTrack.ALPHA
      or release_track == base.ReleaseTrack.BETA
  ):
    policy_group.add_argument(
        '--automated-backup-enforced-retention',
        action='store_true',
        default=None,
        required=False,
        hidden=True,
        help=(
            'If set, enforces the retention period for automated backups.'
            ' Backups created by this policy cannot be deleted before they are'
            ' out of retention.'
        ),
    )

  kms_resource_args.AddKmsKeyResourceArg(
      policy_group,
      'automated backups',
      flag_overrides=GetAutomatedBackupKmsFlagOverrides(),
      permission_info=(
          "The 'AlloyDB Service Agent' service account must hold permission"
          " 'Cloud KMS CryptoKey Encrypter/Decrypter'"
      ),
      name='--automated-backup-encryption-key',
  )

  if update:
    group.add_argument(
        '--clear-automated-backup',
        action='store_true',
        help=(
            'Clears the automated backup policy on the cluster. '
            'The default automated backup policy will be used.'
        ),
    )

  group.add_argument(
      '--disable-automated-backup',
      action='store_true',
      help='Disables automated backups on the cluster.',
  )


def AddAutomatedBackupFlagsForCreateSecondary(parser, alloydb_messages):
  """Adds automated backup flags.

  Args:
    parser: argparse.ArgumentParser: Parser object for command line inputs.
    alloydb_messages: Message module.
  """
  group = parser.add_group(
      mutex=False,
      help=(
          'Automated backup policy. If unspecified, automated backups are'
          ' copied from the associated primary cluster.'
      ),
  )

  group.add_argument(
      '--enable-automated-backup',
      action='store_true',
      default=None,
      help='Enables Automated Backups on the cluster.',
  )

  group.add_argument(
      '--automated-backup-days-of-week',
      metavar='DAYS_OF_WEEK',
      # required=True,
      type=_GetDayOfWeekArgList(alloydb_messages),
      help=(
          'Comma-separated list of days of the week to perform a backup. '
          'At least one day of the week must be provided. '
          '(e.g., --automated-backup-days-of-week=MONDAY,WEDNESDAY,SUNDAY)'
      ),
  )

  group.add_argument(
      '--automated-backup-start-times',
      metavar='START_TIMES',
      # required=True,
      type=_GetTimeOfDayArgList(alloydb_messages),
      help=(
          'Comma-separated list of times during the day to start a backup. '
          'At least one start time must be provided. '
          'The start times are assumed to be in UTC and required to be '
          'an exact hour in the format HH:00. (e.g., '
          '`--automated-backup-start-times=01:00,13:00`)'
      ),
  )

  retention_group = group.add_group(
      mutex=True,
      help=(
          'Retention policy. If no retention policy is provided, '
          'all automated backups will be retained.'
      ),
  )
  retention_group.add_argument(
      '--automated-backup-retention-period',
      metavar='RETENTION_PERIOD',
      type=arg_parsers.Duration(parsed_unit='s'),
      help=(
          'Retention period of the backup relative to creation time.  See '
          '`$ gcloud topic datetimes` for information on duration formats.'
      ),
  )
  retention_group.add_argument(
      '--automated-backup-retention-count',
      metavar='RETENTION_COUNT',
      type=int,
      help='Number of most recent successful backups retained.',
  )

  group.add_argument(
      '--automated-backup-window',
      metavar='TIMEOUT_PERIOD',
      type=arg_parsers.Duration(lower_bound='5m', parsed_unit='s'),
      help=(
          'The length of the time window beginning at start time during '
          'which a backup can be taken. If a backup does not succeed within '
          'this time window, it will be canceled and considered failed. '
          'The backup window must be at least 5 minutes long. '
          'There is no upper bound on the window. If not set, '
          'it will default to 1 hour.'
      ),
  )

  kms_resource_args.AddKmsKeyResourceArg(
      group,
      'automated backups',
      flag_overrides=GetAutomatedBackupKmsFlagOverrides(),
      permission_info=(
          "The 'AlloyDB Service Agent' service account must hold permission"
          " 'Cloud KMS CryptoKey Encrypter/Decrypter'"
      ),
      name='--automated-backup-encryption-key',
  )


def AddEncryptionConfigFlags(parser, verb):
  """Add a resource argument for a KMS Key used to create a CMEK encrypted resource.

  Args:
    parser: argparser, the parser for the command.
    verb: str, the verb used to describe the resource, such as 'to create'.
  """
  concept_parsers.ConceptParser.ForResource(
      '--kms-key',
      GetKmsKeyResourceSpec(),
      'Cloud KMS key to be used {}.'.format(verb),
      required=False,
  ).AddToParser(parser)


def AddRestoreClusterSourceFlags(parser, release_track):
  """Adds RestoreCluster flags.

  Args:
    parser: argparse.ArgumentParser: Parser object for command line inputs.
    release_track: The command version being used - GA/BETA/ALPHA.
  """
  group = parser.add_group(
      mutex=True, required=True, help='RestoreCluster source types.'
  )
  group.add_argument(
      '--backup',
      type=str,
      help=(
          'AlloyDB backup to restore from. This must either be the full'
          ' backup name'
          ' (projects/myProject/locations/us-central1/backups/myBackup) or the'
          ' backup ID (myBackup). In the second case, the project and location'
          ' are assumed to be the same as the restored cluster that is being'
          ' created.'
      ),
  )
  if (
      release_track == base.ReleaseTrack.ALPHA
      or release_track == base.ReleaseTrack.BETA
  ):
    group.add_argument(
        '--backupdr-backup',
        type=str,
        help=(
            'Backup DR backup to restore from. This is a resource path of the'
            ' form'
            ' projects/myProject/locations/us-central1/backupVaults/myBackupVault/dataSources/myDataSource/backups/myBackup.'
        ),
        # TODO(b/400420101): Remove hidden flag once the feature is ready.
        hidden=True,
    )

  continuous_backup_source_group = group.add_group(
      help='Restore a cluster from a source cluster at a given point in time.'
  )
  continuous_backup_source_group.add_argument(
      '--source-cluster',
      required=True,
      help=(
          'AlloyDB source cluster to restore from. This must either be the'
          ' full cluster name'
          ' (projects/myProject/locations/us-central1/backups/myCluster) or the'
          ' cluster ID (myCluster). In the second case, the project and'
          ' location are assumed to be the same as the restored cluster that is'
          ' being created.'
      ),
  )
  continuous_backup_source_group.add_argument(
      '--point-in-time',
      type=arg_parsers.Datetime.Parse,
      required=True,
      help=(
          'Point in time to restore to, in RFC 3339 format. For example, '
          '2012-11-15T16:19:00.094Z.'
      ),
  )


def AddContinuousBackupConfigFlags(parser, release_track, update=False):
  """Adds Continuous backup configuration flags.

  Args:
    parser: argparse.ArgumentParser: Parser object for command line inputs.
    release_track: The command version being used - GA/BETA/ALPHA.
    update: Whether database flags were provided as part of an update.
  """
  continuous_backup_help = 'Continuous Backup configuration.'
  if not update:
    continuous_backup_help += ' If unspecified, continuous backups are enabled.'
  group = parser.add_group(mutex=False, help=continuous_backup_help)

  group.add_argument(
      '--enable-continuous-backup',
      action='store_true',
      default=None,
      help='Enables Continuous Backups on the cluster.',
  )
  group.add_argument(
      '--continuous-backup-recovery-window-days',
      metavar='RECOVERY_PERIOD',
      type=int,
      help=(
          'Recovery window of the log files and backups saved to support '
          'Continuous Backups.'
      ),
  )
  if (
      release_track == base.ReleaseTrack.ALPHA
      or release_track == base.ReleaseTrack.BETA
  ):
    group.add_argument(
        '--continuous-backup-enforced-retention',
        action='store_true',
        default=None,
        required=False,
        hidden=True,
        help=(
            'If set, enforces the retention period for continuous backups.'
            ' Backups created by this configuration cannot be deleted before'
            ' they are out of retention.'
        ),
    )

  cmek_group = group
  if update:
    cmek_group = group.add_group(
        mutex=True, help='Encryption configuration for Continuous Backups.'
    )
    cmek_group.add_argument(
        '--clear-continuous-backup-encryption-key',
        action='store_true',
        help=(
            'Clears the encryption configuration for Continuous Backups.'
            ' Google default encryption will be used for future'
            ' Continuous Backups.'
        ),
    )
  kms_resource_args.AddKmsKeyResourceArg(
      cmek_group,
      'continuous backup',
      flag_overrides=GetContinuousBackupKmsFlagOverrides(),
      permission_info=(
          "The 'AlloyDB Service Agent's service account must hold permission"
          " 'Cloud KMS CryptoKey Encrypter/Decrypter'"
      ),
      name='--continuous-backup-encryption-key',
  )


def AddContinuousBackupConfigFlagsForCreateSecondary(parser):
  """Adds Continuous backup configuration flags.

  Args:
    parser: argparse.ArgumentParser: Parser object for command line inputs.
  """
  group = parser.add_group(
      mutex=False,
      help=(
          'Continuous Backup configuration. If unspecified, continuous backups'
          ' are copied from the associated primary cluster.'
      ),
  )

  group.add_argument(
      '--enable-continuous-backup',
      action='store_true',
      default=None,
      help='Enables Continuous Backups on the cluster.',
  )
  group.add_argument(
      '--continuous-backup-recovery-window-days',
      metavar='RECOVERY_PERIOD',
      type=int,
      help=(
          'Recovery window of the log files and backups saved to support '
          'Continuous Backups.'
      ),
  )

  kms_resource_args.AddKmsKeyResourceArg(
      group,
      'continuous backup',
      flag_overrides=GetContinuousBackupKmsFlagOverrides(),
      permission_info=(
          "The 'AlloyDB Service Agent's service account must hold permission"
          " 'Cloud KMS CryptoKey Encrypter/Decrypter'"
      ),
      name='--continuous-backup-encryption-key',
  )


def AddInsightsConfigQueryStringLength(parser):
  parser.add_argument(
      '--insights-config-query-string-length',
      required=False,
      type=arg_parsers.BoundedInt(lower_bound=256, upper_bound=4500),
      help="""Query string length in bytes to be stored by the query insights
        feature. Default length is 1024 bytes. Allowed range: 256 to 4500
        bytes.""",
  )


def AddInsightsConfigQueryPlansPerMinute(parser):
  parser.add_argument(
      '--insights-config-query-plans-per-minute',
      required=False,
      type=arg_parsers.BoundedInt(lower_bound=0, upper_bound=20),
      help="""Number of query plans to sample every minute.
        Default value is 5. Allowed range: 0 to 20.""",
  )


def _GetKwargsForBoolFlag(show_negated_in_help):
  if show_negated_in_help:
    return {
        'action': arg_parsers.StoreTrueFalseAction,
    }
  else:
    return {'action': 'store_true', 'default': None}


def AddInsightsConfigRecordApplicationTags(parser, show_negated_in_help):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--insights-config-record-application-tags',
      required=False,
      help="""Allow application tags to be recorded by the query insights
        feature.""",
      **kwargs,
  )


def AddOutboundPublicIp(parser, show_negated_in_help):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--outbound-public-ip',
      required=False,
      help="""Add outbound Public IP connectivity to an AlloyDB instance.""",
      **kwargs,
  )


def AddInsightsConfigRecordClientAddress(parser, show_negated_in_help):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--insights-config-record-client-address',
      required=False,
      help="""Allow the client address to be recorded by the query insights
        feature.""",
      **kwargs,
  )


def AddObservabilityConfigEnabled(parser, show_negated_in_help):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--observability-config-enabled',
      required=False,
      help="""Enable enhanced query insights feature.""",
      **kwargs,
  )


def AddObservabilityConfigPreserveComments(parser, show_negated_in_help):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--observability-config-preserve-comments',
      required=False,
      help="""Allow preservation of comments in query string recorded by the
        enhanced query insights feature.""",
      **kwargs,
  )


def AddObservabilityConfigTrackWaitEvents(parser, show_negated_in_help):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--observability-config-track-wait-events',
      required=False,
      help="""Track wait events during query execution.""",
      **kwargs,
  )


def AddObservabilityConfigMaxQueryStringLength(parser):
  parser.add_argument(
      '--observability-config-max-query-string-length',
      required=False,
      type=arg_parsers.BoundedInt(lower_bound=1024, upper_bound=100000),
      help="""Query string length in bytes to be stored by the enhanced query
        insights feature. Default length is 10k bytes.""",
  )


def AddObservabilityConfigRecordApplicationTags(parser, show_negated_in_help):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--observability-config-record-application-tags',
      required=False,
      help="""Allow application tags to be recorded by the enhanced query
        insights feature.""",
      **kwargs,
  )


def AddObservabilityConfigQueryPlansPerMinute(parser):
  parser.add_argument(
      '--observability-config-query-plans-per-minute',
      required=False,
      type=arg_parsers.BoundedInt(lower_bound=0, upper_bound=20),
      help="""Number of query plans to sample every minute.
        Default value is 200. Allowed range: 0 to 200.""",
  )


def AddObservabilityConfigTrackActiveQueries(parser, show_negated_in_help):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--observability-config-track-active-queries',
      required=False,
      help="""Track actively running queries.""",
      **kwargs,
  )


def KmsKeyAttributeConfig():
  # For anchor attribute, help text is generated automatically.
  return concepts.ResourceParameterAttributeConfig(name='kms-key')


def KmsKeyringAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='kms-keyring', help_text='KMS keyring id of the {resource}.'
  )


def KmsLocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='kms-location', help_text='Cloud location for the {resource}.'
  )


def KmsProjectAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='kms-project', help_text='Cloud project id for the {resource}.'
  )


def GetKmsKeyResourceSpec():
  return concepts.ResourceSpec(
      'cloudkms.projects.locations.keyRings.cryptoKeys',
      resource_name='key',
      cryptoKeysId=KmsKeyAttributeConfig(),
      keyRingsId=KmsKeyringAttributeConfig(),
      locationsId=KmsLocationAttributeConfig(),
      projectsId=KmsProjectAttributeConfig(),
  )


def GetAndValidateKmsKeyName(args, flag_overrides=None):
  """Parse the KMS key resource arg, make sure the key format is correct."""
  kms_flags = {
      'kms-key': '--kms-key',
      'kms-keyring': '--kms-keyring',
      'kms-location': '--kms-location',
      'kms-project': '--kms-project',
  }
  kms_flags = flag_overrides if flag_overrides else kms_flags

  kms_ref = getattr(
      args.CONCEPTS, kms_flags['kms-key'][2:].replace('-', '_')
  ).Parse()
  if kms_ref:
    return kms_ref.RelativeName()
  else:
    # If parsing failed but args were specified, raise error
    for keyword in kms_flags.values():
      if getattr(args, keyword[2:].replace('-', '_'), None):
        parameter_name = '{} {} {} {}'.format(
            kms_flags['kms-project'],
            kms_flags['kms-location'],
            kms_flags['kms-keyring'],
            kms_flags['kms-key'],
        )
        message = (
            'Specify fully qualified KMS key ID with {}, or use '
            'combination of {}, {}, {} and {} to specify the key ID in '
            'pieces.'
        )
        message = message.format(
            kms_flags['kms-key'],
            kms_flags['kms-project'],
            kms_flags['kms-location'],
            kms_flags['kms-keyring'],
            kms_flags['kms-key'],
        )
        raise exceptions.InvalidArgumentException(parameter_name, message)
    return None  # User didn't specify KMS key


# LINT.IfChange(validate_continuous_backup_flags)
def ValidateContinuousBackupFlags(args, update=False):
  """Validate the arguments for continuous backup, ensure the correct set of flags are passed."""
  # args.continuous_backup_enforced_retention is not validated here since it's
  # only available in alpha/beta for now, once it's rolled out in GA we should
  # validate it.
  if (
      args.enable_continuous_backup is False  # pylint: disable=g-bool-id-comparison
      and (
          args.continuous_backup_recovery_window_days
          or args.continuous_backup_encryption_key
          or (update and args.clear_continuous_backup_encryption_key)
      )
  ):
    raise exceptions.ConflictingArgumentsException(
        '--no-enable-continuous-backup',
        '--continuous-backup-recovery-window-days',
        '--continuous-backup-encryption-key',
        '--clear-continuous-backup-encryption-key',
    )


# LINT.ThenChange()


# LINT.IfChange(validate_automated_backup_flags_for_secondary)
def ValidateAutomatedBackupFlagsForCreateSecondary(args):
  """Validate the arguments for automated backup for secondary clusters, ensure the correct set of flags are passed."""
  if (
      args.enable_automated_backup is False  # pylint: disable=g-bool-id-comparison
      and (
          args.automated_backup_recovery_window_days
          or args.automated_backup_encryption_key
          or args.automated_backup_start_times
      )
  ):
    raise exceptions.ConflictingArgumentsException(
        '--no-enable-automated-backup',
        '--automated-backup-start-times',
        '--automated-backup-days-of-week',
        '--automated-backup-window',
    )


# LINT.ThenChange()


def ValidateConnectivityFlags(args):
  """Validate the arguments for connectivity, ensure the correct set of flags are passed."""
  # TODO(b/310733501) Move this to create.yaml or update.yaml files.
  if args.enable_private_service_connect and args.network:
    raise exceptions.ConflictingArgumentsException(
        '--enable-private-service-connect',
        '--network',
    )
  if args.enable_private_service_connect and args.allocated_ip_range_name:
    raise exceptions.ConflictingArgumentsException(
        '--enable-private-service-connect',
        '--allocated-ip-range-name',
    )


def GetAutomatedBackupKmsFlagOverrides():
  return {
      'kms-key': '--automated-backup-encryption-key',
      'kms-keyring': '--automated-backup-encryption-key-keyring',
      'kms-location': '--automated-backup-encryption-key-location',
      'kms-project': '--automated-backup-encryption-key-project',
  }


def GetContinuousBackupKmsFlagOverrides():
  return {
      'kms-key': '--continuous-backup-encryption-key',
      'kms-keyring': '--continuous-backup-encryption-key-keyring',
      'kms-location': '--continuous-backup-encryption-key-location',
      'kms-project': '--continuous-backup-encryption-key-project',
  }


def GetInstanceViewFlagMapper(alloydb_messages):
  return arg_utils.ChoiceEnumMapper(
      '--view',
      alloydb_messages.AlloydbProjectsLocationsClustersInstancesGetRequest.ViewValueValuesEnum,
      required=False,
      custom_mappings={
          'INSTANCE_VIEW_BASIC': 'basic',
          'INSTANCE_VIEW_FULL': 'full',
      },
      help_str='View of the instance to return.',
  )


def AddView(parser, alloydb_messages):
  """Adds a view flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    alloydb_messages: Message module.
  """
  GetInstanceViewFlagMapper(alloydb_messages).choice_arg.AddToParser(parser)


def AddUpdateMode(parser):
  """Adds an '--update-mode' flag to the parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--update-mode',
      required=False,
      choices={
          'FORCE_APPLY': (
              'Performs a forced update when applicable. '
              'This will be fast but may incur a downtime.'
          ),
      },
      help=(
          'Specify the mode for updating the instance. If unspecified, '
          'the update would follow a least disruptive approach'
      ),
  )


def AddSSLMode(parser, default_from_primary=False, update=False):
  """Adds SSL Mode flag.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    default_from_primary: If true, we get the default SSL mode from the primary.
      This is always true for secondary instances.
    update: If True, does not set the default SSL mode.
  """
  ssl_mode_help = (
      'Specify the SSL mode to use when the instance connects to the database.'
  )
  if update:
    parser.add_argument(
        '--ssl-mode',
        required=False,
        type=str,
        choices={
            'ENCRYPTED_ONLY': (
                'SSL connections are required. CA verification is not enforced.'
            ),
            'ALLOW_UNENCRYPTED_AND_ENCRYPTED': (
                'SSL connections are optional. CA verification is not enforced.'
            ),
        },
        help=ssl_mode_help,
    )
  elif default_from_primary:
    ssl_mode_help += (
        ' Default SSL mode will match what is set on the primary instance.'
    )
    parser.add_argument(
        '--ssl-mode',
        required=False,
        type=str,
        choices={
            'ENCRYPTED_ONLY': (
                'SSL connections are required. CA verification is not enforced.'
            ),
            'ALLOW_UNENCRYPTED_AND_ENCRYPTED': (
                'SSL connections are optional. CA verification is not enforced.'
            ),
        },
        help=ssl_mode_help,
    )
  else:
    ssl_mode_help += ' Default SSL mode is ENCRYPTED_ONLY.'
    parser.add_argument(
        '--ssl-mode',
        required=False,
        type=str,
        choices={
            'ENCRYPTED_ONLY': (
                'SSL connections are required. CA verification is not enforced.'
            ),
            'ALLOW_UNENCRYPTED_AND_ENCRYPTED': (
                'SSL connections are optional. CA verification is not enforced.'
            ),
        },
        default='ENCRYPTED_ONLY',
        help=ssl_mode_help,
    )


def AddRequireConnectors(parser):
  """Adds Require Connectors flag.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--require-connectors',
      required=False,
      action=arg_parsers.StoreTrueFalseAction,
      help=(
          'Enable or disable enforcing connectors only (ex: AuthProxy) '
          'connections to the database.'
      ),
  )


def AddDatabaseVersion(parser, alloydb_messages):
  """Adds Database Version flag.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    alloydb_messages: Message module.
  """
  choices = [
      alloydb_messages.Cluster.DatabaseVersionValueValuesEnum.POSTGRES_14,
      alloydb_messages.Cluster.DatabaseVersionValueValuesEnum.POSTGRES_15,
      alloydb_messages.Cluster.DatabaseVersionValueValuesEnum.POSTGRES_16,
  ]
  parser.add_argument(
      '--database-version',
      required=False,
      type=alloydb_messages.Cluster.DatabaseVersionValueValuesEnum,
      choices=choices,
      help='Database version of the cluster.',
  )


def AddVersion(parser, alloydb_messages):
  """Adds Version flag.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    alloydb_messages: Message module.
  """
  choices = [
      alloydb_messages.UpgradeClusterRequest.VersionValueValuesEnum.POSTGRES_14,
      alloydb_messages.UpgradeClusterRequest.VersionValueValuesEnum.POSTGRES_15,
      alloydb_messages.UpgradeClusterRequest.VersionValueValuesEnum.POSTGRES_16,
  ]
  parser.add_argument(
      '--version',
      required=True,
      type=alloydb_messages.UpgradeClusterRequest.VersionValueValuesEnum,
      choices=choices,
      help='Target database version for the upgrade.',
  )


def AddSubscriptionType(parser, alloydb_messages):
  """Adds SubscriptionType flag.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    alloydb_messages: Message module.
  """
  parser.add_argument(
      '--subscription-type',
      required=False,
      type=alloydb_messages.Cluster.SubscriptionTypeValueValuesEnum,
      choices=[
          # Don't allow UNSPECIFIED
          alloydb_messages.Cluster.SubscriptionTypeValueValuesEnum.STANDARD,
          alloydb_messages.Cluster.SubscriptionTypeValueValuesEnum.TRIAL,
      ],
      help='Subscription type of the cluster.',
  )


def AddTags(parser):
  """Makes the base.Argument for --tags flag."""
  help_parts = [
      'List of tags KEY=VALUE pairs to bind.',
      'Each item must be expressed as',
      '`<tag-key-namespaced-name>=<tag-value-short-name>`.\n',
      'Example: `123/environment=production,123/costCenter=marketing`\n',
  ]
  parser.add_argument(
      '--tags',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      action=arg_parsers.UpdateAction,
      help='\n'.join(help_parts),
  )


def AddTagsArg(parser):
  """Makes the base.Argument for --tags flag."""
  help_parts = [
      'List of tags KEY=VALUE pairs to bind.',
      'Each item must be expressed as',
      '`<tag-key-namespaced-name>=<tag-value-short-name>`.\n',
      'Example: `123/environment=production,123/costCenter=marketing`\n',
  ]
  parser.add_argument(
      '--tags',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      action=arg_parsers.UpdateAction,
      hidden=True,
      help='\n'.join(help_parts),
  )


def GetTagsFromArgs(args, tags_message, tags_arg_name='tags'):
  """Makes the tags message object."""
  tags = getattr(args, tags_arg_name)
  if not tags:
    return None
  # Sorted for test stability
  return tags_message(
      additionalProperties=[
          tags_message.AdditionalProperty(key=key, value=value)
          for key, value in sorted(tags.items())
      ]
  )


def AddAssignInboundPublicIp(parser):
  """Adds Assign Inbound Public IP flag.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--assign-inbound-public-ip',
      required=False,
      type=str,
      help=("""Specify to enable or disable public IP on an instance.
          ASSIGN_INBOUND_PUBLIC_IP must be one of:
          * *NO_PUBLIC_IP*
          ** This disables public IP on the instance. Updating an instance to
          disable public IP will clear the list of authorized networks.
          * *ASSIGN_IPV4*
          ** Assign an inbound public IPv4 address for the instance.
          Public IP is enabled."""),
  )


def AddAuthorizedExternalNetworks(parser):
  """Adds a `--authorized-external-networks` flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--authorized-external-networks',
      type=arg_parsers.ArgList(),
      metavar='AUTHORIZED_NETWORK',
      required=False,
      help=(
          'Comma-separated list of authorized external networks to set on the '
          'instance. Authorized networks should use CIDR notation (e.g. '
          '1.2.3.4/30). This flag is only allowed to be set for instances with '
          'public IP enabled.'
      ),
  )


def _AddMaintenanceWindowAny(group):
  """Adds maintenance window any flag to the group."""
  group.add_argument(
      '--maintenance-window-any',
      required=False,
      action='store_true',
      default=False,
      help='Remove the user-specified maintenance window.',
  )


def _AddMaintenanceWindowDayAndHour(group, alloydb_messages):
  """Adds maintenance window day and hour flags to the group."""
  day_of_week_enum = alloydb_messages.MaintenanceWindow.DayValueValuesEnum
  group.add_argument(
      '--maintenance-window-day',
      required=True,
      type=day_of_week_enum,
      choices=([
          day_of_week_enum.MONDAY,
          day_of_week_enum.TUESDAY,
          day_of_week_enum.WEDNESDAY,
          day_of_week_enum.THURSDAY,
          day_of_week_enum.FRIDAY,
          day_of_week_enum.SATURDAY,
          day_of_week_enum.SUNDAY,
      ]),
      help='Day of week for maintenance window, in UTC time zone.',
  )
  group.add_argument(
      '--maintenance-window-hour',
      required=True,
      type=arg_parsers.BoundedInt(lower_bound=0, upper_bound=23),
      help='Hour of day for maintenance window, in UTC time zone.',
  )


def AddMaintenanceWindow(parser, alloydb_messages, update=False):
  """Adds maintenance window related flags to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    alloydb_messages: Message module
    update: If false, only allow user to configure maintenance window day and
      hour.
  """
  if update:
    parent_group = parser.add_group(
        mutex=True, help='Configure a preferred maintenance window.'
    )
    child_group = parent_group.add_group(
        help='Specify preferred day and time for maintenance.'
    )
    _AddMaintenanceWindowAny(parent_group)
    _AddMaintenanceWindowDayAndHour(child_group, alloydb_messages)
  else:
    group = parser.add_group(
        help='Specify preferred day and time for maintenance.'
    )
    _AddMaintenanceWindowDayAndHour(group, alloydb_messages)


def _ValidateMonthAndDay(month, day, value):
  """Validates value of month and day."""
  if month < 1 or month > 12:
    raise arg_parsers.ArgumentTypeError(
        'Failed to parse date: {0}, invalid month.'.format(value)
    )
  if day < 1 or day > 31:
    raise arg_parsers.ArgumentTypeError(
        'Failed to parse date: {0}, invalid day.'.format(value)
    )
  return


def _GetDate(alloydb_message):
  """returns google.type.Date date."""

  def Parse(value):
    full_match = re.fullmatch(r'^\d{4}-\d{2}-\d{2}', value)
    if full_match:
      ymd = full_match.group().split('-')
      year = int(ymd[0])
      month = int(ymd[1])
      day = int(ymd[2])
      _ValidateMonthAndDay(month, day, value)
      return alloydb_message.GoogleTypeDate(year=year, month=month, day=day)

    no_year_match = re.fullmatch(r'\d{2}-\d{2}', value)
    if no_year_match:
      ymd = no_year_match.group().split('-')
      month = int(ymd[0])
      day = int(ymd[1])
      _ValidateMonthAndDay(month, day, value)
      return alloydb_message.GoogleTypeDate(year=0, month=month, day=day)

    fmt = '"YYYY-MM-DD" or "MM-DD"'
    err_msg = 'Failed to parse date: {}, expected format: {}.'
    raise arg_parsers.ArgumentTypeError(err_msg.format(value, fmt))

  return Parse


def _GetTimeOfDay(alloydb_message):
  """returns google.type.TimeOfDay time of day from HH:MM format."""

  def Parse(value):
    try:
      dt = datetime.datetime.strptime(value, '%H:%M')
      hour, minute = dt.hour, dt.minute
      return alloydb_message.GoogleTypeTimeOfDay(
          hours=hour,
          minutes=minute,
      )
    except ValueError:
      raise arg_parsers.ArgumentTypeError(
          f'Failed to parse time of day: {value!r}, expected format HH:MM.'
      )

  return Parse


def _AddRemoveDenyMaintenancePeriod(group):
  """Adds remove deny maintenance period flag to the group."""
  group.add_argument(
      '--remove-deny-maintenance-period',
      required=False,
      action='store_true',
      default=False,
      help='Remove the deny maintenance period.',
  )


def _AddDenyMaintenancePeriodDateAndTime(group, alloydb_messages):
  """Adds deny maintenance period start and end date and time flags to the group."""
  group.add_argument(
      '--deny-maintenance-period-start-date',
      required=True,
      type=_GetDate(alloydb_messages),
      help=(
          'Date when the deny maintenance period begins, that is 2020-11-01 or'
          ' 11-01 for recurring.'
      ),
  )
  group.add_argument(
      '--deny-maintenance-period-end-date',
      required=True,
      type=_GetDate(alloydb_messages),
      help=(
          'Date when the deny maintenance period ends, that is 2020-11-01 or'
          ' 11-01 for recurring.'
      ),
  )
  group.add_argument(
      '--deny-maintenance-period-time',
      required=True,
      type=_GetTimeOfDay(alloydb_messages),
      help=(
          'Time when the deny maintenance period starts and ends, for example'
          ' 05:00, in UTC time zone.'
      ),
  )


def AddDenyMaintenancePeriod(parser, alloydb_messages, update=False):
  """Adds deny maintenance period flags to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    alloydb_messages: Message module
    update: If false, only allow user to configure deny maintenance period start
      and end date and time.
  """
  if update:
    parent_group = parser.add_group(
        mutex=True, help='Specify maintenance deny period.'
    )
    child_group = parent_group.add_group(
        help='Specify preferred day and time for maintenance deny period.'
    )
    _AddRemoveDenyMaintenancePeriod(parent_group)
    _AddDenyMaintenancePeriodDateAndTime(child_group, alloydb_messages)
  else:
    group = parser.add_group(
        help='Specify preferred day and time for maintenance deny period.',
    )
    _AddDenyMaintenancePeriodDateAndTime(group, alloydb_messages)


def AddNodeIds(parser):
  """Adds the `--node-ids` flag to the parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--node-ids',
      required=False,
      type=arg_parsers.ArgList(),
      metavar='NODE_IDS',
      help=(
          'Comma-separated list of node IDs. '
          'Only supported for read pool instances. (e.g.,'
          ' `--node-ids=node-1,node-2,node-3`)'
      ),
  )


def AddDatabase(parser, required=True):
  """Adds a --database flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --database is required.
  """
  parser.add_argument(
      '--database',
      required=required,
      type=str,
      help='Database name.',
  )


def AddDestinationURI(parser, required=True):
  """Adds a --gcs-uri flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --gcs-uri is required.
  """
  destination_uri_group = parser.add_group(
      mutex=True,
      required=required,
      help='Destination URI where the file needs to be exported.',
  )
  destination_uri_group.add_argument(
      '--gcs-uri',
      type=str,
      help=(
          'Path to the Google Cloud Storage file to which'
          ' export has to be done.'
      ),
  )


def AddExportOptions(parser):
  """Adds a --select-query flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  export_options_group = parser.add_group(
      mutex=True, required=True, help='Export options for the cluster.'
  )
  csv_export_options_group = export_options_group.add_group(
      help='CSV export options for the cluster.'
  )
  csv_export_options_group.add_argument(
      '--csv',
      required=True,
      action='store_true',
      help='Specifies destination file type.',
  )
  csv_export_options_group.add_argument(
      '--select-query',
      required=True,
      type=str,
      help='Select query to be used for export.',
  )
  csv_export_options_group.add_argument(
      '--field-delimiter',
      required=False,
      type=str,
      help='Field delimiter to be used for export.',
  )
  csv_export_options_group.add_argument(
      '--escape-character',
      required=False,
      type=str,
      help='Escape character to be used for export.',
  )
  csv_export_options_group.add_argument(
      '--quote-character',
      required=False,
      type=str,
      help='Quote character to be used for export.',
  )
  sql_export_options_group = export_options_group.add_group(
      help='SQL export options for the cluster.'
  )
  sql_export_options_group.add_argument(
      '--sql',
      required=True,
      action='store_true',
      help='Specifies destination file type.',
  )
  sql_export_options_group.add_argument(
      '--schema-only',
      required=False,
      action='store_true',
      help='Export only schema of the database.',
  )
  sql_export_options_group.add_argument(
      '--tables',
      required=False,
      type=str,
      help='Comma-separated list of table names which need to be exported.',
  )
  clean_target_options_group = sql_export_options_group.add_group(
      help='SQL export options to clean target objects.'
  )
  clean_target_options_group.add_argument(
      '--clean-target-objects',
      required=True,
      action='store_true',
      help=(
          'If true, output commands to DROP all the dumped database objects'
          ' prior to outputting the commands for creating them.'
      ),
  )
  clean_target_options_group.add_argument(
      '--if-exist-target-objects',
      required=False,
      action='store_true',
      help=(
          "If true, use DROP ... IF EXISTS commands to check for the object's"
          ' existence before dropping it in clean_target_objects mode.'
      ),
  )


def AddSourceURI(parser, required=True):
  """Adds a --gcs-uri flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --gcs-uri is required.
  """
  source_uri_group = parser.add_group(
      mutex=True,
      required=required,
      help='URI of the source file for import.',
  )
  source_uri_group.add_argument(
      '--gcs-uri',
      type=str,
      help=(
          'Path to the Google Cloud Storage file from which'
          ' import has to be done.'
      ),
  )


def AddImportUser(parser):
  """Adds --user flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--user',
      required=False,
      type=str,
      help='Database user for the import.',
  )


def AddImportOptions(parser):
  """Adds different import options flags to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  import_options_group = parser.add_group(
      mutex=True, required=True, help='Import options for the cluster.'
  )
  csv_import_options_group = import_options_group.add_group(
      help='CSV import options for the cluster.'
  )
  csv_import_options_group.add_argument(
      '--csv',
      required=True,
      action='store_true',
      help='Specify source file type.',
  )
  csv_import_options_group.add_argument(
      '--table',
      required=True,
      type=str,
      help='Table name to which the data has to be imported.',
  )
  csv_import_options_group.add_argument(
      '--columns',
      required=False,
      type=str,
      help='Comma-separated list of column names to be used for import.',
  )
  csv_import_options_group.add_argument(
      '--field-delimiter',
      required=False,
      type=str,
      help='Field delimiter in the source file.',
  )
  csv_import_options_group.add_argument(
      '--escape-character',
      required=False,
      type=str,
      help='Escape character in the source file.',
  )
  csv_import_options_group.add_argument(
      '--quote-character',
      required=False,
      type=str,
      help='Quote character in the source file.',
  )
  sql_import_options_group = import_options_group.add_group(
      help='SQL import options for the cluster.'
  )
  sql_import_options_group.add_argument(
      '--sql',
      required=True,
      action='store_true',
      help='Specify source file type.',
  )


def AddMigrateCloudSqlFlags(parser: argparse.PARSER) -> None:
  """Adds the Migrate Cloud SQL specific flags.

  Args:
    parser: Parser object for command line inputs.
  """
  group = parser.add_group(
      mutex=True, required=True, help='Migrate Cloud SQL strategy.'
  )
  parser.add_argument(
      '--cloud-sql-project-id',
      required=True,
      type=str,
      help=(
          'CloudSQL project to migrate from. This must be the'
          ' project ID (myProject).'
      ),
  )
  parser.add_argument(
      '--cloud-sql-instance-id',
      required=True,
      type=str,
      help=(
          'CloudSQL instance ID to migrate from. This must be the'
          ' instance ID (myInstance).'
      ),
  )
  # Currently, only migration via restore from CloudSQL backup is supported.
  migrate_cloud_sql_group = group.add_group(
      help=(
          'Migrate CloudSQL instance to an AlloyDB cluster by restoring from'
          ' an existing backup.'
      )
  )
  migrate_cloud_sql_group.add_argument(
      '--cloud-sql-backup-id',
      required=True,
      type=int,
      help=(
          'CloudSQL backup ID to migrate from. This must be the'
          ' backup ID (myBackup).'
      ),
  )
