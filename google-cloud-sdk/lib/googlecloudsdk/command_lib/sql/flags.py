# -*- coding: utf-8 -*- #
# Copyright 2015 Google LLC. All Rights Reserved.
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
"""Common flags for some of the SQL commands.

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

import sys
from googlecloudsdk.api_lib.compute import utils as compute_utils
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.util import completers

messages = apis.GetMessagesModule('sql', 'v1beta4')
DEFAULT_INSTANCE_DATABASE_VERSION = 'MYSQL_8_0'

_IP_ADDRESS_PART = r'(25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})'  # Match decimal 0-255
_CIDR_PREFIX_PART = r'([0-9]|[1-2][0-9]|3[0-2])'  # Match decimal 0-32
# Matches either IPv4 range in CIDR notation or a naked IPv4 address.
_CIDR_REGEX = r'{addr_part}(\.{addr_part}){{3}}(\/{prefix_part})?$'.format(
    addr_part=_IP_ADDRESS_PART, prefix_part=_CIDR_PREFIX_PART
)


class DatabaseCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(DatabaseCompleter, self).__init__(
        collection='sql.databases',
        api_version='v1beta4',
        list_command='sql databases list --uri',
        flags=['instance'],
        **kwargs)


class InstanceCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(InstanceCompleter, self).__init__(
        collection='sql.instances',
        list_command='sql instances list --uri',
        **kwargs)


class UserCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(UserCompleter, self).__init__(
        collection=None,  # TODO(b/62961917): Should be 'sql.users',
        api_version='v1beta4',
        list_command='sql users list --flatten=name[] --format=disable',
        flags=['instance'],
        **kwargs)


class _MajorVersionMatchList(list):

  def __contains__(self, database_version):
    """Check if <database_version> begins with a major_version in <self>."""
    return any(
        database_version.startswith(major_version) for major_version in self)


def AddInstance(parser, support_wildcard_instances=False):
  parser.add_argument(
      '--instance',
      '-i',
      required=True,
      completer=InstanceCompleter,
      help='Cloud SQL instance ID.' if not support_wildcard_instances else
      'Cloud SQL instance ID or "-" for all instances.')


def AddOptionalInstance(parser, support_wildcard_instances=False):
  parser.add_argument(
      '--instance',
      required=False,
      completer=InstanceCompleter,
      help='Cloud SQL instance ID.' if not support_wildcard_instances else
      'Cloud SQL instance ID or "-" for all instances.')


def AddInstanceArgument(parser):
  """Add the 'instance' argument to the parser."""
  parser.add_argument(
      'instance', completer=InstanceCompleter, help='Cloud SQL instance ID.')


# The max storage size specified can be the int's max value, and min is 10.
def AddInstanceResizeLimit(parser):
  parser.add_argument(
      '--storage-auto-increase-limit',
      type=arg_parsers.BoundedInt(10, sys.maxsize, unlimited=True),
      help='Allows you to set a maximum storage capacity, in GB. Automatic '
      'increases to your capacity will stop once this limit has been reached. '
      'Default capacity is *unlimited*.')


def AddUsername(parser):
  parser.add_argument(
      'username', completer=UserCompleter, help='Cloud SQL username.')


def AddHost(parser):
  """Add the '--host' flag to the parser."""
  parser.add_argument(
      '--host',
      help=(
          "Cloud SQL user's hostname expressed as a specific IP address or"
          ' address range. `%` denotes an unrestricted hostname. Applicable'
          ' flag for MySQL instances; ignored for all other engines. Note, if'
          ' you connect to your instance using IP addresses, you must add your'
          ' client IP address as an authorized address, even if your hostname'
          ' is unrestricted. For more information, see [Configure'
          ' IP](https://cloud.google.com/sql/docs/mysql/configure-ip).'
      ),
  )


def AddAvailabilityType(parser):
  """Add the '--availability-type' flag to the parser."""
  availabilty_type_flag = base.ChoiceArgument(
      '--availability-type',
      required=False,
      choices={
          'regional': 'Provides high availability and is recommended for '
                      'production instances; instance automatically fails over '
                      'to another zone within your selected region.',
          'zonal': 'Provides no failover capability. This is the default.'
      },
      help_str=('Specifies level of availability.'))
  availabilty_type_flag.AddToParser(parser)


def AddPassword(parser):
  parser.add_argument('--password', help='Cloud SQL user\'s password.')


def AddRootPassword(parser):
  """Add the root password field to the parser."""
  parser.add_argument(
      '--root-password',
      required=False,
      help='Root Cloud SQL user\'s password.')


def AddPromptForPassword(parser):
  parser.add_argument(
      '--prompt-for-password',
      action='store_true',
      help=('Prompt for the Cloud SQL user\'s password with character echo '
            'disabled. The password is all typed characters up to but not '
            'including the RETURN or ENTER key.'))


def AddType(parser):
  parser.add_argument(
      '--type',
      help='Cloud SQL user\'s type. It determines '
      'the method to authenticate the user during login. '
      'See the list of user types at '
      'https://cloud.google.com/sql/docs/postgres/admin-api/'
      'rest/v1beta4/SqlUserType')


# Instance create and patch flags


def AddActivationPolicy(parser):
  base.ChoiceArgument(
      '--activation-policy',
      required=False,
      choices=['always', 'never', 'on-demand'],
      default=None,
      help_str=(
          'Activation policy for this instance. This specifies when '
          'the instance should be activated and is applicable only when '
          'the instance state is `RUNNABLE`. The default is `on-demand`. '
          'More information on activation policies can be found here: '
          'https://cloud.google.com/sql/docs/mysql/start-stop-restart-instance#activation_policy'
      )).AddToParser(parser)


def AddAssignIp(parser):
  parser.add_argument(
      '--assign-ip',
      help='Assign a public IP address to the instance. This is a public, '
      'externally available IPv4 address that you can use to connect to your '
      'instance when properly authorized.',
      action=arg_parsers.StoreTrueFalseAction)


def AddEnableGooglePrivatePath(parser, show_negated_in_help=False):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--enable-google-private-path',
      required=False,
      help='Enable a private path for Google Cloud services. '
      'This flag specifies whether the instance is accessible to '
      'internal Google Cloud services such as BigQuery. '
      'This is only applicable to MySQL and PostgreSQL instances that '
      'don\'t use public IP. Currently, SQL Server isn\'t supported.',
      **kwargs)


def AddAuthorizedGAEApps(parser, update=False):
  help_ = (
      'First Generation instances only. List of project IDs for App Engine '
      'applications running in the Standard environment that '
      'can access this instance.')
  if update:
    help_ += (
        '\n\nThe value given for this argument *replaces* the existing list.')
  parser.add_argument(
      '--authorized-gae-apps',
      type=arg_parsers.ArgList(min_length=1),
      metavar='APP',
      required=False,
      help=help_)


def AddAuthorizedNetworks(parser, update=False):
  """Adds the `--authorized-networks` flag."""
  cidr_validator = arg_parsers.RegexpValidator(
      _CIDR_REGEX, ('Must be specified in CIDR notation, also known as '
                    '\'slash\' notation (e.g. 192.168.100.0/24).'))
  help_ = ('The list of external networks that are allowed to connect to '
           'the instance. Specified in CIDR notation, also known as '
           '\'slash\' notation (e.g. 192.168.100.0/24).')
  if update:
    help_ += (
        '\n\nThe value given for this argument *replaces* the existing list.')
  parser.add_argument(
      '--authorized-networks',
      type=arg_parsers.ArgList(min_length=1, element_type=cidr_validator),
      metavar='NETWORK',
      required=False,
      default=[],
      help=help_)


def AddBackupStartTime(parser):
  parser.add_argument(
      '--backup-start-time',
      required=False,
      help=('Start time of daily backups, specified in the HH:MM format, in '
            'the UTC timezone.'))


def AddBackupLocation(parser, allow_empty):
  help_text = (
      'Choose where to store your backups. Backups are stored in the closest '
      'multi-region location to you by default. Only customize if needed.')
  if allow_empty:
    help_text += ' Specify empty string to revert to default.'
  parser.add_argument('--backup-location', required=False, help=help_text)


# Currently, MAX_BACKUP_RETENTION_COUNT=365, and MIN_BACKUP_RETENTION_COUNT=1.
def AddRetainedBackupsCount(parser):
  help_text = (
      'How many backups to keep. The valid range is between 1 and 365. The '
      'default value is 7 if not specified. Applicable only if --no-backups is '
      'not specified.')
  parser.add_argument(
      '--retained-backups-count',
      type=arg_parsers.BoundedInt(1, 365, unlimited=False),
      help=help_text)


# Currently, MAX_TRANSACTION_LOG_RETENTION_DAYS=35, and
# MIN_TRANSACTION_LOG_RETENTION_DAYS=1.
def AddRetainedTransactionLogDays(parser):
  help_text = (
      'How many days of transaction logs to keep. The valid range is between 1 '
      'and 35. The default value is 7. The 35 days log retention feature is '
      'only enabled for specific customer. Only use this option when point-in-'
      'time recovery is enabled. Storage size for transaction logs increases '
      'when the number of days for log retention increases.')
  parser.add_argument(
      '--retained-transaction-log-days',
      type=arg_parsers.BoundedInt(1, 35, unlimited=False),
      help=help_text)


def AddDatabaseFlags(parser, update=False):
  """Adds the `--database-flags` flag."""
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


def AddDatabaseVersion(parser,
                       restrict_choices=True,
                       hidden=False,
                       support_default_version=True):
  """Adds `--database-version` to the parser with choices restricted or not."""
  # Section for engine-specific content.
  # This section is auto-generated by //cloud/storage_fe/sql/sync_engines.
  # Do not make manual edits.
  choices = [
      'MYSQL_5_6',
      'MYSQL_5_7',
      'MYSQL_8_0',
      'POSTGRES_9_6',
      'POSTGRES_10',
      'POSTGRES_11',
      'POSTGRES_12',
      'POSTGRES_13',
      'POSTGRES_14',
      'POSTGRES_15',
      'SQLSERVER_2017_EXPRESS',
      'SQLSERVER_2017_WEB',
      'SQLSERVER_2017_STANDARD',
      'SQLSERVER_2017_ENTERPRISE',
      'SQLSERVER_2019_EXPRESS',
      'SQLSERVER_2019_WEB',
      'SQLSERVER_2019_STANDARD',
      'SQLSERVER_2019_ENTERPRISE',
  ]
  # End of engine-specific content.

  help_text_unspecified_part = DEFAULT_INSTANCE_DATABASE_VERSION + ' is used.' if support_default_version else 'no changes occur.'
  help_text = (
      'The database engine type and versions. If left unspecified, ' +
      help_text_unspecified_part + ' See the list of database versions at ' +
      'https://cloud.google.com/sql/docs/mysql/admin-api/rest/v1beta4/SqlDatabaseVersion.'
  )

  if restrict_choices:
    help_text += (
        ' Apart from listed major versions, DATABASE_VERSION also accepts'
        ' supported minor versions.')

  parser.add_argument(
      '--database-version',
      required=False,
      default=DEFAULT_INSTANCE_DATABASE_VERSION
      if support_default_version else None,
      choices=_MajorVersionMatchList(choices) if restrict_choices else None,
      help=help_text,
      hidden=hidden)


def AddCPU(parser):
  parser.add_argument(
      '--cpu',
      type=int,
      required=False,
      help=('Whole number value indicating how many cores are desired in '
            'the machine. Both --cpu and --memory must be specified if a '
            'custom machine type is desired, and the --tier flag must be '
            'omitted.'))


def _GetKwargsForBoolFlag(show_negated_in_help):
  if show_negated_in_help:
    return {
        'action': arg_parsers.StoreTrueFalseAction,
    }
  else:
    return {'action': 'store_true', 'default': None}


def AddInstanceCollation(parser):
  parser.add_argument(
      '--collation',
      help='Cloud SQL server-level collation setting, which specifies '
      'the set of rules for comparing characters in a character set.')


def AddEnableBinLog(parser, show_negated_in_help=False):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--enable-bin-log',
      required=False,
      help=('Allows for data recovery from a specific point in time, down to a '
            'fraction of a second. Must have automatic backups enabled to use. '
            'Make sure storage can support at least 7 days of logs.'),
      **kwargs)


def AddEnablePointInTimeRecovery(parser, show_negated_in_help=False):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--enable-point-in-time-recovery',
      required=False,
      help=('Allows for data recovery from a specific point in time, down to a '
            'fraction of a second, via write-ahead logs. Must have automatic '
            'backups enabled to use. Make sure storage can support at least 7 '
            'days of logs.'),
      **kwargs)


def AddExternalMasterGroup(parser):
  """Add flags to the parser for creating an external master and replica."""

  # Group for creating external primary instances.
  external_master_group = parser.add_group(
      required=False,
      help='Options for creating a wrapper for an external data source.')
  external_master_group.add_argument(
      '--source-ip-address',
      required=True,
      type=compute_utils.IPV4Argument,
      help=('Public IP address used to connect to and replicate from '
            'the external data source.'))
  external_master_group.add_argument(
      '--source-port',
      type=arg_parsers.BoundedInt(lower_bound=1, upper_bound=65535),
      # Default MySQL port number.
      default=3306,
      help=('Port number used to connect to and replicate from the '
            'external data source.'))

  # Group for creating replicas of external primary instances.
  internal_replica_group = parser.add_group(
      required=False,
      help=('Options for creating an internal replica of an external data '
            'source.'))
  internal_replica_group.add_argument(
      '--master-username',
      required=True,
      help='Name of the replication user on the external data source.')

  # TODO(b/78648703): Make group required when mutex required status is fixed.
  # For entering the password of the replication user of an external primary.
  master_password_group = internal_replica_group.add_group(
      'Password group.', mutex=True)
  master_password_group.add_argument(
      '--master-password',
      help='Password of the replication user on the external data source.')
  master_password_group.add_argument(
      '--prompt-for-master-password',
      action='store_true',
      help=('Prompt for the password of the replication user on the '
            'external data source. The password is all typed characters up '
            'to but not including the RETURN or ENTER key.'))
  internal_replica_group.add_argument(
      '--master-dump-file-path',
      required=True,
      type=storage_util.ObjectReference.FromArgument,
      help=('Path to the MySQL dump file in Google Cloud Storage from '
            'which the seed import is made. The URI is in the form '
            'gs://bucketName/fileName. Compressed gzip files (.gz) are '
            'also supported.'))

  # For specifying SSL certs for connecting to an external primary.
  credential_group = internal_replica_group.add_group(
      'Client and server credentials.', required=False)
  credential_group.add_argument(
      '--master-ca-certificate-path',
      required=True,
      help=('Path to a file containing the X.509v3 (RFC5280) PEM encoded '
            'certificate of the CA that signed the external data source\'s '
            'certificate.'))

  # For specifying client certs for connecting to an external primary.
  client_credential_group = credential_group.add_group(
      'Client credentials.', required=False)
  client_credential_group.add_argument(
      '--client-certificate-path',
      required=True,
      help=('Path to a file containing the X.509v3 (RFC5280) PEM encoded '
            'certificate that will be used by the replica to authenticate '
            'against the external data source.'))
  client_credential_group.add_argument(
      '--client-key-path',
      required=True,
      help=('Path to a file containing the unencrypted PKCS#1 or PKCS#8 '
            'PEM encoded private key associated with the '
            'clientCertificate.'))


def AddFollowGAEApp(parser):
  parser.add_argument(
      '--follow-gae-app',
      required=False,
      help=('First Generation instances only. The App Engine app '
            'this instance should follow. It must be in the same region as '
            'the instance. WARNING: Instance may be restarted.'))


def AddMaintenanceReleaseChannel(parser):
  base.ChoiceArgument(
      '--maintenance-release-channel',
      choices={
          'production': 'Production updates are stable and recommended '
                        'for applications in production.',
          'preview': 'Preview updates release prior to production '
                     'updates. You may wish to use the preview channel '
                     'for dev/test applications so that you can preview '
                     'their compatibility with your application prior '
                     'to the production release.'
      },
      help_str=("Which channel's updates to apply during the maintenance "
                'window. If not specified, Cloud SQL chooses the timing of '
                'updates to your instance.')).AddToParser(parser)


def AddMaintenanceWindowDay(parser):
  parser.add_argument(
      '--maintenance-window-day',
      choices=arg_parsers.DayOfWeek.DAYS,
      type=arg_parsers.DayOfWeek.Parse,
      help='Day of week for maintenance window, in UTC time zone.')


def AddMaintenanceWindowHour(parser):
  parser.add_argument(
      '--maintenance-window-hour',
      type=arg_parsers.BoundedInt(lower_bound=0, upper_bound=23),
      help='Hour of day for maintenance window, in UTC time zone.')


def AddDenyMaintenancePeriodStartDate(parser):
  parser.add_argument(
      '--deny-maintenance-period-start-date',
      help='Date when the deny maintenance period begins, that is ``2020-11-01\'\'.'
      )


def AddDenyMaintenancePeriodEndDate(parser):
  parser.add_argument(
      '--deny-maintenance-period-end-date',
      help='Date when the deny maintenance period ends, that is ``2021-01-10\'\'.'
  )


def AddDenyMaintenancePeriodTime(parser):
  parser.add_argument(
      '--deny-maintenance-period-time',
      help='Time when the deny maintenance period starts or ends, that is ``05:00:00\'\'.'
  )


def AddInsightsConfigQueryInsightsEnabled(parser, show_negated_in_help=False):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--insights-config-query-insights-enabled',
      required=False,
      help="""Enable query insights feature to provide query and query plan
        analytics.""",
      **kwargs)


def AddInsightsConfigQueryStringLength(parser):
  parser.add_argument(
      '--insights-config-query-string-length',
      required=False,
      type=arg_parsers.BoundedInt(lower_bound=256, upper_bound=4500),
      help="""Query string length in bytes to be stored by the query insights
        feature. Default length is 1024 bytes. Allowed range: 256 to 4500
        bytes.""")


def AddInsightsConfigRecordApplicationTags(parser, show_negated_in_help=False):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--insights-config-record-application-tags',
      required=False,
      help="""Allow application tags to be recorded by the query insights
        feature.""",
      **kwargs)


def AddInsightsConfigRecordClientAddress(parser, show_negated_in_help=False):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--insights-config-record-client-address',
      required=False,
      help="""Allow the client address to be recorded by the query insights
        feature.""",
      **kwargs)


def AddInsightsConfigQueryPlansPerMinute(parser):
  parser.add_argument(
      '--insights-config-query-plans-per-minute',
      required=False,
      type=arg_parsers.BoundedInt(lower_bound=0, upper_bound=20),
      help="""Number of query plans to sample every minute.
        Default value is 5. Allowed range: 0 to 20.""")


def AddMemory(parser):
  parser.add_argument(
      '--memory',
      type=arg_parsers.BinarySize(),
      required=False,
      help=('Whole number value indicating how much memory is desired in '
            'the machine. A size unit should be provided (eg. 3072MiB or '
            '9GiB) - if no units are specified, GiB is assumed. Both --cpu '
            'and --memory must be specified if a custom machine type is '
            'desired, and the --tier flag must be omitted.'))


def AddNetwork(parser):
  """Adds the `--network` flag to the parser."""
  parser.add_argument(
      '--network',
      help=('Network in the current project that the instance will be part '
            'of. To specify using a network with a shared VPC, use the full '
            'URL of the network. For an example host project, \'testproject\', '
            'and shared network, \'testsharednetwork\', this would use the '
            'form: '
            '`--network`=`projects/testproject/global/networks/'
            'testsharednetwork`'))


def AddAllocatedIpRangeName(parser):
  """Adds the `--allocated-ip-range-name` flag to the parser."""
  parser.add_argument(
      '--allocated-ip-range-name',
      required=False,
      help=('The name of the IP range allocated for a Cloud SQL instance with '
            'private network connectivity. For example: '
            '\'google-managed-services-default\'. If set, the instance IP is '
            'created in the allocated range represented by this name.'))


def AddMaintenanceVersion(parser):
  """Adds the `--maintenance-version` flag to the parser."""
  parser.add_argument(
      '--maintenance-version',
      required=False,
      help=('The desired maintenance version of the instance.'))


def AddSqlServerAudit(parser):
  """Adds SQL Server audit related flags to the parser."""
  parser.add_argument(
      '--audit-bucket-path',
      required=False,
      help=(
          'The location, as a Cloud Storage bucket, to which audit files are '
          'uploaded. The URI is in the form gs://bucketName/folderName. Only '
          'available for SQL Server instances.'
      ))

  parser.add_argument(
      '--audit-retention-interval',
      default=None,
      type=arg_parsers.Duration(upper_bound='7d'),
      required=False,
      help=(
          'The number of days for audit log retention on disk, for example, 3d'
          'for 3 days. Only available for SQL Server instances.'
      ))

  parser.add_argument(
      '--audit-upload-interval',
      default=None,
      type=arg_parsers.Duration(upper_bound='720m'),
      required=False,
      help=(
          'How often to upload audit logs (audit files), for example, 30m'
          'for 30 minutes. Only available for SQL Server instances.'
      ))


def AddReplication(parser):
  base.ChoiceArgument(
      '--replication',
      required=False,
      choices=['synchronous', 'asynchronous'],
      default=None,
      help_str='Type of replication this instance uses. The default is '
      'synchronous.').AddToParser(parser)


def AddStorageAutoIncrease(parser, show_negated_in_help=True):
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--storage-auto-increase',
      help=('Storage size can be increased, but it cannot be decreased; '
            'storage increases are permanent for the life of the instance. '
            'With this setting enabled, a spike in storage requirements '
            'can result in permanently increased storage costs for your '
            'instance. However, if an instance runs out of available space, '
            'it can result in the instance going offline, dropping existing '
            'connections. This setting is enabled by default.'),
      **kwargs)


def AddStorageSize(parser):
  parser.add_argument(
      '--storage-size',
      type=arg_parsers.BinarySize(
          lower_bound='10GB',
          upper_bound='65536GB',
          suggested_binary_size_scales=['GB']),
      help=('Amount of storage allocated to the instance. Must be an integer '
            'number of GB. The default is 10GB. Information on storage '
            'limits can be found here: '
            'https://cloud.google.com/sql/docs/quotas#storage_limits'))


def AddStorageSizeForStorageShrink(parser):
  parser.add_argument(
      '--storage-size',
      type=arg_parsers.BinarySize(
          lower_bound='10GB',
          upper_bound='65536GB',
          suggested_binary_size_scales=['GB'],
      ),
      required=True,
      help=(
          'The target storage size must be an integer that represents the'
          ' number of GB. For example, --storage-size=10GB'
      ),
  )


def AddTier(parser, is_patch=False, is_alpha=False):
  """Adds '--tier' and '--workload_tier' flags to the parser."""
  tier_group = parser.add_mutually_exclusive_group()

  help_text = ("Machine type for a shared-core instance e.g. ``db-g1-small''. "
               'For all other instances, instead of using tiers, customize '
               'your instance by specifying its CPU and memory. You can do so '
               'with the `--cpu` and `--memory` flags. Learn more about how '
               'CPU and memory affects pricing: '
               'https://cloud.google.com/sql/pricing.')
  if is_patch:
    help_text += ' WARNING: Instance will be restarted.'

  tier_group.add_argument('--tier', '-t', required=False, help=help_text)
  if not is_alpha:
    return
  workload_tier_flag = base.ChoiceArgument(
      '--workload-tier',
      required=False,
      choices={
          'standard':
              'Standard option for smaller instances.',
          'premium':
              'Premium option recommended for cpu-intensive workloads. '
              'Offers access to premium features and capabilities.'
      },
      default=None,
      hidden=True,
      help_str=('Specifies workload tier.'))
  workload_tier_flag.AddToParser(tier_group)


def AddZone(parser, help_text):
  """Adds the mutually exclusive `--gce-zone` and `--zone` to the parser."""
  zone_group = parser.add_mutually_exclusive_group()
  zone_group.add_argument(
      '--gce-zone',
      required=False,
      action=actions.DeprecationAction(
          '--gce-zone',
          removed=False,
          warn=('Flag `{flag_name}` is deprecated and will be removed by '
                'release 255.0.0. Use `--zone` instead.')),
      help=help_text)

  AddZonesPrimarySecondary(zone_group, help_text)


def AddZonesPrimarySecondary(parser, help_text):
  """Adds the `--zone` and `--secondary-zone` to the parser."""

  zone_group = parser.add_group(required=False)
  zone_group.add_argument('--zone', required=False, help=help_text)
  zone_group.add_argument(
      '--secondary-zone',
      required=False,
      help=('Preferred secondary Compute Engine zone '
            '(e.g. us-central1-a, us-central1-b, etc.).'))


def AddRegion(parser):
  parser.add_argument(
      '--region',
      required=False,
      default='us-central',
      help=('Regional location (e.g. asia-east1, us-east1). See the full '
            'list of regions at '
            'https://cloud.google.com/sql/docs/instance-locations.'))


# TODO(b/31989340): add remote completion
# TODO(b/73362371): Make specifying a location required.
def AddLocationGroup(parser):
  location_group = parser.add_mutually_exclusive_group()
  AddRegion(location_group)
  AddZone(
      location_group,
      help_text=('Preferred Compute Engine zone (e.g. us-central1-a, '
                 'us-central1-b, etc.).'))


# Database specific flags


def AddDatabaseName(parser):
  parser.add_argument(
      'database', completer=DatabaseCompleter, help='Cloud SQL database name.')


def AddCharset(parser):
  parser.add_argument(
      '--charset',
      help='Cloud SQL database charset setting, which specifies the '
      'set of symbols and encodings used to store the data in your database. '
      'Each database version may support a different set of charsets.')


def AddCollation(parser, custom_help=None):
  parser.add_argument(
      '--collation',
      help=custom_help or 'Cloud SQL database collation setting, which '
      'specifies the set of rules for comparing characters in a character set. '
      'Each database version may support a different set of collations. For '
      'PostgreSQL database versions, this may only be set to the collation of '
      'the template database.')


def AddOperationArgument(parser):
  parser.add_argument(
      'operation',
      nargs='+',
      help='An identifier that uniquely identifies the operation.')


# Instance export / import flags.


def AddUriArgument(parser, help_text):
  """Add the 'uri' argument to the parser, with help text help_text."""
  parser.add_argument('uri', help=help_text)


def AddOffloadArgument(parser):
  """Add the 'offload' argument to the parser."""
  parser.add_argument(
      '--offload',
      action='store_true',
      help=(
          'Offload an export to a temporary instance. Doing so reduces strain '
          'on source instances and allows other operations to be performed '
          'while the export is in progress.'))


def AddQuoteArgument(parser):
  """Add the 'quote' argument to the parser."""
  parser.add_argument(
      '--quote',
      help=(
          'Specifies the character that encloses values from columns that have '
          'string data type. The value of this argument has to be a character '
          'in Hex ASCII Code. For example, "22" represents double quotes. '
          'This flag is only available for MySQL and Postgres. If this flag is '
          'not provided, double quotes character will be used as the default '
          'value.'))


def AddEscapeArgument(parser):
  """Add the 'escape' argument to the parser."""
  parser.add_argument(
      '--escape',
      help=(
          'Specifies the character that should appear before a data character '
          'that needs to be escaped. The value of this argument has to be a '
          'character in Hex ASCII Code. For example, "22" represents double '
          'quotes. This flag is only available for MySQL and Postgres. If this '
          'flag is not provided, double quotes character will be used as the '
          'default value.'))


def AddFieldsDelimiterArgument(parser):
  """Add the 'fields-terminated-by' argument to the parser."""
  parser.add_argument(
      '--fields-terminated-by',
      help=(
          'Specifies the character that splits column values. The value of this '
          'argument has to be a character in Hex ASCII Code. For example, '
          '"2C" represents a comma. This flag is only available for MySQL '
          'and Postgres. If this flag is not provided, a comma character will '
          'be used as the default value.'))


def AddLinesDelimiterArgument(parser):
  """Add the 'lines-terminated-by' argument to the parser."""
  parser.add_argument(
      '--lines-terminated-by',
      help=(
          'Specifies the character that split line records. The value of this '
          'argument has to be a character in Hex ASCII Code. For example, '
          '"0A" represents a new line. This flag is only available for MySQL. '
          'If this flag is not provided, a new line character will be used as '
          'the default value.'))


DEFAULT_DATABASE_IMPORT_HELP_TEXT = (
    'Database to which the import is made. If not set, it is assumed that '
    'the database is specified in the file to be imported. If your SQL '
    'dump file includes a database statement, it will override the '
    'database set in this flag.')

SQLSERVER_DATABASE_IMPORT_HELP_TEXT = (
    'A new database into which the import is made.')


def AddDatabase(parser, help_text, required=False):
  """Add the '--database' and '-d' flags to the parser.

  Args:
    parser: The current argparse parser to add these database flags to.
    help_text: String, specifies the help text for the database flags.
    required: Boolean, specifies whether the database flag is required.
  """
  parser.add_argument('--database', '-d', required=required, help=help_text)


DEFAULT_DATABASE_LIST_EXPORT_HELP_TEXT = (
    'Database(s) from which the export is made. Information on requirements '
    'can be found here: https://cloud.google.com/sql/docs/mysql/admin-api/'
    'v1beta4/instances/export#exportContext.databases')

SQLSERVER_DATABASE_LIST_EXPORT_HELP_TEXT = (
    'Database from which the export is made. Information on requirements '
    'can be found here: https://cloud.google.com/sql/docs/sqlserver/admin-api/'
    'v1beta4/instances/export#exportContext.databases')


def AddDatabaseList(parser, help_text, required=False):
  """Add the '--database' and '-d' list flags to the parser.

  Args:
    parser: The current argparse parser to add these database flags to.
    help_text: String, specifies the help text for the database flags.
    required: Boolean, specifies whether the database flag is required.
  """
  if required:
    group = parser.add_group(mutex=False, required=True)
    group.add_argument(
        '--database',
        '-d',
        type=arg_parsers.ArgList(min_length=1),
        metavar='DATABASE',
        help=help_text)
  else:
    parser.add_argument(
        '--database',
        '-d',
        type=arg_parsers.ArgList(min_length=1),
        metavar='DATABASE',
        required=False,
        help=help_text)


def AddUser(parser, help_text):
  """Add the '--user' flag to the parser, with help text help_text."""
  parser.add_argument('--user', help=help_text)


def AddEncryptedBakFlags(parser):
  """Add the flags for importing encrypted BAK files.

  Add the --cert-path, --pvk-path, --pvk-password and
  --prompt-for-pvk-password flags to the parser

  Args:
    parser: The current argparse parser to add these database flags to.
  """
  enc_group = parser.add_group(
      mutex=False,
      required=False,
      help='Encryption info to support importing an encrypted .bak file')
  enc_group.add_argument(
      '--cert-path',
      required=True,
      help=('Path to the encryption certificate file in Google Cloud Storage '
            'associated with the BAK file. The URI is in the form '
            '`gs://bucketName/fileName`.'))
  enc_group.add_argument(
      '--pvk-path',
      required=True,
      help=('Path to the encryption private key file in Google Cloud Storage '
            'associated with the BAK file. The URI is in the form '
            '`gs://bucketName/fileName`.'))
  password_group = enc_group.add_group(mutex=True, required=True)
  password_group.add_argument(
      '--pvk-password',
      help='The private key password associated with the BAK file.')
  password_group.add_argument(
      '--prompt-for-pvk-password',
      action='store_true',
      help=(
          'Prompt for the private key password associated with the BAK file '
          'with character echo disabled. The password is all typed characters '
          'up to but not including the RETURN or ENTER key.'))


def AddBakExportStripeCountArgument(parser):
  """Add the 'stripe_count' argument to the parser for striped export."""
  parser.add_argument('--stripe_count', type=int, default=None, help=(
      'Specifies the number of stripes to use for SQL Server exports.'))


def AddBakExportStripedArgument(parser, show_negated_in_help=True):
  """Add the 'striped' argument to the parser for striped export."""
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--striped',
      required=False,
      help='Whether SQL Server export should be striped.',
      **kwargs)


def AddBakImportStripedArgument(parser, show_negated_in_help=True):
  """Add the 'striped' argument to the parser for striped import."""
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--striped',
      required=False,
      help='Whether SQL Server import should be striped.',
      **kwargs)


def AddRescheduleType(parser):
  """Add the flag to specify reschedule type.

  Args:
    parser: The current argparse parser to add this to.
  """
  choices = [
      messages.Reschedule.RescheduleTypeValueValuesEnum.IMMEDIATE.name,
      messages.Reschedule.RescheduleTypeValueValuesEnum.NEXT_AVAILABLE_WINDOW
      .name,
      messages.Reschedule.RescheduleTypeValueValuesEnum.SPECIFIC_TIME.name,
  ]
  help_text = 'The type of reschedule operation to perform.'
  parser.add_argument(
      '--reschedule-type', choices=choices, required=True, help=help_text)


def AddScheduleTime(parser):
  """Add the flag for maintenance reschedule schedule time.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--schedule-time',
      type=arg_parsers.Datetime.Parse,
      help=('When specifying SPECIFIC_TIME, the date and time at which to '
            'schedule the maintenance in ISO 8601 format.'))


def AddBackupRunId(parser):
  """Add the flag for ID of backup run.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      'id',
      type=arg_parsers.BoundedInt(lower_bound=1, unlimited=True),
      help='The ID of the backup run. You can find the ID by running '
      '$ gcloud sql backups list -i {instance}.')


def AddPasswordPolicyMinLength(parser):
  """Add the flag to specify password policy min length.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--password-policy-min-length',
      type=int,
      required=False,
      default=None,
      help='Minimum number of characters allowed in the password.'
  )


def AddPasswordPolicyComplexity(parser):
  """Add the flag to specify password policy complexity.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--password-policy-complexity',
      choices={
          'COMPLEXITY_UNSPECIFIED':
              'The default value if COMPLEXITY_DEFAULT is not specified. It implies that complexity check is not enabled.',
          'COMPLEXITY_DEFAULT':
              'A combination of lowercase, uppercase, numeric, and non-alphanumeric characters.'
      },
      required=False,
      default=None,
      help='The complexity of the password. This flag is available only for PostgreSQL.'
  )


def AddPasswordPolicyReuseInterval(parser):
  """Add the flag to specify password policy reuse interval.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--password-policy-reuse-interval',
      type=arg_parsers.BoundedInt(lower_bound=0, upper_bound=100),
      required=False,
      default=None,
      help='Number of previous passwords that cannot be reused. The valid range is 0 to 100.'
  )


def AddPasswordPolicyDisallowUsernameSubstring(parser,
                                               show_negated_in_help=True):
  """Add the flag to specify password policy disallow username as substring.

  Args:
    parser: The current argparse parser to add this to.
    show_negated_in_help: Show nagative action in help.
  """
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--password-policy-disallow-username-substring',
      required=False,
      help='Disallow username as a part of the password.',
      **kwargs)


def AddPasswordPolicyPasswordChangeInterval(parser):
  """Add the flag to specify password policy password change interval.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--password-policy-password-change-interval',
      default=None,
      type=arg_parsers.Duration(lower_bound='1s'),
      required=False,
      help="""\
        Minimum interval after which the password can be changed, for example,
        2m for 2 minutes. See <a href="/sdk/gcloud/reference/topic/datetimes">
        $ gcloud topic datetimes</a> for information on duration formats.
        This flag is available only for PostgreSQL.
      """)


def AddPasswordPolicyEnablePasswordPolicy(parser, show_negated_in_help=False):
  """Add the flag to enable password policy.

  Args:
    parser: The current argparse parser to add this to.
    show_negated_in_help: Show nagative action in help.
  """
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--enable-password-policy',
      required=False,
      help="""\
        Enable the password policy, which enforces user password management with
        the policies configured for the instance. This flag is only available for Postgres.
      """,
      **kwargs)


def AddPasswordPolicyClearPasswordPolicy(parser, show_negated_in_help=False):
  """Add the flag to clear password policy.

  Args:
    parser: The current argparse parser to add this to.
    show_negated_in_help: Show nagative action in help.
  """
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--clear-password-policy',
      required=False,
      help='Clear the existing password policy. This flag is only available for Postgres.',
      **kwargs)


def AddPasswordPolicyAllowedFailedAttempts(parser):
  """Add the flag to set number of failed login attempts allowed before a user is locked.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--password-policy-allowed-failed-attempts',
      type=int,
      required=False,
      default=None,
      help='Number of failed login attempts allowed before a user is locked out. This flag is available only for MySQL.'
  )


def AddPasswordPolicyPasswordExpirationDuration(parser):
  """Add the flag to specify expiration duration after password is updated.

  Args:
    parser: The current argparse parser to add this to.
  """
  parser.add_argument(
      '--password-policy-password-expiration-duration',
      default=None,
      type=arg_parsers.Duration(lower_bound='1s'),
      required=False,
      help="""\
        Expiration duration after a password is updated, for example,
        2d for 2 days. See `gcloud topic datetimes` for information on
        duration formats. This flag is available only for MySQL.
      """)


def AddPasswordPolicyEnableFailedAttemptsCheck(parser,
                                               show_negated_in_help=True):
  """Add the flag to enable the failed login attempts check.

  Args:
    parser: The current argparse parser to add this to.
    show_negated_in_help: Show nagative action in help.
  """
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--password-policy-enable-failed-attempts-check',
      required=False,
      help='Enables the failed login attempts check if set to true. This flag is available only for MySQL.',
      **kwargs)


def AddPasswordPolicyEnablePasswordVerification(parser,
                                                show_negated_in_help=True):
  """Add the flag to specify password policy password verification.

  Args:
    parser: The current argparse parser to add this to.
    show_negated_in_help: Show nagative action in help.
  """
  kwargs = _GetKwargsForBoolFlag(show_negated_in_help)
  parser.add_argument(
      '--password-policy-enable-password-verification',
      required=False,
      help='The current password must be specified when altering the password. This flag is available only for MySQL.',
      **kwargs)


def AddUserRetainPassword(parser):
  """Will retain the old password when changing to the new password.

  Args:
    parser: The current argparse parser to add this to.
  """
  kwargs = _GetKwargsForBoolFlag(False)
  parser.add_argument(
      '--retain-password',
      required=False,
      help='Retain the old password when changing to the new password. Must set password with this flag. This flag is only available for MySQL 8.0.',
      **kwargs)


def AddUserDiscardDualPassword(parser):
  """Will discard the user's secondary password.

  Args:
    parser: The current argparse parser to add this to.
  """
  kwargs = _GetKwargsForBoolFlag(False)
  parser.add_argument(
      '--discard-dual-password',
      required=False,
      help='Discard the user\'s secondary password. Cannot set password and set this flag. This flag is only available for MySQL 8.0.',
      **kwargs)


def AddSqlServerTimeZone(parser):
  """Adds the `--time-zone` flag to the parser."""
  parser.add_argument(
      '--time-zone',
      required=False,
      help=(
          'Set a non-default time zone. '
          'Only available for SQL Server instances.'
          ))


def AddThreadsPerCore(parser):
  """Adds the `--threads-per-core` flag to the parser."""
  parser.add_argument(
      '--threads-per-core',
      type=int,
      hidden=True,
      required=False,
      help=(
          'Set a non-default number of threads per core. '
          'Only available for SQL Server instances.'
          ))

INSTANCES_USERLABELS_FORMAT = ':(settings.userLabels:alias=labels:label=LABELS)'

INSTANCES_FORMAT_COLUMNS = [
    'name', 'databaseVersion', 'firstof(gceZone,region):label=LOCATION',
    'settings.tier',
    'ip_addresses.filter("type:PRIMARY").*extract(ip_address).flatten()'
    '.yesno(no="-"):label=PRIMARY_ADDRESS',
    'ip_addresses.filter("type:PRIVATE").*extract(ip_address).flatten()'
    '.yesno(no="-"):label=PRIVATE_ADDRESS', 'state:label=STATUS'
]


def GetInstanceListFormat():
  """Returns the table format for listing instances."""
  table_format = '{} table({})'.format(INSTANCES_USERLABELS_FORMAT,
                                       ','.join(INSTANCES_FORMAT_COLUMNS))
  return table_format


OPERATION_FORMAT = """
  table(
    operation,
    operationType:label=TYPE,
    startTime.iso():label=START,
    endTime.iso():label=END,
    error.errors[0].code.yesno(no="-"):label=ERROR,
    state:label=STATUS
  )
"""

OPERATION_FORMAT_BETA = """
  table(
    name,
    operationType:label=TYPE,
    startTime.iso():label=START,
    endTime.iso():label=END,
    error.errors[0].code.yesno(no="-"):label=ERROR,
    status:label=STATUS
  )
"""

CLIENT_CERTS_FORMAT = """
  table(
    commonName:label=NAME,
    sha1Fingerprint,
    expirationTime.yesno(no="-"):label=EXPIRATION
  )
"""

SERVER_CA_CERTS_FORMAT = """
  table(
    sha1Fingerprint,
    expirationTime.yesno(no="-"):label=EXPIRATION
  )
"""

TIERS_FORMAT = """
  table(
    tier,
    region.list():label=AVAILABLE_REGIONS,
    RAM.size(),
    DiskQuota.size():label=DISK
  )
"""


def AddActiveDirectoryDomain(parser):
  """Adds the '--active-directory-domain' flag to the parser.

  Args:
    parser: The current argparse parser to add this to.
  """
  help_text = (
      'Managed Service for Microsoft Active Directory domain this instance is '
      'joined to. Only available for SQL Server instances.')
  parser.add_argument('--active-directory-domain', help=help_text)


def AddDeletionProtection(parser):
  """Adds the '--deletion-protection' flag to the parser for instances patch action.

  Args:
    parser: The current argparse parser to add this to.
  """
  help_text = (
      'Enable deletion protection on a Cloud SQL instance.')
  parser.add_argument(
      '--deletion-protection',
      action=arg_parsers.StoreTrueFalseAction,
      help=help_text)


def AddConnectorEnforcement(parser):
  """Adds the '--connector-enforcement' flag to the parser.

  Args:
    parser: The current argparse parser to add this to.
  """
  help_text = (
      'Cloud SQL Connector enforcement mode. It determines how Cloud SQL '
      'Connectors are used in the connection. See the list of modes '
      '[here](https://cloud.google.com/sql/docs/mysql/admin-api/rest/v1beta4/instances#connectorenforcement).'
  )
  parser.add_argument(
      '--connector-enforcement',
      choices={
          'CONNECTOR_ENFORCEMENT_UNSPECIFIED':
              'The requirement for Cloud SQL connectors is unknown.',
          'NOT_REQUIRED':
              'Does not require Cloud SQL connectors.',
          'REQUIRED':
              ('Requires all connections to use Cloud SQL connectors, '
               'including the Cloud SQL Auth Proxy and Cloud SQL Java, Python, '
               'and Go connectors. Note: This disables all existing authorized '
               'networks.')
      },
      required=False,
      default=None,
      help=help_text)


def AddTimeout(
    parser,
    default_max_wait,
    help_text='Time to synchronously wait for the operation to complete, after'
              ' which the operation continues asynchronously. Ignored if '
              '--async flag is specified. By default, set to 3600s. To wait '
              'indefinitely, set to *unlimited*.'):
  """Adds --timeout flag."""
  parser.add_argument(
      '--timeout',
      required=False,
      default=default_max_wait,
      help=help_text,
      type=arg_parsers.BoundedInt(lower_bound=0, unlimited=True))


def AddEnablePrivateServiceConnect(parser):
  kwargs = _GetKwargsForBoolFlag(False)
  parser.add_argument(
      '--enable-private-service-connect',
      hidden=True,
      required=False,
      help=('When the flag is set, a Cloud SQL instance will be created with '
            'PSC enabled.'),
      **kwargs)


def AddAllowedPscProjects(parser):
  parser.add_argument(
      '--allowed-psc-projects',
      type=arg_parsers.ArgList(min_length=1),
      required=False,
      hidden=True,
      metavar='PROJECT',
      help=('A comma-separated list of projects. Each project in this list may '
            'be represented by a project number (numeric) or by a project id '
            '(alphanumeric). This will allow certain projects to create PSC '
            'bindings to the instance. This can be set only after PSC is '
            'enabled.'))


def AddClearAllowedPscProjects(parser):
  kwargs = _GetKwargsForBoolFlag(False)
  parser.add_argument(
      '--clear-allowed-psc-projects',
      hidden=True,
      required=False,
      help=('This will clear the project allowlist of PSC, disallowing all '
            'projects from creating new PSC bindings to the instance.'),
      **kwargs)


def AddRecreateReplicasOnPrimaryCrash(parser):
  """Adds --recreate-replicas-on-primary-crash flag."""
  parser.add_argument(
      '--recreate-replicas-on-primary-crash',
      hidden=True,
      required=False,
      help=('Enable/Disable replica recreation when a primary MySQL instance '
            'operating in reduced durability mode with either or both of '
            '`innodb_flush_log_at_trx_commit` and `sync_binlog` flags set to '
            'non-default values. Not recreating the replicas might lead to '
            'data inconsistencies between the primary and the replicas. '),
      action=arg_parsers.StoreTrueFalseAction)
