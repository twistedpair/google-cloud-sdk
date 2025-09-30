# -*- coding: utf-8 -*- #
# Copyright 2016 Google LLC. All Rights Reserved.
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
"""Provides common arguments for the Spanner command surface."""

from argcomplete.completers import FilesCompleter
from cloudsdk.google.protobuf import descriptor_pb2
from googlecloudsdk.api_lib.spanner import databases
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as c_exceptions
from googlecloudsdk.command_lib.spanner import ddl_parser
from googlecloudsdk.command_lib.spanner import split_file_parser
from googlecloudsdk.command_lib.util import completers
from googlecloudsdk.core.util import files


class BackupCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(BackupCompleter, self).__init__(
        collection='spanner.projects.instances.backups',
        list_command='spanner backups list --uri',
        flags=['instance'],
        **kwargs)


class BackupScheduleCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(BackupScheduleCompleter, self).__init__(
        collection='spanner.projects.instances.databases.backupSchedules',
        list_command='spanner backup-schedules list --uri',
        flags=['database', 'instance'],
        **kwargs
    )


class DatabaseCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(DatabaseCompleter, self).__init__(
        collection='spanner.projects.instances.databases',
        list_command='spanner databases list --uri',
        flags=['instance'],
        **kwargs)


class DatabaseOperationCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(DatabaseOperationCompleter, self).__init__(
        collection='spanner.projects.instances.databases.operations',
        list_command='spanner operations list --uri',
        flags=['instance'],
        **kwargs)


class InstanceCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(InstanceCompleter, self).__init__(
        collection='spanner.projects.instances',
        list_command='spanner instances list --uri',
        **kwargs)


class InstancePartitionCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(InstancePartitionCompleter, self).__init__(
        collection='spanner.projects.instances.instancePartitions',
        list_command='alpha spanner instance-partitions list --uri',
        **kwargs
    )


class InstanceConfigCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(InstanceConfigCompleter, self).__init__(
        collection='spanner.projects.instanceConfigs',
        list_command='spanner instance-configs list --uri',
        **kwargs)


class OperationCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(OperationCompleter, self).__init__(
        collection='spanner.projects.instances.operations',
        list_command='spanner operations list --uri',
        flags=['instance'],
        **kwargs)


class DatabaseSessionCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(DatabaseSessionCompleter, self).__init__(
        collection='spanner.projects.instances.databases.sessions',
        list_command='spanner databases sessions list --uri',
        flags=['database', 'instance'],
        **kwargs)


class DatabaseRoleCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(DatabaseRoleCompleter, self).__init__(
        collection='spanner.projects.instances.databases.roles',
        list_command='beta spanner databases roles list --uri',
        flags=['database', 'instance'],
        **kwargs)


def Database(positional=True, required=True, text='Cloud Spanner database ID.'):
  if positional:
    return base.Argument('database', completer=DatabaseCompleter, help=text)
  else:
    return base.Argument(
        '--database', required=required, completer=DatabaseCompleter, help=text)


def Backup(positional=True, required=True, text='Cloud Spanner backup ID.'):
  if positional:
    return base.Argument('backup', completer=BackupCompleter, help=text)
  else:
    return base.Argument(
        '--backup', required=required, completer=BackupCompleter, help=text)


def Ddl(help_text=''):
  return base.Argument(
      '--ddl',
      action='append',
      required=False,
      help=help_text,
  )


def DdlFile(help_text):
  return base.Argument(
      '--ddl-file',
      required=False,
      completer=FilesCompleter,
      help=help_text,
  )


def ProtoDescriptorsFile(help_text):
  return base.Argument(
      '--proto-descriptors-file',
      required=False,
      completer=FilesCompleter,
      help=help_text,
  )


def DatabaseDialect(help_text):
  return base.Argument(
      '--database-dialect',
      required=False,
      choices=[
          databases.DATABASE_DIALECT_POSTGRESQL,
          databases.DATABASE_DIALECT_GOOGLESQL
      ],
      help=help_text,
  )


def IncludeProtoDescriptors(help_text):
  return base.Argument(
      '--include-proto-descriptors',
      action='store_true',
      help=help_text,
      default=False,
  )


def GetDDLsFromArgs(args):
  if args.ddl_file:
    return [files.ReadFileContents(args.ddl_file)]
  return args.ddl or []


def SplitDdlIntoStatements(args):
  """Break DDL statements on semicolon while preserving string literals."""
  ddls = GetDDLsFromArgs(args)
  statements = []
  for x in ddls:
    if hasattr(args, 'database_dialect'
              ) and args.database_dialect and args.database_dialect.upper(
              ) == databases.DATABASE_DIALECT_POSTGRESQL:
      # Split the ddl string by semi-colon and remove empty string to avoid
      # adding a PG ddl parser.
      # TODO(b/195711543): This would be incorrect if ';' is inside strings
      # and / or comments.
      statements.extend([stmt for stmt in x.split(';') if stmt])
    else:
      statements.extend(ddl_parser.PreprocessDDLWithParser(x))
  return statements


def GetProtoDescriptors(args):
  if args.proto_descriptors_file:
    proto_desc_content = files.ReadBinaryFileContents(
        args.proto_descriptors_file)
    descriptor_pb2.FileDescriptorSet.FromString(proto_desc_content)
    return proto_desc_content
  return None


def Config(
    required=True,
    text=(
        'Instance configuration defines the geographic placement and'
        ' replication of the databases in that instance. Available'
        ' configurations can be found by running "gcloud spanner'
        ' instance-configs list"'
    ),
):
  return base.Argument(
      '--config',
      completer=InstanceConfigCompleter,
      required=required,
      help=text,
  )


def Description(required=True, text='Description of the instance.'):
  return base.Argument('--description', required=required, help=text)


def Instance(positional=True, text='Cloud Spanner instance ID.'):
  if positional:
    return base.Argument('instance', completer=InstanceCompleter, help=text)
  else:
    return base.Argument(
        '--instance', required=True, completer=InstanceCompleter, help=text)


def InstancePartition(
    positional=True,
    required=True,
    hidden=True,
    text='Cloud Spanner instance partition ID.',
):
  """Initialize an instance partition flag.

  Args:
    positional: bool. If true, then it's a positional flag.
    required: bool. If true, then this flag is required.
    hidden: bool. If true, then this flag is hidden.
    text: helper test.

  Returns:
  """
  if positional:
    return base.Argument(
        'instance_partition',
        completer=InstancePartitionCompleter,
        hidden=hidden,
        help=text,
    )
  else:
    return base.Argument(
        '--instance-partition', required=required, hidden=hidden, help=text
    )


def Nodes(required=False, text='Number of nodes for the instance.'):
  return base.Argument(
      '--nodes',
      required=required,
      type=int,
      help=text,
  )


def AddTags(parser):
  """Makes the base.Argument for --tags flag."""
  help_parts = [
      'List of tags KEY=VALUE pairs to bind.',
      'Each item must be expressed as either',
      'ID: `<tag-key-id>=<tag-value-id>` or\n',
      'Namespaced name: `<tag-key-namespaced-name>=<tag-value-short-name>`.\n',
      'Example: `tagKeys/123=tagValues/223`\n',
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
  tags = getattr(args, tags_arg_name, None)
  if not tags:
    return None
  # Sorted for test stability
  return tags_message(
      additionalProperties=[
          tags_message.AdditionalProperty(key=key, value=value)
          for key, value in sorted(tags.items())
      ]
  )


def ProcessingUnits(
    required=False, text='Number of processing units for the instance.'
):
  return base.Argument(
      '--processing-units', required=required, type=int, help=text
  )


def AutoscalingMaxNodes(required=False):
  return base.Argument(
      '--autoscaling-max-nodes',
      required=required,
      type=int,
      help='Maximum number of nodes for the autoscaled instance.',
  )


def AutoscalingMinNodes(required=False):
  return base.Argument(
      '--autoscaling-min-nodes',
      required=required,
      type=int,
      help='Minimum number of nodes for the autoscaled instance.',
  )


def AutoscalingMaxProcessingUnits(required=False):
  return base.Argument(
      '--autoscaling-max-processing-units',
      required=required,
      type=int,
      help='Maximum number of processing units for the autoscaled instance.',
  )


def AutoscalingMinProcessingUnits(required=False):
  return base.Argument(
      '--autoscaling-min-processing-units',
      required=required,
      type=int,
      help='Minimum number of processing units for the autoscaled instance.',
  )


def AutoscalingHighPriorityCpuTarget(required=False, hidden=False):
  return base.Argument(
      '--autoscaling-high-priority-cpu-target',
      required=required,
      hidden=hidden,
      type=int,
      help=(
          'Specifies the target percentage of high-priority CPU the autoscaled'
          ' instance can utilize.'
      ),
  )


def AutoscalingTotalCpuTarget(required=False, hidden=True):
  return base.Argument(
      '--autoscaling-total-cpu-target',
      required=required,
      hidden=hidden,
      type=int,
      help=(
          'Specifies the target percentage of total CPU the autoscaled instance'
          ' can utilize.'
      ),
  )


def AutoscalingStorageTarget(required=False):
  return base.Argument(
      '--autoscaling-storage-target',
      required=required,
      type=int,
      help=(
          'Specifies the target percentage of storage the autoscaled instance'
          ' can utilize.'
      ),
  )


def DisableHighPriorityCpuAutoscaling(required=False, hidden=True):
  return base.Argument(
      '--disable-high-priority-cpu-autoscaling',
      required=required,
      hidden=hidden,
      type=bool,
      help=(
          'Set the flag to disable high priority CPU autoscaling on the '
          'replica.'
      ),
  )


def DisableTotalCpuAutoscaling(required=False, hidden=True):
  return base.Argument(
      '--disable-total-cpu-autoscaling',
      required=required,
      hidden=hidden,
      type=bool,
      help='Set the flag to disable total CPU autoscaling on the replica.',
  )


def DisableDownScaling(required=False, hidden=True):
  return base.Argument(
      '--disable-downscaling',
      required=required,
      hidden=hidden,
      action=arg_parsers.StoreTrueFalseAction,
      help='Set the flag to disable downscaling for the autoscaled instance.',
  )


def AsymmetricAutoscalingOptionFlag(
    include_total_cpu_target=False, include_disable_autoscaling_args=False
):
  """Adds the --asymmetric-autoscaling-option flag.

  Args:
    include_total_cpu_target: bool. If True, include 'total_cpu_target' in the
      ArgDict spec.
    include_disable_autoscaling_args: bool. If True, include
      'disable_high_priority_cpu_autoscaling' and
      'disable_total_cpu_autoscaling' in the ArgDict spec.

  Returns:
    A base.Argument for the --asymmetric-autoscaling-option flag.
  """
  help_text = 'Specifies the asymmetric autoscaling option for the instance. '
  spec = {
            'location': str,
            'min_nodes': int,
            'max_nodes': int,
            'min_processing_units': int,
            'max_processing_units': int,
            'high_priority_cpu_target': int,
  }
  if include_total_cpu_target:
    spec['total_cpu_target'] = int
  if include_disable_autoscaling_args:
    spec['disable_high_priority_cpu_autoscaling'] = arg_parsers.ArgBoolean()
    spec['disable_total_cpu_autoscaling'] = arg_parsers.ArgBoolean()

  return base.Argument(
      '--asymmetric-autoscaling-option',
      type=arg_parsers.ArgDict(
          spec=spec,
          required_keys=['location'],
      ),
      required=False,
      action='append',
      help=help_text,
  )


def ClearAsymmetricAutoscalingOptionsFlag():
  return base.Argument(
      '--clear-asymmetric-autoscaling-option',
      type=arg_parsers.ArgList(min_length=1),
      metavar='LOCATION',
      required=False,
      help=(
          'Specify a comma separated list of locations from which to remove'
          ' asymmetric autoscaling options'
      ),
  )


def SsdCache(
    positional=False,
    required=False,
    hidden=True,
    text='Cloud Spanner SSD Cache ID.',
):
  if positional:
    return base.Argument('cache_id', hidden=hidden, help=text)
  else:
    return base.Argument(
        '--ssd-cache', required=required, hidden=hidden, help=text
    )


def GetEditionHelpText(update=False):
  """Returns the help text for the edition flag."""
  if update:
    return (
        'Spanner edition. You can upgrade your Standard edition instance to the'
        ' `ENTERPRISE` edition or `ENTERPRISE_PLUS` edition. You can also'
        ' upgrade your Enterprise edition instance to the `ENTERPRISE_PLUS`'
        ' edition. You can downgrade your `ENTERPRISE_PLUS` edition instance to'
        ' the `ENTERPRISE` or `STANDARD` edition. You can also downgrade your'
        ' `ENTERPRISE` edition instance to the `STANDARD` edition. You must'
        ' stop using the higher-tier edition features in order to downgrade.'
        ' Otherwise, downgrade fails. For more information, see [Spanner'
        ' editions'
        ' overview](https://cloud.google.com/spanner/docs/editions-overview).'
    )
  return 'Spanner edition.'


def Edition(
    choices=None,
    update=False,
    required=False,
):
  return base.Argument(
      '--edition',
      required=required,
      help=GetEditionHelpText(update),
      choices=choices,
  )


def DefaultBackupScheduleType(
    choices=None,
    required=False,
    text='The default backup schedule type that is used in the instance.',
):
  return base.Argument(
      '--default-backup-schedule-type',
      required=required,
      help=text,
      choices=choices,
  )


def SplitsFile(help_text):
  return base.Argument(
      '--splits-file',
      required=True,
      completer=FilesCompleter,
      help=help_text,
  )


def SplitExpirationDate(help_text):
  return base.Argument(
      '--split-expiration-date',
      required=False,
      help=help_text,
  )


def Initiator(help_text):
  return base.Argument(
      '--initiator',
      required=False,
      help=help_text,
  )


def AddCapacityArgsForInstance(
    require_all_autoscaling_args,
    parser,
    add_asymmetric_option_flag=False,
    asymmetric_options_group=False,
    autoscaling_cpu_target_group=False,
    add_asymmetric_total_cpu_target_flag=False,
    add_asymmetric_disable_autoscaling_flags=False,
    add_disable_downscaling_flag=False,
):
  """Parse the instance capacity arguments, including manual and autoscaling.

  Args:
    require_all_autoscaling_args: bool. If True, a complete autoscaling config
      is required.
    parser: the argparse parser for the command.
    add_asymmetric_option_flag: bool. If True, add the asymmetric autoscaling
      option flag.
    asymmetric_options_group: bool. If True, add the asymmetric autoscaling
      options group.
    autoscaling_cpu_target_group: bool. If True, add the autoscaling cpu target
      group.
    add_asymmetric_total_cpu_target_flag: bool. If True, add the asymmetric
      total cpu target flag.
    add_asymmetric_disable_autoscaling_flags: bool. If True, add the asymmetric
      disable autoscaling flags.
    add_disable_downscaling_flag: bool. If True, add the disable downscaling
      flag.
  """
  capacity_parser = parser.add_argument_group(mutex=True, required=False)

  # Manual scaling.
  Nodes().AddToParser(capacity_parser)
  ProcessingUnits().AddToParser(capacity_parser)

  # Autoscaling.
  autoscaling_config_group_parser = capacity_parser.add_argument_group(
      help='Autoscaling'
  )
  if autoscaling_cpu_target_group:
    # TODO(b/424254143): Add help text for the cpu target options group "Specify
    # both or only one of the CPU targets:"
    cpu_target_options_group_parser = (
        autoscaling_config_group_parser.add_argument_group(
            required=require_all_autoscaling_args,
            help='',
        )
    )
    AutoscalingHighPriorityCpuTarget(
        required=False
    ).AddToParser(cpu_target_options_group_parser)
    AutoscalingTotalCpuTarget(
        required=False, hidden=True
    ).AddToParser(cpu_target_options_group_parser)
  else:
    AutoscalingHighPriorityCpuTarget(
        required=require_all_autoscaling_args
    ).AddToParser(autoscaling_config_group_parser)

  if add_disable_downscaling_flag:
    DisableDownScaling(
        required=False, hidden=True
    ).AddToParser(autoscaling_config_group_parser)

  AutoscalingStorageTarget(
      required=require_all_autoscaling_args
    ).AddToParser(autoscaling_config_group_parser)

  autoscaling_limits_group_parser = autoscaling_config_group_parser.add_argument_group(
      mutex=True,
      required=require_all_autoscaling_args,
      help=(
          'Autoscaling limits can be defined in either nodes or processing'
          ' units.'
      ),
  )
  autoscaling_node_limits_group_parser = (
      autoscaling_limits_group_parser.add_argument_group(
          help='Autoscaling limits in nodes:'
      )
  )
  AutoscalingMinNodes(required=require_all_autoscaling_args).AddToParser(
      autoscaling_node_limits_group_parser
  )
  AutoscalingMaxNodes(required=require_all_autoscaling_args).AddToParser(
      autoscaling_node_limits_group_parser
  )
  autoscaling_pu_limits_group_parser = (
      autoscaling_limits_group_parser.add_argument_group(
          help='Autoscaling limits in processing units:'
      )
  )
  AutoscalingMinProcessingUnits(
      required=require_all_autoscaling_args
  ).AddToParser(autoscaling_pu_limits_group_parser)
  AutoscalingMaxProcessingUnits(
      required=require_all_autoscaling_args
  ).AddToParser(autoscaling_pu_limits_group_parser)
  # Asymmetric autoscaling augument structure is different between create and
  # update commands.
  if add_asymmetric_option_flag:
    if asymmetric_options_group:
      asymmetric_options_group_parser = (
          autoscaling_config_group_parser.add_argument_group(
              mutex=True
          )
      )
      AsymmetricAutoscalingOptionFlag(
          add_asymmetric_total_cpu_target_flag,
          add_asymmetric_disable_autoscaling_flags
      ).AddToParser(asymmetric_options_group_parser)
      ClearAsymmetricAutoscalingOptionsFlag().AddToParser(
          asymmetric_options_group_parser
      )
    else:
      AsymmetricAutoscalingOptionFlag(
          include_total_cpu_target=add_asymmetric_total_cpu_target_flag,
          include_disable_autoscaling_args=add_asymmetric_disable_autoscaling_flags,
      ).AddToParser(parser=autoscaling_config_group_parser)


def AddCapacityArgsForInstancePartition(
    parser,
    add_autoscaling_args=True,
    autoscaling_args_hidden=False,
    require_all_autoscaling_args=True,
):
  """Parse the instance partition capacity arguments.

  Args:
    parser: the argparse parser for the command.
    add_autoscaling_args: bool. If True, add the autoscaling arguments. This is
      required because these arguments are only available in the ALPHA track.
      This will be removed once the arguments are promoted to BETA and GA.
    autoscaling_args_hidden: bool. If True, mark the autoscaling arguments as
      hidden. This will be removed once the arguments are promoted to BETA and
      GA.
    require_all_autoscaling_args: bool. If True, a complete autoscaling config
      is required. This is required during instance partition creation, but not
      during instance partition update.
  """
  capacity_parser = parser.add_argument_group(mutex=True, required=False)

  # Manual scaling.
  Nodes(text='Number of nodes for the instance partition.').AddToParser(
      capacity_parser
  )
  ProcessingUnits(
      text='Number of processing units for the instance partition.'
  ).AddToParser(capacity_parser)

  # TODO(b/434234543): Remove this check once the autoscaling arguments are
  # promoted to BETA and GA.
  if not add_autoscaling_args:
    return

  # Autoscaling.
  autoscaling_config_group_parser = capacity_parser.add_argument_group(
      help='Autoscaling',
      hidden=autoscaling_args_hidden,
  )
  cpu_target_options_group_parser = (
      autoscaling_config_group_parser.add_argument_group(
          required=require_all_autoscaling_args,
          help='Target for high priority CPU utilization.',
      )
  )
  AutoscalingHighPriorityCpuTarget(
      required=False,
      hidden=autoscaling_args_hidden,
  ).AddToParser(cpu_target_options_group_parser)
  AutoscalingTotalCpuTarget(
      required=False,
      hidden=autoscaling_args_hidden,
  ).AddToParser(cpu_target_options_group_parser)
  AutoscalingStorageTarget(required=require_all_autoscaling_args).AddToParser(
      autoscaling_config_group_parser
  )
  autoscaling_limits_group_parser = autoscaling_config_group_parser.add_argument_group(
      mutex=True,
      required=require_all_autoscaling_args,
      help=(
          'Autoscaling limits can be defined in either nodes or processing'
          ' units.'
      ),
  )
  autoscaling_node_limits_group_parser = (
      autoscaling_limits_group_parser.add_argument_group(
          help='Autoscaling limits in nodes:'
      )
  )
  AutoscalingMinNodes(required=require_all_autoscaling_args).AddToParser(
      autoscaling_node_limits_group_parser
  )
  AutoscalingMaxNodes(required=require_all_autoscaling_args).AddToParser(
      autoscaling_node_limits_group_parser
  )
  autoscaling_pu_limits_group_parser = (
      autoscaling_limits_group_parser.add_argument_group(
          help='Autoscaling limits in processing units:'
      )
  )
  AutoscalingMinProcessingUnits(
      required=require_all_autoscaling_args
  ).AddToParser(autoscaling_pu_limits_group_parser)
  AutoscalingMaxProcessingUnits(
      required=require_all_autoscaling_args
  ).AddToParser(autoscaling_pu_limits_group_parser)


def TargetConfig(required=True):
  return base.Argument(
      '--target-config',
      completer=InstanceConfigCompleter,
      required=required,
      help='Target Instance configuration to move the instances.')


def EnableDropProtection(required=False):
  return base.Argument(
      '--enable-drop-protection',
      required=required,
      dest='enable_drop_protection',
      action=arg_parsers.StoreTrueFalseAction,
      help='Enable database deletion protection on this database.',
  )


def EnableUpdateKmsKeys(required=False):
  return base.Argument(
      '--kms-keys',
      required=required,
      metavar='KMS_KEY',
      action=arg_parsers.StoreOnceAction,
      dest='kms_keys',
      type=arg_parsers.ArgList(min_length=1),
      help=(
          'Update KMS key references for this database. Users should always'
          ' provide the full set of required KMS key references.'
      ),
  )


def OperationId(database=False):
  return base.Argument(
      'operation',
      metavar='OPERATION-ID',
      completer=DatabaseOperationCompleter if database else OperationCompleter,
      help='ID of the operation')


def Session(positional=True, required=True, text='Cloud Spanner session ID'):
  if positional:
    return base.Argument(
        'session', completer=DatabaseSessionCompleter, help=text)

  else:
    return base.Argument(
        '--session',
        required=required,
        completer=DatabaseSessionCompleter,
        help=text)


def ReplicaFlag(parser, name, text, required=True):
  return parser.add_argument(
      name,
      required=required,
      metavar='location=LOCATION,type=TYPE',
      action='store',
      type=arg_parsers.ArgList(
          custom_delim_char=':',
          min_length=1,
          element_type=arg_parsers.ArgDict(
              spec={
                  'location': str,
                  'type': str
              },
              required_keys=['location', 'type']),
      ),
      help=text)


def _TransformOperationDone(resource):
  """Combines done and throttled fields into a single column."""
  done_cell = '{0}'.format(resource.get('done', False))
  if resource.get('metadata', {}).get('throttled', False):
    done_cell += ' (throttled)'
  return done_cell


def _TransformOperationEndTime(resource):
  """Combines endTime and progressPercent into a single column."""
  metadata = resource.get('metadata')
  base_type = 'type.googleapis.com/google.spanner.admin.database.v1.{}'
  op_type = metadata.get('@type')

  if op_type == base_type.format(
      'RestoreDatabaseMetadata'
  ) or op_type == base_type.format('OptimizeRestoredDatabaseMetadata'):
    progress = metadata.get('progress')
    if progress is None:
      return None
    progress_end_time = progress.get('endTime')
    progress_percent = progress.get('progressPercent')
    if progress_end_time is None and progress_percent is not None:
      return progress_percent + '%'
    return progress_end_time
  else:
    return None


def _TransformDatabaseId(resource):
  """Gets database ID depending on operation type."""
  metadata = resource.get('metadata')
  base_type = 'type.googleapis.com/google.spanner.admin.database.v1.{}'
  op_type = metadata.get('@type')

  if op_type == base_type.format(
      'RestoreDatabaseMetadata') or op_type == base_type.format(
          'OptimizeRestoredDatabaseMetadata'):
    return metadata.get('name')
  return metadata.get('database')


def AddCommonListArgs(parser, additional_choices=None):
  """Add Common flags for the List operation group."""
  mutex_group = parser.add_group(mutex=True, required=True)
  mutex_group.add_argument(
      '--instance-config',
      completer=InstanceConfigCompleter,
      help='The ID of the instance configuration the operation is executing on.'
  )
  mutex_group.add_argument(
      '--instance',
      completer=InstanceCompleter,
      help='The ID of the instance the operation is executing on.')
  Database(
      positional=False,
      required=False,
      text='For database operations, the name of the database '
      'the operations are executing on.').AddToParser(parser)
  Backup(
      positional=False,
      required=False,
      text='For backup operations, the name of the backup '
      'the operations are executing on.').AddToParser(parser)
  InstancePartition(
      positional=False,
      required=False,
      hidden=False,
      text=(
          'For instance partition operations, the name of the instance '
          'partition the operation is executing on.'
      ),
  ).AddToParser(parser)

  type_choices = {
      'INSTANCE': (
          'Returns instance operations for the given instance. '
          'Note, type=INSTANCE does not work with --database or --backup.'
      ),
      'DATABASE': (
          'If only the instance is specified (--instance), returns all '
          'database operations associated with the databases in the '
          'instance. When a database is specified (--database), the command '
          'would return database operations for the given database.'
      ),
      'BACKUP': (
          'If only the instance is specified (--instance), returns all '
          'backup operations associated with backups in the instance. When '
          'a backup is specified (--backup), only the backup operations for '
          'the given backup are returned.'
      ),
      'INSTANCE_PARTITION': (
          'If only the instance is specified (--instance), returns all '
          'instance partition operations associated with instance partitions '
          'in the instance. When an instance partition is specified '
          '(--instance-partition), only the instance partition operations '
          'for the given instance partition are returned. '
      ),
      'DATABASE_RESTORE': (
          'Database restore operations are returned for all databases in '
          'the given instance (--instance only) or only those associated '
          'with the given database (--database)'
      ),
      'DATABASE_CHANGE_QUORUM': (
          'Database change quorum operations are returned for all databases '
          'in the given instance (--instance only) or only those associated '
          'with the given database (--database).'
      ),
      'DATABASE_CREATE': (
          'Database create operations are returned for all databases in '
          'the given instance (--instance only) or only those associated '
          'with the given database (--database)'
      ),
      'DATABASE_UPDATE_DDL': (
          'Database update DDL operations are returned for all databases in '
          'the given instance (--instance only) or only those associated '
          'with the given database (--database)'
      ),
      'INSTANCE_CONFIG_CREATE': (
          'Instance configuration create operations are returned for the '
          'given instance configuration (--instance-config).'
      ),
      'INSTANCE_CONFIG_UPDATE': (
          'Instance configuration update operations are returned for the '
          'given instance configuration (--instance-config).'
      ),
  }

  if additional_choices is not None:
    type_choices.update(additional_choices)

  parser.add_argument(
      '--type',
      default='',
      type=lambda x: x.upper(),
      choices=type_choices,
      help='(optional) List only the operations of the given type.')

  parser.display_info.AddFormat("""
          table(
            name.basename():label=OPERATION_ID,
            metadata.statements.join(sep="\n"),
            done():label=DONE,
            metadata.'@type'.split('.').slice(-1:).join()
          )
        """)
  parser.display_info.AddCacheUpdater(None)
  parser.display_info.AddTransforms({'done': _TransformOperationDone})
  parser.display_info.AddTransforms({'database': _TransformDatabaseId})
  parser.display_info.AddTransforms({'endtime': _TransformOperationEndTime})


def AddCommonDescribeArgs(parser):
  """Adds common args to describe operations parsers shared across all stages.

  The common arguments are Database, Backup and OperationId.

  Args:
    parser: argparse.ArgumentParser to register arguments with.
  """
  # TODO(b/215646847): Remove Common args function, after instance-config flag
  # is present in all (GA/Beta/Alpha) stages. Currently, it is only present in
  # the Alpha stage.
  Database(
      positional=False,
      required=False,
      text='For a database operation, the name of the database '
      'the operation is executing on.').AddToParser(parser)
  Backup(
      positional=False,
      required=False,
      text=(
          'For a backup operation, the name of the backup '
          'the operation is executing on.'
      ),
  ).AddToParser(parser)
  InstancePartition(
      positional=False,
      required=False,
      hidden=False,
      text=(
          'For an instance partition operation, the name of the instance '
          'partition the operation is executing on.'
      ),
  ).AddToParser(parser)
  OperationId().AddToParser(parser)


def AddCommonCancelArgs(parser):
  """Adds common args to cancel operations parsers shared across all stages.

  The common arguments are Database, Backup and OperationId.

  Args:
    parser: argparse.ArgumentParser to register arguments with.
  """
  # TODO(b/215646847): Remove Common args function, after instance-config flag
  # is present in all (GA/Beta/Alpha) stages. Currently, it is only present in
  # the Alpha stage.
  Database(
      positional=False,
      required=False,
      text='For a database operation, the name of the database '
      'the operation is executing on.').AddToParser(parser)
  Backup(
      positional=False,
      required=False,
      text='For a backup operation, the name of the backup '
      'the operation is executing on.').AddToParser(parser)
  InstancePartition(
      positional=False,
      required=False,
      hidden=False,
      text=(
          'For an instance partition operation, the name of the instance '
          'partition the operation is executing on.'
      ),
  ).AddToParser(parser)
  OperationId().AddToParser(parser)


def DatabaseRole():
  return base.Argument(
      '--database-role',
      required=False,
      completer=DatabaseRoleCompleter,
      help='Cloud Spanner database role to assume for this request.',
  )


def GetSpannerMigrationSourceFlag():
  return base.Argument(
      '--source',
      required=True,
      help=(
          'Flag for specifying source database (e.g., PostgreSQL, MySQL,'
          ' DynamoDB).'
      ),
  )


def GetSpannerMigrationPrefixFlag():
  return base.Argument('--prefix', help='File prefix for generated files.')


def GetSpannerMigrationSourceProfileFlag():
  return base.Argument(
      '--source-profile',
      help=(
          'Flag for specifying connection profile for source database (e.g.,'
          ' "file=<path>,format=dump").'
      ),
  )


def GetSpannerMigrationTargetFlag():
  return base.Argument(
      '--target',
      help=(
          'Specifies the target database, defaults to Spanner '
          '(accepted values: Spanner) (default "Spanner").'
      ),
  )


def GetSpannerMigrationTargetProfileFlag():
  return base.Argument(
      '--target-profile',
      required=True,
      help=(
          'Flag for specifying connection profile for target database '
          '(e.g., "dialect=postgresql)".'
      ),
  )


def GetSpannerMigrationSessionFlag():
  return base.Argument(
      '--session',
      required=True,
      help='Specifies the file that you restore session state from.',
  )


def GetSpannerMigrationSkipForeignKeysFlag():
  return base.Argument(
      '--skip-foreign-keys',
      action='store_true',
      help='Skip creating foreign keys after data migration is complete.',
  )


def GetSpannerMigrationWriteLimitFlag():
  return base.Argument(
      '--write-limit',
      help=(
          'Number of parallel writers to Cloud Spanner during bulk data'
          ' migrations (default 40).'
      ),
  )


def GetSpannerMigrationDryRunFlag():
  return base.Argument(
      '--dry-run',
      action='store_true',
      help='Flag for generating DDL and schema conversion report without'
      ' creating a Cloud Spanner database.')


def GetSpannerMigrationLogLevelFlag():
  return base.Argument(
      '--log-level',
      help='To configure the log level for the execution (INFO, VERBOSE).')


def GetSpannerMigrationWebOpenFlag():
  return base.Argument('--open', action='store_true',
                       help='Open the Spanner migration tool web interface in '
                       'the default browser.')


def GetSpannerMigrationWebPortFlag():
  return base.Argument(
      '--port',
      help=(
          'The port in which Spanner migration tool will run, defaults to 8080'
      ),
  )


def GetSpannerMigrationJobIdFlag():
  return base.Argument(
      '--job-id', required=True, help='The job Id of an existing migration job.'
  )


def GetSpannerMigrationDataShardIdsFlag():
  return base.Argument(
      '--data-shard-ids',
      help=(
          'Relevant to sharded migrations. Optional comma separated list of'
          ' data shard Ids, if nothing is specified, all shards are cleaned up.'
      ),
  )


def GetSpannerMigrationCleanupDatastreamResourceFlag():
  return base.Argument(
      '--datastream',
      action='store_true',
      help='Cleanup datastream resource(s).',
  )


def GetSpannerMigrationCleanupDataflowResourceFlag():
  return base.Argument(
      '--dataflow', action='store_true', help='Cleanup dataflow resource(s).'
  )


def GetSpannerMigrationCleanupPubsubResourceFlag():
  return base.Argument(
      '--pub-sub', action='store_true', help='Cleanup pubsub resource(s).'
  )


def GetSpannerMigrationCleanupMonitoringResourceFlag():
  return base.Argument(
      '--monitoring',
      action='store_true',
      help='Cleanup monitoring dashboard(s).',
  )


# Checks that user only specified instance partition, or database, or backup
# flag for LRO operations given --instance.
# TODO(b/339032416): Consider using gcloud mutex.
def CheckExclusiveLROFlagsUnderInstance(args):
  exlusive_flag_count = 0
  for flag in ['instance_partition', 'database', 'backup']:
    if args.IsSpecified(flag):
      exlusive_flag_count += 1
  if exlusive_flag_count > 1:
    raise c_exceptions.InvalidArgumentException(
        '--database or --backup or --instance-partition',
        'Must specify only --database or --backup or --instance-partition.',
    )


def GetSpannerMigrationProjectFlag():
  return base.Argument(
      '--project',
      help=(
          'The project in which the migration job and its resources will be'
          ' created.'
      ),
  )


def GetSpannerMigrationDataflowTemplateFlag():
  return base.Argument(
      '--dataflow-template',
      help=(
          'The google cloud storage path of the minimal downtime migration'
          ' template to use to run the migration job.'
      ),
  )


def GetSplitPoints(args):
  return split_file_parser.ParseSplitPoints(args)


def TableName(req, text='Cloud Spanner table name'):
  return base.Argument(
      '--table-name', required=req, help=text)


def SourceUri(req, text='URI of the file with data to import'):
  return base.Argument(
      '--source-uri', required=req, help=text)


def SourceFormat(req, text='Format of the file with data to import.'
                 'Supported formats: csv or mysqldump or pgdump'):
  return base.Argument(
      '--source-format', required=req, help=text)


def SchemaUri(req, text='URI of the file with schema of the data to import'):
  return base.Argument(
      '--schema-uri', required=req, help=text)


def CsvFieldDelimiter(req, text='Field delimiter for CSV files.'):
  return base.Argument(
      '--csv-field-delimiter', required=req, help=text)


def CsvLineDelimiter(req, text='Line delimiter for CSV files.'):
  return base.Argument(
      '--csv-line-delimiter', required=req, help=text)


# Spanner CLI flags
def GetSpannerCliHostFlag():
  return base.Argument(
      '--host',
      default='localhost',
      help='Host on which Spanner server is located.',
  )


def GetSpannerCliPortFlag():
  return base.Argument(
      '--port',
      default=None,
      type=arg_parsers.BoundedInt(lower_bound=1, upper_bound=65535),
      help='Port number that gcloud uses to connect to Spanner.',
  )


def GetSpannerCliIdleTransactionTimeoutFlag():
  return base.Argument(
      '--idle-transaction-timeout',
      type=int,
      default=60,
      help=(
          'Set the idle transaction timeout. The default timeout is 60 seconds.'
      ),
  )


def GetSpannerCliSkipColumnNamesFlag():
  return base.Argument(
      '--skip-column-names',
      action='store_true',
      help='Do not show column names in output.',
  )


def GetSpannerCliSkipSystemCommandFlag():
  return base.Argument(
      '--skip-system-command',
      action='store_true',
      help='Do not allow system command.',
  )


def GetSpannerCliPromptFlag():
  return base.Argument(
      '--prompt',
      default='spanner-cli> ',
      help='Set the prompt to the specified format.',
  )


def GetSpannerCliDelimiterFlag():
  return base.Argument(
      '--delimiter',
      default=';',
      help='Set the statement delimiter.',
  )


def GetSpannerCliTableFlag():
  return base.Argument(
      '--table',
      action='store_true',
      help='Show output in table format.',
  )


def GetSpannerCliHtmlFlag():
  return base.Argument(
      '--html',
      action='store_true',
      help='Show output in HTML format.',
  )


def GetSpannerCliXmlFlag():
  return base.Argument(
      '--xml',
      action='store_true',
      help='Show output in XML format.',
  )


def GetSpannerCliExecuteFlag():
  return base.Argument(
      '--execute',
      default='',
      help='Execute the statement and then exits.',
  )


def GetSpannerCliDatabaseRoleFlag():
  return base.Argument(
      '--database-role',
      default='',
      help='Database role user used to access the database.',
  )


def GetSpannerCliSourceFlag():
  return base.Argument(
      '--source',
      default='',
      help='Execute the statement from a file and then exits.',
  )


def GetSpannerCliTeeFlag():
  return base.Argument(
      '--tee',
      default='',
      help='Append a copy of the output to a named file.',
  )


def GetSpannerCliInitCommandFlag():
  return base.Argument(
      '--init-command',
      default='',
      help='SQL statement to execute after startup.',
  )


def GetSpannerCliInitCommandAddFlag():
  return base.Argument(
      '--init-command-add',
      default='',
      help='Additional SQL statement to execute after startup.',
  )


def GetSpannerCliSystemCommandFlag():
  return base.Argument(
      '--system-command',
      default='ON',
      type=lambda x: x.upper(),
      choices=['ON', 'OFF'],
      help='Enable or disable system commands. Default: ON',
  )
