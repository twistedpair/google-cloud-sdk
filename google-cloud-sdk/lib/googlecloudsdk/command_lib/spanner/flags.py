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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from argcomplete.completers import FilesCompleter
from googlecloudsdk.api_lib.spanner import databases
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.spanner import ddl_parser
from googlecloudsdk.command_lib.util import completers
from googlecloudsdk.core.util import files


class BackupCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(BackupCompleter, self).__init__(
        collection='spanner.projects.instances.backups',
        list_command='spanner backups list --uri',
        flags=['instance'],
        **kwargs)


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


def Database(positional=True,
             required=True,
             text='Cloud Spanner database ID.'):
  if positional:
    return base.Argument(
        'database',
        completer=DatabaseCompleter,
        help=text)
  else:
    return base.Argument(
        '--database',
        required=required,
        completer=DatabaseCompleter,
        help=text)


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


def Config(required=True):
  return base.Argument(
      '--config',
      completer=InstanceConfigCompleter,
      required=required,
      help='Instance configuration defines the geographic placement and '
      'replication of the databases in that instance. Available '
      'configurations can be found by running '
      '"gcloud spanner instance-configs list"')


def Description(required=True):
  return base.Argument(
      '--description',
      required=required,
      help='Description of the instance.')


def Instance(positional=True, text='Cloud Spanner instance ID.'):
  if positional:
    return base.Argument(
        'instance',
        completer=InstanceCompleter,
        help=text)
  else:
    return base.Argument(
        '--instance',
        required=True,
        completer=InstanceCompleter,
        help=text)


def Nodes(required=False):
  return base.Argument(
      '--nodes',
      required=required,
      type=int,
      help='Number of nodes for the instance.')


def ProcessingUnits(required=False):
  return base.Argument(
      '--processing-units',
      required=required,
      type=int,
      help='Number of processing units for the instance.')


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

  type_choices = {
      'INSTANCE':
          'Returns instance operations for the given instance. '
          'Note, type=INSTANCE does not work with --database or --backup.',
      'DATABASE':
          'If only the instance is specified (--instance), returns all '
          'database operations associated with the databases in the '
          'instance. When a database is specified (--database), the command '
          'would return database operations for the given database.',
      'BACKUP':
          'If only the instance is specified (--instance), returns all '
          'backup operations associated with backups in the instance. When '
          'a backup is specified (--backup), only the backup operations for '
          'the given backup are returned.',
      'DATABASE_RESTORE':
          'Database restore operations are returned for all databases in '
          'the given instance (--instance only) or only those associated '
          'with the given database (--database)',
      'DATABASE_CREATE':
          'Database create operations are returned for all databases in '
          'the given instance (--instance only) or only those associated '
          'with the given database (--database)',
      'DATABASE_UPDATE_DDL':
          'Database update DDL operations are returned for all databases in '
          'the given instance (--instance only) or only those associated '
          'with the given database (--database)'
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
      text='For a backup operation, the name of the backup '
      'the operation is executing on.').AddToParser(parser)
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
  OperationId().AddToParser(parser)
