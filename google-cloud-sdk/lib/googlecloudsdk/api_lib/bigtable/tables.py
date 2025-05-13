# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Bigtable tables API helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64

from apitools.base.py import encoding
from googlecloudsdk.api_lib.bigtable import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import times
import six


def ParseSingleRule(rule):
  """Parses GC rules from a rule string.

  Args:
    rule: A string representing a GC rule, e.g. `maxage=10d`

  Returns:
    A GcRule object.

  Raises:
    BadArgumentExpection: the input is mal-formatted.
  """
  rule_parts = rule.split('=')
  if len(rule_parts) != 2 or not rule_parts[1]:
    raise exceptions.BadArgumentException(
        '--column-families',
        'Invalid union or intersection rule: {0}'.format(rule),
    )

  if rule_parts[0] == 'maxage':
    return util.GetAdminMessages().GcRule(
        maxAge=ConvertDurationToSeconds(rule_parts[1], '--column-families')
    )
  elif rule_parts[0] == 'maxversions':
    return util.GetAdminMessages().GcRule(maxNumVersions=int(rule_parts[1]))
  else:
    raise exceptions.BadArgumentException(
        '--column-families',
        'Invalid union or intersection rule: {0}'.format(rule),
    )


def ParseBinaryRule(rule_list):
  """Parses GC rules from a rule list of 2 elements.

  Args:
    rule_list: A string list containing 2 elements.

  Returns:
    A list of GcRule objects.

  Raises:
    BadArgumentExpection: the input list is mal-formatted.
  """
  if len(rule_list) != 2:
    # Only support binary rule
    raise exceptions.BadArgumentException(
        '--column-families',
        'Invalid union or intersection rule: ' + ' '.join(rule_list),
    )

  results = []
  for rule in rule_list:
    results.append(ParseSingleRule(rule))

  return results


def ParseExpr(expr):
  """Parses family name and GC rules from the string expression.

  Args:
    expr: A string express contains family name and optional GC rules in the
      format of `family_name[:gc_rule]`, such as `my_family:maxage=10d`.

  Returns:
    A family name and a GcRule object defined in the Bigtable admin API.

  Raises:
    BadArgumentExpection: the input string is mal-formatted.
  """
  expr_list = expr.split(':')
  family = expr_list[0]
  expr_list_len = len(expr_list)
  if expr_list_len > 2 or family != family.strip():
    raise exceptions.BadArgumentException(
        '--column-families',
        'Input column family ({0}) is mal-formatted.'.format(expr),
    )

  # Without GC rules
  if expr_list_len == 1:
    # No GC rule is allowed
    return family, None

  # With GC rules
  if not expr_list[1]:
    raise exceptions.BadArgumentException(
        '--column-families',
        'Input column family ({0}) is mal-formatted.'.format(expr),
    )

  gc_rule = expr_list[1]
  union_list = gc_rule.split('||')
  intersection_list = gc_rule.split('&&')

  # Only do 1-level of parsing, don't support nested expression.
  if len(union_list) == 2 and len(intersection_list) == 1:
    # Union rule
    return family, util.GetAdminMessages().GcRule(
        union=util.GetAdminMessages().Union(rules=ParseBinaryRule(union_list))
    )
  elif len(union_list) == 1 and len(intersection_list) == 2:
    # Intersection rule
    return family, util.GetAdminMessages().GcRule(
        intersection=util.GetAdminMessages().Intersection(
            rules=ParseBinaryRule(intersection_list)
        )
    )
  elif len(union_list) == 1 and len(intersection_list) == 1:
    # Either empty or a simple rule
    if gc_rule:
      return family, ParseSingleRule(gc_rule)
  else:
    raise exceptions.BadArgumentException(
        '--column-families',
        'Input column family ({0}) is mal-formatted.'.format(expr),
    )


def UpdateRequestWithInput(original_ref, args, req):
  """Parse argument and construct create table request.

  Args:
    original_ref: the gcloud resource.
    args: input arguments.
    req: the real request to be sent to backend service.

  Returns:
    req: the real request to be sent to backend service.
  """
  req.createTableRequest.tableId = args.table
  req.parent = original_ref.Parent().RelativeName()

  return req


def MakeSplits(split_list):
  """Convert a string list to a Split object.

  Args:
    split_list: A list that contains strings representing splitting points.

  Returns:
    A Split object.
  """
  results = []
  for split in split_list:
    results.append(util.GetAdminMessages().Split(key=split.encode('utf-8')))

  return results


def ConvertDurationToSeconds(duration, arg_name):
  """Convert a string of duration in any form to seconds.

  Args:
    duration: A string of any valid form of duration, such as `10d`, `1w`, `36h`
    arg_name: The name of the argument that the duration is passed in.

  Returns:
    A string of duration counted in seconds, such as `1000s`

  Raises:
    BadArgumentExpection: the input duration is mal-formatted.
  """
  try:
    return times.FormatDurationForJson(times.ParseDuration(duration))
  except times.DurationSyntaxError as duration_error:
    raise exceptions.BadArgumentException(
        arg_name,
        str(duration_error),
    )
  except times.DurationValueError as duration_error:
    raise exceptions.BadArgumentException(
        arg_name,
        str(duration_error),
    )


def ParseColumnFamilies(family_list):
  """Parses column families value object from the string list.

  Args:
    family_list: A list that contains one or more strings representing family
      name and optional GC rules in the format of `family_name[:gc_rule]`, such
      as `my_family_1,my_family_2:maxage=10d`.

  Returns:
    A column families value object.
  """
  results = []

  for expr in family_list:
    family, gc_rule = ParseExpr(expr)
    column_family = util.GetAdminMessages().ColumnFamily(gcRule=gc_rule)
    results.append(
        util.GetAdminMessages().Table.ColumnFamiliesValue.AdditionalProperty(
            key=family, value=column_family
        )
    )

  return util.GetAdminMessages().Table.ColumnFamiliesValue(
      additionalProperties=results
  )


def ParseChangeStreamRetentionPeriod(retention_period):
  """Parses change stream retention period from the string.

  Args:
    retention_period: Change stream retention period in the format of `3d` for 3
      days.

  Returns:
    A string of duration counted in seconds, such as `259200s`
  """
  return ConvertDurationToSeconds(
      retention_period, '--change-stream-retention-period'
  )


def ParseTieredStorageConfigDuration(duration):
  """Parses tiered storage config duration from the string.

  Args:
    duration: Tiered storage config duration in the format of a valid gcloud
      datetime duration string, such as `10d`, `1w`, `36h`.

  Returns:
    A string of duration counted in seconds, such as `259200s`
  """
  return ConvertDurationToSeconds(
      duration, '--tiered-storage-infrequent-access-older-than'
  )


def AddFieldToUpdateMask(field, req):
  """Adding a new field to the update mask of the updateTableRequest.

  Args:
    field: the field to be updated.
    req: the original updateTableRequest.

  Returns:
    req: the updateTableRequest with update mask refreshed.
  """
  update_mask = req.updateMask
  if update_mask:
    if update_mask.count(field) == 0:
      req.updateMask = update_mask + ',' + field
  else:
    req.updateMask = field
  return req


def RefreshUpdateMask(unused_ref, args, req):
  """Refresh the update mask of the updateTableRequest according to the input arguments.

  Args:
    unused_ref: the gcloud resource (unused).
    args: the input arguments.
    req: the original updateTableRequest.

  Returns:
    req: the updateTableRequest with update mask refreshed.
  """
  if args.clear_change_stream_retention_period:
    req = AddFieldToUpdateMask('changeStreamConfig', req)
  if args.change_stream_retention_period:
    req = AddFieldToUpdateMask('changeStreamConfig.retentionPeriod', req)
  if args.enable_automated_backup or args.disable_automated_backup:
    req = AddFieldToUpdateMask('automatedBackupPolicy', req)
  if args.automated_backup_retention_period:
    req = AddFieldToUpdateMask('automatedBackupPolicy.retentionPeriod', req)
  # TODO: b/379182385 - Remove this check once the flag is released in GA.
  #
  # We need this to verify that the flag exists in this release track.
  if hasattr(args, 'clear_tiered_storage_config'):
    if args.clear_tiered_storage_config:
      req = AddFieldToUpdateMask('tieredStorageConfig', req)
    if args.tiered_storage_infrequent_access_older_than:
      req = AddFieldToUpdateMask(
          'tieredStorageConfig.infrequentAccess.includeIfOlderThan', req
      )
  if args.row_key_schema_definition_file or args.clear_row_key_schema:
    req = AddFieldToUpdateMask('rowKeySchema', req)
  return req


def AddAdditionalArgs():
  """Adds additional flags."""
  return (
      AddChangeStreamConfigUpdateTableArgs()
      + AddAutomatedBackupPolicyUpdateTableArgs()
  )


def AddAdditionalArgsAlphaBeta():
  """Adds additional flags for alpha and beta."""
  return AddAdditionalArgs() + AddTieredStorageConfigUpdateTableArgs()


def AddChangeStreamConfigUpdateTableArgs():
  """Adds the change stream commands to update table CLI.

  This can't be defined in the yaml because that automatically generates the
  inverse for any boolean args and we don't want the nonsensical
  `no-clear-change-stream-retention-period`. We use store_const to only allow
  `clear-change-stream-retention-period` or `change-stream-retention-period`
  arguments

  Returns:
    Argument group containing change stream args
  """
  argument_group = base.ArgumentGroup(mutex=True)
  argument_group.AddArgument(
      base.Argument(
          '--clear-change-stream-retention-period',
          help=(
              'This disables the change stream and eventually removes the'
              ' change stream data.'
          ),
          action='store_const',
          const=True,
      )
  )
  argument_group.AddArgument(
      base.Argument(
          '--change-stream-retention-period',
          help=(
              'The length of time to retain change stream data for the table, '
              'in the range of [1 day, 7 days]. Acceptable units are days (d), '
              'hours (h), minutes (m), and seconds (s). If not already '
              'specified, enables a change stream for the table. Examples: `5d`'
              ' or `48h`.'
          ),
      )
  )
  return [argument_group]


def AddTieredStorageConfigUpdateTableArgs():
  """Adds the tiered storage config commands to update table CLI.

  This can't be defined in the yaml because that automatically generates the
  inverse for any boolean args and we don't want the nonsensical
  `no-clear-tiered-storage-config`. We use store_const to only allow
  `clear-tiered-storage-config`.

  Returns:
    Argument group containing tiered storage config args
  """
  argument_group = base.ArgumentGroup(mutex=True)
  argument_group.AddArgument(
      base.Argument(
          '--clear-tiered-storage-config',
          help='Disables the tiered storage config.',
          action='store_const',
          const=True,
      )
  )
  argument_group.AddArgument(
      base.Argument(
          '--tiered-storage-infrequent-access-older-than',
          help=(
              'The age at which data should be moved to infrequent access'
              ' storage.\n\nSee `$ gcloud topic datetimes` for information on'
              ' absolute duration formats.'
          ),
      )
  )
  return [argument_group]


def AddAutomatedBackupPolicyCreateTableArgs():
  """Adds automated backup policy commands to create table CLI.

  This can't be defined in the yaml because that automatically generates the
  inverse for any boolean args and we don't want the nonsensical
  `no-enable-automated-backup`. We use store_const to only allow
  `enable-automated-backup` argument.

  Returns:
    Argument group containing automated backup args.
  """
  argument_group = base.ArgumentGroup(mutex=True)
  argument_group.AddArgument(
      base.Argument(
          '--enable-automated-backup',
          help=(
              'Once set, enables the default automated backup policy'
              ' (retention_period=7d, frequency=1d) for the table.'
          ),
          action='store_const',
          const=True,
      )
  )
  argument_group.AddArgument(
      base.Argument(
          '--automated-backup-retention-period',
          help=(
              'The retention period of automated backup in the format of `30d`'
              ' for 30 days. Min retention period is `3d` and max is `90d`.'
              ' Setting this flag will enable automated backup for the table.'
          ),
      )
  )
  return [argument_group]


def AddAutomatedBackupPolicyUpdateTableArgs():
  """Adds automated backup policy commands to update table CLI."""
  argument_group = base.ArgumentGroup(mutex=True)
  argument_group.AddArgument(
      base.Argument(
          '--enable-automated-backup',
          help=(
              'Once set, enables the default automated backup policy'
              ' (retention_period=7d, frequency=1d) for the table. Note: If a'
              ' table has automated backup enabled, this flag resets it to the'
              ' default policy.'
          ),
          action='store_const',
          const=True,
      )
  )
  argument_group.AddArgument(
      base.Argument(
          '--disable-automated-backup',
          help='Once set, disables automated backup policy for the table.',
          action='store_const',
          const=True,
      )
  )
  argument_group.AddArgument(
      base.Argument(
          '--automated-backup-retention-period',
          help=(
              'The retention period of automated backup in the format of `30d`'
              ' for 30 days. Min retention period is `3d` and max is `90d`.'
              ' Setting this flag will enable automated backup for the table.'
          ),
      )
  )
  return [argument_group]


def HandleChangeStreamArgs(unused_ref, args, req):
  if args.change_stream_retention_period:
    req.table.changeStreamConfig = CreateChangeStreamConfig(
        args.change_stream_retention_period
    )
  return req


def HandleAutomatedBackupPolicyCreateTableArgs(unused_ref, args, req):
  """Handles automated backup policy args for create table CLI."""
  if args.enable_automated_backup:
    req.createTableRequest.table.automatedBackupPolicy = (
        CreateDefaultAutomatedBackupPolicy()
    )
  if args.automated_backup_retention_period:
    req.createTableRequest.table.automatedBackupPolicy = (
        # Keeping the frequency as None to be consistent with the UpdateTable
        # command.
        CreateAutomatedBackupPolicy(
            args.automated_backup_retention_period, None
        )
    )
  return req


def HandleAutomatedBackupPolicyUpdateTableArgs(unused_ref, args, req):
  """Handle automated backup policy args for update table CLI.

  If `enable_automated_backup` flag is set, add default policy to table. If
  `disable_automated_backup` flag is set, keep table.automatedBackupPolicy as
  empty, together with the update_mask, it will clear automated backup policy.
  If `automated_backup_retention_period` flag is set, add policy with given
  retention period to table.

  Args:
    unused_ref: the gcloud resource (unused).
    args: the input arguments.
    req: the original updateTableRequest.

  Returns:
    req: the updateTableRequest with automated backup policy handled.
  """
  if args.enable_automated_backup:
    req.table.automatedBackupPolicy = CreateDefaultAutomatedBackupPolicy()
  if args.automated_backup_retention_period:
    req.table.automatedBackupPolicy = CreateAutomatedBackupPolicy(
        args.automated_backup_retention_period, None
    )
  return req


def HandleTieredStorageArgs(unused_ref, args, req):
  """Handle tiered storage args for update table CLI.

  Args:
    unused_ref: the gcloud resource (unused).
    args: the input arguments.
    req: the original updateTableRequest.

  Returns:
    req: the updateTableRequest with tiered storage config handled.
  """
  # TODO: b/379182385 - Remove this check once the flag is released in GA.
  #
  # We need this to verify that the flag exists in this release track.
  if not hasattr(args, 'clear_tiered_storage_config'):
    return req

  if args.clear_tiered_storage_config:
    req.table.tieredStorageConfig = None
  if args.tiered_storage_infrequent_access_older_than:
    req.table.tieredStorageConfig = util.GetAdminMessages().TieredStorageConfig(
        infrequentAccess=util.GetAdminMessages().TieredStorageRule(
            includeIfOlderThan=ParseTieredStorageConfigDuration(
                args.tiered_storage_infrequent_access_older_than
            )
        )
    )

  return req


def CreateChangeStreamConfig(duration):
  return util.GetAdminMessages().ChangeStreamConfig(
      retentionPeriod=ConvertDurationToSeconds(
          duration, '--change-stream-retention-period'
      )
  )


def CreateAutomatedBackupPolicy(retention_period, frequency):
  """Constructs AutomatedBackupPolicy message with given values.

  Args:
    retention_period: The retention period of the automated backup policy.
    frequency: The frequency of the automated backup policy.

  Returns:
    AutomatedBackupPolicy with the specified policy config.
  """
  policy = util.GetAdminMessages().AutomatedBackupPolicy()
  if retention_period:
    policy.retentionPeriod = ConvertDurationToSeconds(
        retention_period, '--automated-backup-retention-period'
    )
  if frequency:
    policy.frequency = ConvertDurationToSeconds(
        frequency, '--automated-backup-frequency'
    )
  return policy


def CreateDefaultAutomatedBackupPolicy():
  """Constructs AutomatedBackupPolicy message with default values.

  The default values are: retention_period=7d, frequency=1d

  Returns:
    AutomatedBackupPolicy with default policy config.
  """
  return CreateAutomatedBackupPolicy('7d', '1d')


def Utf8ToBase64(s):
  """Encode a utf-8 string as a base64 string."""
  return six.ensure_text(base64.b64encode(six.ensure_binary(s)))


def HandleRowKeySchemaCreateTableArgs(unused_ref, args, req):
  """Handles row key schema create table args."""
  if args.row_key_schema_definition_file:
    req.createTableRequest.table.rowKeySchema = (
        ParseRowKeySchemaFromDefinitionFile(
            args.row_key_schema_definition_file,
            args.row_key_schema_pre_encoded_bytes,
        )
    )
  return req


def HandleRowKeySchemaUpdateTableArgs(unused_ref, args, req):
  """Handles row key schema update table args."""
  if args.row_key_schema_definition_file:
    req.table.rowKeySchema = ParseRowKeySchemaFromDefinitionFile(
        args.row_key_schema_definition_file,
        args.row_key_schema_pre_encoded_bytes,
    )

  if args.clear_row_key_schema:
    req.ignoreWarnings = True

  return req


def Base64EncodeBinaryFieldsInRowKeySchema(row_key_schema):
  """Encodes binary fields in the row key schema in Base64."""
  # We don't need to check for missing encoding here, as the admin API will
  # return an error if the encoding is missing.
  if (
      not row_key_schema
      or 'encoding' not in row_key_schema
      or 'delimitedBytes' not in row_key_schema['encoding']
      or 'delimiter' not in row_key_schema['encoding']['delimitedBytes']
      or not row_key_schema['encoding']['delimitedBytes']['delimiter']
  ):
    return row_key_schema

  row_key_schema['encoding']['delimitedBytes']['delimiter'] = Utf8ToBase64(
      row_key_schema['encoding']['delimitedBytes']['delimiter']
  )
  return row_key_schema


def ParseRowKeySchemaFromDefinitionFile(definition_file, pre_encoded):
  """Parses row key schema from the definition file.

  Args:
    definition_file: The path to the definition file. File must be in YAML or
      JSON format.
    pre_encoded: Whether all the binary fields in the row key schema (e.g.
      encoding.delimited_bytes.delimiter) are pre-encoded in Base64.

  Returns:
    A struct type object representing the row key schema.

  Raises:
    BadArgumentException if the definition file is not found, can't be
      read, or is not a valid YAML or JSON file.
    ValueError if the YAML/JSON object cannot be parsed as a valid row key
      schema.
  """
  row_key_schema_msg_type = (
      util.GetAdminMessages().GoogleBigtableAdminV2TypeStruct
  )
  try:
    row_key_schema_to_parse = yaml.load_path(definition_file)
    if not pre_encoded:
      Base64EncodeBinaryFieldsInRowKeySchema(row_key_schema_to_parse)
    parsed_row_key_schema = encoding.PyValueToMessage(
        row_key_schema_msg_type, row_key_schema_to_parse
    )
  except (yaml.FileLoadError, yaml.YAMLParseError) as e:
    raise exceptions.BadArgumentException('--row-key-schema-definition-file', e)
  except AttributeError as e:
    raise ValueError(
        'File [{0}] cannot be parsed as a valid row key schema. [{1}]'.format(
            definition_file, e
        )
    )
  return parsed_row_key_schema
