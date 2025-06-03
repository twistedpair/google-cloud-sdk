# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the migration jobs related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum

from googlecloudsdk.calliope import arg_parsers


@enum.unique
class ApiType(enum.Enum):
  """This API type is used to differentiate between the classification types of Create requests and Update requests."""
  CREATE = 'create'
  UPDATE = 'update'


def AddNoAsyncFlag(parser):
  """Adds a --no-async flag to the given parser."""
  help_text = (
      'Waits for the operation in progress to complete before returning.'
  )
  parser.add_argument('--no-async', action='store_true', help=help_text)


def AddDisplayNameFlag(parser):
  """Adds a --display-name flag to the given parser."""
  help_text = """
    A user-friendly name for the migration job. The display name can include
    letters, numbers, spaces, and hyphens, and must start with a letter.
    """
  parser.add_argument('--display-name', help=help_text)


def AddTypeFlag(parser, required=False):
  """Adds --type flag to the given parser."""
  help_text = 'Type of the migration job.'
  choices = ['ONE_TIME', 'CONTINUOUS']
  parser.add_argument(
      '--type', help=help_text, choices=choices, required=required
  )


def AddDumpGroupFlag(parser):
  """Adds a --dump-path or --dump-flags flag to the given parser."""
  dump_group = parser.add_group(mutex=True)
  AddDumpPathFlag(dump_group)
  AddDumpFlagsFlag(dump_group)


def AddDumpPathFlag(parser):
  """Adds a --dump-path flag to the given parser."""
  help_text = """\
    Path to the dump file in Google Cloud Storage, in the format:
    `gs://[BUCKET_NAME]/[OBJECT_NAME]`.
    """
  parser.add_argument('--dump-path', help=help_text)


def AddDumpFlagsFlag(parser):
  """Adds a --dump-flags flag to the given parser."""
  help_text = """\
    A list of dump flags. An object containing a list of "key": "value" pairs.
    """
  parser.add_argument(
      '--dump-flags',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      help=help_text,
      hidden=True,
  )


def AddConnectivityGroupFlag(parser, api_type, required=False):
  """Adds connectivity flag group to the given parser."""
  if api_type == ApiType.CREATE:
    connectivity_group = parser.add_group(
        (
            'The connectivity method used by the migration job. If a'
            " connectivity method isn't specified, then it isn't added to the"
            ' migration job.'
        ),
        mutex=True,
    )
  elif api_type == ApiType.UPDATE:
    connectivity_group = parser.add_group(
        (
            'The connectivity method used by the migration job. If a'
            " connectivity method isn't specified, then it isn't updated for"
            ' the migration job.'
        ),
        mutex=True,
    )
  connectivity_group.add_argument(
      '--static-ip',
      action='store_true',
      help=(
          'Use the default IP allowlist method. This method creates a public IP'
          ' that will be used with the destination Cloud SQL database. The'
          ' method works by configuring the source database server to accept'
          ' connections from the outgoing IP of the Cloud SQL instance.'
      ),
  )
  connectivity_group.add_argument(
      '--peer-vpc',
      help=(
          'Name of the VPC network to peer with the Cloud SQL private network.'
      ),
  )
  reverse_ssh_group = connectivity_group.add_group(
      'Parameters for the reverse-SSH tunnel connectivity method.'
  )
  reverse_ssh_group.add_argument(
      '--vm-ip', help='Bastion Virtual Machine IP.', required=required
  )
  reverse_ssh_group.add_argument(
      '--vm-port',
      help='Forwarding port for the SSH tunnel.',
      type=int,
      required=required,
  )
  reverse_ssh_group.add_argument(
      '--vm', help='Name of VM that will host the SSH tunnel bastion.'
  )
  reverse_ssh_group.add_argument(
      '--vpc',
      help='Name of the VPC network where the VM is hosted.',
      required=required,
  )


def AddFilterFlag(parser):
  """Adds a --filter flag to the given parser."""
  help_text = (
      'Filter the entities based on [AIP-160](https://google.aip.dev/160)'
      ' standard. Example: to filter all tables whose name start with'
      ' "Employee" and are present under schema "Company", use filter as'
      ' "Company.Employee```*``` AND type=TABLE"'
  )
  parser.add_argument('--filter', help=help_text)


def AddCommitIdFlag(parser):
  """Adds a --commit-id flag to the given parser."""
  help_text = (
      'Commit id for the conversion workspace to use for creating the migration'
      ' job. If not specified, the latest commit id will be used by default.'
  )
  parser.add_argument('--commit-id', help=help_text)


def AddDumpParallelLevelFlag(parser):
  """Adds a --dump-parallel-level flag to the given parser."""
  help_text = (
      'Parallelization level during initial dump of the migration job. If not'
      ' specified, will be defaulted to OPTIMAL.'
  )
  choices = ['MIN', 'OPTIMAL', 'MAX']
  parser.add_argument('--dump-parallel-level', help=help_text, choices=choices)


def AddDumpTypeFlag(parser):
  """Adds a --dump-type flag to the given parser."""
  help_text = (
      'The type of the data dump. Currently applicable for MySQL to MySQL '
      'migrations only.'
  )
  choices = ['LOGICAL', 'PHYSICAL']
  parser.add_argument('--dump-type', help=help_text, choices=choices)


def AddSqlServerHomogeneousMigrationConfigFlag(parser, is_update=False):
  """Adds SQL Server homogeneous migration flag group to the given parser."""
  sqlserver_homogeneous_migration_config = parser.add_group(
      (
          'The SQL Server homogeneous migration config. This is used only for'
          ' SQL Server to CloudSQL SQL Server migrations.'
      ),
  )
  if is_update:
    AddSqlServerBackupFilePattern(
        sqlserver_homogeneous_migration_config, default_value=None
    )
    AddSqlServerDatabasesFlag(
        sqlserver_homogeneous_migration_config, required=False
    )
    AddSqlServerEncryptedDatabasesFlag(sqlserver_homogeneous_migration_config)
    AddSqlServerUseDiffBackupFlag(sqlserver_homogeneous_migration_config)
    AddSqlServerPromoteWhenReadyFlag(sqlserver_homogeneous_migration_config)
  else:
    AddSqlServerBackupFilePattern(
        sqlserver_homogeneous_migration_config,
        default_value='.*(\\.|_)(<epoch>\\d*)\\.(trn|bak|trn\\.final)',
    )
    AddSqlServerDatabasesFlag(
        sqlserver_homogeneous_migration_config, required=True
    )
    AddSqlServerEncryptedDatabasesFlag(sqlserver_homogeneous_migration_config)
    AddSqlServerUseDiffBackupFlag(sqlserver_homogeneous_migration_config)
    AddSqlServerPromoteWhenReadyFlag(sqlserver_homogeneous_migration_config)


def AddSqlServerBackupFilePattern(parser, default_value=None):
  """Adds a --sqlserver-backup-file-pattern flag to the given parser."""
  help_text = (
      'Pattern that describes the default backup naming strategy. The specified'
      ' pattern should ensure lexicographical order of backups. The pattern'
      ' should define the following capture group set\nepoch - unix'
      ' timestamp\nExample: For backup files TestDB.1691448240.bak,'
      ' TestDB.1691448254.trn, TestDB.1691448284.trn.final use pattern:'
      ' .*\\.(<epoch>\\d*)\\.(trn|bak|trn\\.final) or'
      ' .*\\.(<timestamp>\\d*)\\.(trn|bak|trn\\.final)\nThis flag is used only'
      ' for SQL Server to Cloud SQL migrations.'
  )
  parser.add_argument(
      '--sqlserver-backup-file-pattern',
      help=help_text,
      default=default_value,
      hidden=True,
  )


def AddSqlServerDatabasesFlag(parser, required=True):
  """Adds a --sqlserver-databases flag to the given parser."""
  help_text = """\
    A list of databases to be migrated to the destination Cloud SQL instance.
    Provide databases as a comma separated list. This list should contain all
    encrypted and non-encrypted database names. This flag is used only for
    SQL Server to Cloud SQL migrations.
    """
  parser.add_argument(
      '--sqlserver-databases',
      metavar='databaseName',
      type=arg_parsers.ArgList(min_length=1),
      help=help_text,
      required=required,
  )


def AddSqlServerEncryptedDatabasesFlag(parser):
  """Adds a --sqlserver-encrypted-databases flag to the given parser."""
  help_text = """\
    A JSON/YAML file describing the encryption settings per database for all encrytped databases.
    Note:
    Path to the Certificate (.cer) and Private Key (.pvk) in Cloud Storage,
    should be in the form of `gs://bucketName/fileName`. The instance must
    have write permissions to the bucket and read access to the file.
    An example of a JSON request:
        [{
            "database": "db1",
            "encryptionOptions": {
                "certPath": "Path to certificate 1",
                "pvkPath": "Path to certificate private key 1",
                "pvkPassword": "Private key password 1"
            }
        },
        {
            "database": "db2",
            "encryptionOptions": {
                "certPath": "Path to certificate 2",
                "pvkPath": "Path to certificate private key 2",
                "pvkPassword": "Private key password 2"
            }
        }]

      This flag accepts "-" for stdin. This flag is used only for SQL Server to Cloud SQL migrations.
    """
  parser.add_argument(
      '--sqlserver-encrypted-databases',
      type=arg_parsers.YAMLFileContents(),
      help=help_text,
  )


def AddSqlServerUseDiffBackupFlag(parser):
  """Adds a --sqlserver-diff-backup flag to the given parser."""
  help_text = """\
      Enable differential backups. If not specified, differential backups
      are disabled by default. Use --sqlserver-diff-backup to enable and
      --no-sqlserver-diff-backup to disable. This flag is used only for
      homogeneous SQL Server to Cloud SQL for SQL Server migrations.
    """
  parser.add_argument(
      '--sqlserver-diff-backup',
      action='store_true',
      help=help_text,
  )


def AddSkipValidationFlag(parser):
  """Adds a --skip-validation flag to the given parser."""
  help_text = """\
    Restart the migration job without running prior configuration verification.
    """
  parser.add_argument(
      '--skip-validation',
      action='store_true',
      help=help_text,
  )


def AddMigrationJobObjectsConfigFlagForCreateAndUpdate(parser):
  """Adds migration job objects config flag group to the given parser."""
  migration_config = parser.add_group(
      'The migration job objects config.',
      mutex=True,
  )
  database_config = migration_config.add_group(
      'The migration job objects config for databases.',
      mutex=True,
  )
  AddDatabasesFilterFlag(database_config)
  AddAllDatabasesFlag(database_config)


def AddMigrationJobObjectsConfigFlagForPromote(parser):
  """Adds migration job objects config flag group to the given parser."""
  migration_config = parser.add_group(
      'The migration job objects config.',
      mutex=True,
  )
  AddDatabasesFilterFlagForSqlServer(migration_config)


def AddMigrationJobObjectsConfigFlagForRestart(parser):
  """Adds migration job objects config flag group to the given parser."""
  migration_config = parser.add_group(
      'The migration job objects config.',
      mutex=True,
  )
  AddDatabasesFilterFlagForSqlServer(migration_config)
  AddObjectFilterFlagForHeterogeneous(migration_config)


def AddDatabasesFilterFlag(parser):
  """Adds a --databases-filter flag to the given parser."""
  help_text = """\
    A list of databases to be migrated to the destination instance.
    Provide databases as a comma separated list. This flag is used only for
    Postgres to AlloyDB migrations and Postgres to Cloud SQL Postgres migrations.
    """
  parser.add_argument(
      '--databases-filter',
      metavar='databaseName',
      type=arg_parsers.ArgList(min_length=1),
      help=help_text,
  )


def AddAllDatabasesFlag(parser):
  """Adds --all-databases flag to the given parser."""
  help_text = """\
    Migrate all databases for the migration job. This flag is used only for
    Postgres to AlloyDB migrations and Postgres to Cloud SQL Postgres migrations.
    """
  parser.add_argument('--all-databases', action='store_true', help=help_text)


def AddDatabasesFilterFlagForSqlServer(parser):
  """Adds a --databases-filter flag to the given parser."""
  help_text = """\
    A list of databases to be migrated to the destination instance.
    Provide databases as a comma separated list. This flag is used only for
    SQL Server to Cloud SQL SQL Server migrations.
    """
  parser.add_argument(
      '--databases-filter',
      metavar='databaseName',
      type=arg_parsers.ArgList(min_length=1),
      help=help_text,
  )


def AddObjectFilterFlagForHeterogeneous(parser):
  """Adds a --object-filter flag to the given parser."""
  help_text = """\
    A list of schema and table names to be migrated to the destination instance.
    Usage: --object-filter schema=schema1,table=table1 --object-filter schema=schema2,table=table2
    This flag is used only for heterogeneous migrations.
    """
  parser.add_argument(
      '--object-filter',
      type=arg_parsers.ArgDict(
          spec={
              'schema': str,
              'table': str,
          },
          required_keys=['schema', 'table'],
      ),
      action='append',
      help=help_text,
      hidden=True,
  )


def AddSqlServerPromoteWhenReadyFlag(parser):
  """Adds a --sqlserver-promote-when-ready flag to the given parser."""
  help_text = """\
      Promote the database when it is ready. Use --sqlserver-promote-when-ready
      to enable and --no-sqlserver-promote-when-ready to disable. This flag is
      used only for homogeneous SQL Server to Cloud SQL for SQL Server
      migrations.
    """
  parser.add_argument(
      '--sqlserver-promote-when-ready',
      action='store_true',
      help=help_text,
  )


def AddRestartFailedObjectsFlag(parser):
  """Adds a --restart-failed-objects flag to the given parser."""
  help_text = """\
    Restart the failed objects in the migration job. This flag is used only for
    Postgres to AlloyDB migrations and Postgres to Cloud SQL Postgres migrations.
    """
  parser.add_argument(
      '--restart-failed-objects',
      action='store_true',
      help=help_text,
  )


def AddHeterogeneousMigrationConfigFlag(parser, is_update=False):
  """Adds heterogeneous migration flag group to the given parser."""
  heterogeneous_migration_config = parser.add_group(
      (
          'The heterogeneous migration config. This is used only for'
          ' Oracle to Cloud SQL for PostgreSQL and SQL Server to Cloud SQL for'
          ' PostgreSQL migrations.'
      ),
  )
  AddHeterogeneousMigrationSourceConfigFlags(
      heterogeneous_migration_config, is_update
  )
  AddHeterogeneousMigrationDestinationConfigFlags(
      heterogeneous_migration_config
  )


def AddHeterogeneousMigrationDestinationConfigFlags(parser):
  """Adds heterogeneous migration destination config flag to the parser."""
  destination_config = parser.add_group(
      (
          'Configuration for Postgres as a destination in a heterogeneous'
          ' migration.'
      ),
  )
  destination_config.add_argument(
      '--max-concurrent-destination-connections',
      help="""\
        Maximum number of concurrent connections Database Migration Service will
        open to the destination for data migration.
        """,
      type=int,
  )
  destination_config.add_argument(
      '--transaction-timeout',
      help="""Timeout for data migration transactions.""",
      type=arg_parsers.Duration(lower_bound='30s', upper_bound='300s'),
  )


def AddHeterogeneousMigrationSourceConfigFlags(parser, is_update=False):
  """Adds heterogeneous migration source config flag group to the parser."""
  source_config = parser.add_group(
      (
          'Configuration for Oracle or SQL Server as a source in a'
          ' heterogeneous migration.'
      ),
  )
  source_config.add_argument(
      '--max-concurrent-full-dump-connections',
      help="""\
        Maximum number of connections Database Migration Service will open to
        the source for full dump phase.
        """,
      type=int,
  )
  source_config.add_argument(
      '--max-concurrent-cdc-connections',
      help="""\
        Maximum number of connections Database Migration Service will open to
        the source for CDC phase.
        """,
      type=int,
  )
  if not is_update:
    skip_full_dump_group = source_config.add_group(
        'Configuration for skipping full dump.',
    )
    skip_full_dump_group.add_argument(
        '--skip-full-dump',
        help="""\
          Whether to skip full dump or not.
          """,
        action='store_true',
    )
    cdc_start_position_group = skip_full_dump_group.add_group(
        'Configuration for CDC start position.',
        mutex=True,
    )
    cdc_start_position_group.add_argument(
        '--oracle-cdc-start-position',
        help="""\
          Oracle schema change number (SCN) to start CDC data migration from.
          """,
        type=int,
    )
    cdc_start_position_group.add_argument(
        '--sqlserver-cdc-start-position',
        help="""\
          Sqlserver log squence number (LSN) to start CDC data migration from.
          """
    )
