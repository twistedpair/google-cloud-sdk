# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Database Migration Service migration jobs API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.database_migration import api_util
from googlecloudsdk.api_lib.database_migration import conversion_workspaces
from googlecloudsdk.api_lib.database_migration import filter_rewrite
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core.resource import resource_property
import six


class Error(core_exceptions.Error):
  """Class for errors raised by container commands."""


class MigrationJobsClient(object):
  """Client for migration jobs service in the API."""

  # Contains the update mask for specified fields.
  _FIELDS_MAP = [
      'display_name',
      'type',
      'dump_path',
      'source',
      'destination',
      'dump_flags',
  ]
  _REVERSE_MAP = ['vm_ip', 'vm_port', 'vm', 'vpc']

  def __init__(self, release_track):
    self.client = api_util.GetClientInstance(release_track)
    self.messages = api_util.GetMessagesModule(release_track)
    self._service = self.client.projects_locations_migrationJobs
    if release_track == base.ReleaseTrack.GA:
      self._service_objects = (
          self.client.projects_locations_migrationJobs_objects
      )
    else:
      self._service_objects = None
    self.resource_parser = api_util.GetResourceParser(release_track)
    self.release_track = release_track

  def _ValidateArgs(self, args):
    self._ValidateDumpPath(args)

  def _ValidateDumpPath(self, args):
    if args.dump_path is None:
      return
    try:
      storage_util.ObjectReference.FromArgument(
          args.dump_path, allow_empty_object=False
      )
    except Exception as e:
      raise exceptions.InvalidArgumentException('dump-path', six.text_type(e))

  def _ValidateConversionWorkspaceArgs(self, conversion_workspace_ref, args):
    """Validate flags for conversion workspace.

    Args:
      conversion_workspace_ref: str, the reference of the conversion workspace.
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Raises:
      BadArgumentException: commit-id or filter field is provided without
      specifying the conversion workspace
    """
    if conversion_workspace_ref is None:
      if args.IsKnownAndSpecified('commit_id'):
        raise exceptions.BadArgumentException(
            'commit-id',
            (
                'Conversion workspace commit-id can only be specified for'
                ' migration jobs associated with a conversion workspace.'
            ),
        )
      if args.IsKnownAndSpecified('filter'):
        raise exceptions.BadArgumentException(
            'filter',
            (
                'Filter can only be specified for migration jobs associated'
                ' with a conversion workspace.'
            ),
        )

  def _ValidateConversionWorkspaceMessageArgs(self, conversion_workspace, args):
    """Validate flags for conversion workspace.

    Args:
      conversion_workspace: str, the internal migration job conversion workspace
        message.
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Raises:
      BadArgumentException: commit-id or filter field is provided without
      specifying the conversion workspace
    """
    if conversion_workspace.name is None:
      if args.IsKnownAndSpecified('commit_id'):
        raise exceptions.BadArgumentException(
            'commit-id',
            (
                'Conversion workspace commit-id can only be specified for'
                ' migration jobs associated with a conversion workspace.'
            ),
        )
      if args.IsKnownAndSpecified('filter'):
        raise exceptions.BadArgumentException(
            'filter',
            (
                'Filter can only be specified for migration jobs associated'
                ' with a conversion workspace.'
            ),
        )

  def _GetType(self, mj_type, type_value):
    return mj_type.TypeValueValuesEnum.lookup_by_name(type_value)

  def _GetDumpType(self, dump_type, dump_type_value):
    return dump_type.DumpTypeValueValuesEnum.lookup_by_name(dump_type_value)

  def _GetVpcPeeringConnectivity(self, args):
    return self.messages.VpcPeeringConnectivity(vpc=args.peer_vpc)

  def _GetReverseSshConnectivity(self, args):
    return self.messages.ReverseSshConnectivity(
        vm=args.vm, vmIp=args.vm_ip, vmPort=args.vm_port, vpc=args.vpc
    )

  def _GetStaticIpConnectivity(self):
    return self.messages.StaticIpConnectivity()

  def _UpdateLabels(self, args, migration_job, update_fields):
    """Updates labels of the migration job."""
    add_labels = labels_util.GetUpdateLabelsDictFromArgs(args)
    remove_labels = labels_util.GetRemoveLabelsListFromArgs(args)
    value_type = self.messages.MigrationJob.LabelsValue
    update_result = labels_util.Diff(
        additions=add_labels,
        subtractions=remove_labels,
        clear=args.clear_labels,
    ).Apply(value_type)
    if update_result.needs_update:
      migration_job.labels = update_result.labels
      update_fields.append('labels')

  def _GetConversionWorkspace(self, conversion_workspace_name):
    """Returns the conversion workspace.

    Args:
      conversion_workspace_name: str, the reference of the conversion workspace.

    Raises:
      BadArgumentException: Unable to fetch latest commit for the specified
      conversion workspace.
    """
    cw_client = conversion_workspaces.ConversionWorkspacesClient(
        release_track=self.release_track,
    )
    conversion_workspace = cw_client.crud.Read(
        name=conversion_workspace_name,
    )
    if conversion_workspace.latestCommitId is None:
      raise exceptions.BadArgumentException(
          'conversion-workspace',
          (
              'Unable to fetch latest commit for the specified conversion'
              ' workspace. Conversion Workspace might not be committed.'
          ),
      )
    return conversion_workspace

  def _GetConversionWorkspaceInfo(
      self, conversion_workspace_ref, args
  ):
    """Returns the conversion workspace info.

    Args:
      conversion_workspace_ref: str, the reference of the conversion workspace.
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Raises:
      BadArgumentException: Unable to fetch latest commit for the specified
      conversion workspace.
    """
    conversion_workspace_obj = self.messages.ConversionWorkspaceInfo(
        name=conversion_workspace_ref.RelativeName()
    )
    if args.commit_id is not None:
      conversion_workspace_obj.commitId = args.commit_id
    else:
      conversion_workspace = self._GetConversionWorkspace(
          conversion_workspace_ref.RelativeName()
      )
      conversion_workspace_obj.commitId = conversion_workspace.latestCommitId
    return conversion_workspace_obj

  def _ComplementConversionWorkspaceInfo(self, conversion_workspace, args):
    """Returns the conversion workspace info with the supplied or the latest commit id.

    Args:
      conversion_workspace: the internal migration job conversion workspace
        message.
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Raises:
      BadArgumentException: Unable to fetch latest commit for the specified
      conversion workspace.
      InvalidArgumentException: Invalid conversion workspace message on the
      migration job.
    """
    if conversion_workspace.name is None:
      raise exceptions.InvalidArgumentException(
          'conversion-workspace',
          (
              'The supplied migration job does not have a valid conversion'
              ' workspace attached to it'
          ),
      )
    if args.commit_id is not None:
      conversion_workspace.commitId = args.commit_id
      return conversion_workspace
    # Get conversion workspace's latest commit id.
    cw_client = conversion_workspaces.ConversionWorkspacesClient(
        release_track=self.release_track,
    )
    cst_conversion_workspace = cw_client.crud.Read(
        name=conversion_workspace.name,
    )
    if cst_conversion_workspace.latestCommitId is None:
      raise exceptions.BadArgumentException(
          'conversion-workspace',
          (
              'Unable to fetch latest commit for the specified conversion'
              ' workspace. Conversion Workspace might not be committed.'
          ),
      )
    conversion_workspace.commitId = cst_conversion_workspace.latestCommitId
    return conversion_workspace

  def _GetPerformanceConfig(self, args):
    """Returns the performance config with dump parallel level.

    Args:
      args: argparse.Namespace, the arguments that this command was invoked
        with.
    """
    performance_config_obj = self.messages.PerformanceConfig
    return performance_config_obj(
        dumpParallelLevel=performance_config_obj.DumpParallelLevelValueValuesEnum.lookup_by_name(
            args.dump_parallel_level
        )
    )

  def _GetSqlServerDatabaseBackups(
      self, sqlserver_databases, sqlserver_encrypted_databases
  ):
    """Returns the sqlserver database backups list.

    Args:
      sqlserver_databases: The list of databases to be migrated.
      sqlserver_encrypted_databases: JSON/YAML file for encryption settings for
        encrypted databases.

    Raises:
      Error: Empty list item in JSON/YAML file.
      Error: Encrypted Database name not found in database list.
      Error: Invalid JSON/YAML file.
    """
    database_backups = []
    encrypted_databases_list = []

    if sqlserver_encrypted_databases:
      for database in sqlserver_encrypted_databases:
        if database is None:
          raise Error('Empty list item in JSON/YAML file.')
        if database['database'] not in sqlserver_databases:
          raise Error(
              'Encrypted Database name {dbName} not found in database list.'
              .format(dbName=database['database'])
          )
        try:
          database_backup = encoding.PyValueToMessage(
              self.messages.SqlServerDatabaseBackup,
              database,
          )
        except Exception as e:
          raise Error(e)
        encrypted_databases_list.append(database['database'])
        database_backups.append(database_backup)

    for database in sqlserver_databases:
      if database in encrypted_databases_list:
        continue
      database_backups.append(
          self.messages.SqlServerDatabaseBackup(database=database)
      )
    return database_backups

  def _GetSqlserverHomogeneousMigrationJobConfig(self, args):
    """Returns the sqlserver homogeneous migration job config.

    Args:
      args: argparse.Namespace, the arguments that this command was invoked
        with.
    """
    sqlserver_homogeneous_migration_job_config_obj = (
        self.messages.SqlServerHomogeneousMigrationJobConfig(
            backupFilePattern=args.sqlserver_backup_file_pattern
        )
    )
    if args.IsKnownAndSpecified('sqlserver_diff_backup'):
      sqlserver_homogeneous_migration_job_config_obj.useDiffBackup = (
          args.sqlserver_diff_backup
      )
    if args.IsKnownAndSpecified('sqlserver_promote_when_ready'):
      sqlserver_homogeneous_migration_job_config_obj.promoteWhenReady = (
          args.sqlserver_promote_when_ready
      )
    if args.IsKnownAndSpecified('sqlserver_databases'):
      sqlserver_homogeneous_migration_job_config_obj.databaseBackups = (
          self._GetSqlServerDatabaseBackups(
              args.sqlserver_databases, args.sqlserver_encrypted_databases
          )
      )
    return sqlserver_homogeneous_migration_job_config_obj

  def _GetSourceObjectsConfigForAllDatabases(self):
    """Returns the source objects config."""
    return self.messages.SourceObjectsConfig(
        objectsSelectionType=self.messages.SourceObjectsConfig.ObjectsSelectionTypeValueValuesEnum.ALL_OBJECTS
    )

  def _GetSourceObjectsConfigForSpecifiedDatabases(self, databases_filter):
    """Returns the source objects config."""
    source_objects_conifg = self.messages.SourceObjectsConfig(
        objectsSelectionType=self.messages.SourceObjectsConfig.ObjectsSelectionTypeValueValuesEnum.SPECIFIED_OBJECTS
    )
    source_object_configs = []
    for database in databases_filter:
      source_object_identifier = self.messages.SourceObjectIdentifier(
          database=database,
          type=self.messages.SourceObjectIdentifier.TypeValueValuesEnum.lookup_by_name(
              'DATABASE'
          ),
      )
      source_object_configs.append(
          self.messages.SourceObjectConfig(
              objectIdentifier=source_object_identifier,
          ),
      )
    source_objects_conifg.objectConfigs = source_object_configs
    return source_objects_conifg

  def _GetMigrationJobObjectsConfig(self, args):
    """Returns the migration job objects config.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
        with.
    """
    source_objects_conifg = self.messages.SourceObjectsConfig()

    if args.IsKnownAndSpecified('all_databases'):
      source_objects_conifg = self._GetSourceObjectsConfigForAllDatabases()
    elif args.IsKnownAndSpecified('databases_filter'):
      source_objects_conifg = self._GetSourceObjectsConfigForSpecifiedDatabases(
          args.databases_filter
      )

    return self.messages.MigrationJobObjectsConfig(
        sourceObjectsConfig=source_objects_conifg
    )

  def _IsHeterogeneousConfigKnownAndSpecified(self, args):
    """Checks if at least one heterogeneous config flag is specified.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Returns:
      True if at least one of the heterogeneous config's flags is known and
      specified.
    """
    return (
        args.IsKnownAndSpecified('max_concurrent_full_dump_connections')
        or args.IsKnownAndSpecified('max_concurrent_cdc_connections')
        or args.IsKnownAndSpecified('skip_full_dump')
        or args.IsKnownAndSpecified('oracle_cdc_start_position')
        or args.IsKnownAndSpecified('sqlserver_cdc_start_position')
        or args.IsKnownAndSpecified('max_concurrent_destination_connections')
        or args.IsKnownAndSpecified('transaction_timeout')
    )

  def _GetPostgresDestinationConfig(self, args):
    """Returns the postgres destination config.

    Args:
      args: argparse.Namespace, the arguments that this command was invoked
        with.

    Returns:
      PostgresDestinationConfig: The postgres destination config.
    """
    postgres_destination_config = self.messages.PostgresDestinationConfig()
    if args.IsKnownAndSpecified('max_concurrent_destination_connections'):
      postgres_destination_config.maxConcurrentConnections = (
          args.max_concurrent_destination_connections
      )
    if args.IsKnownAndSpecified('transaction_timeout'):
      postgres_destination_config.transactionTimeout = (
          str(args.transaction_timeout) + 's'
      )
    return postgres_destination_config

  def _GetOracleSourceConfig(self, args):
    """Returns the oracle source config.

    Args:
      args: argparse.Namespace, the arguments that this command was invoked
        with.

    Returns:
      The oracle source config.

    Raises:
      RequiredArgumentException: The Oracle CDC start position should be
      specified when skipping full dump.
    """
    oracle_source_config = self.messages.OracleSourceConfig()
    if args.IsKnownAndSpecified('max_concurrent_full_dump_connections'):
      oracle_source_config.maxConcurrentFullDumpConnections = (
          args.max_concurrent_full_dump_connections
      )
    if args.IsKnownAndSpecified('max_concurrent_cdc_connections'):
      oracle_source_config.maxConcurrentCdcConnections = (
          args.max_concurrent_cdc_connections
      )
    if args.IsKnownAndSpecified('skip_full_dump'):
      oracle_source_config.skipFullDump = args.skip_full_dump
      if args.IsKnownAndSpecified('oracle_cdc_start_position'):
        temp = int(args.oracle_cdc_start_position)
        oracle_source_config.cdcStartPosition = temp
      else:
        raise exceptions.RequiredArgumentException(
            'oracle-cdc-start-position',
            (
                'The Oracle CDC start position should be specified when'
                ' skipping full dump.'
            ),
        )
    return oracle_source_config

  def _GetSqlServerSourceConfig(self, args):
    """Returns the sqlserver source config.

    Args:
      args: argparse.Namespace, the arguments that this command was invoked
        with.

    Returns:
      The sqlserver source config.

    Raises:
      RequiredArgumentException: The SQL Server CDC start position should be
      specified when skipping full dump.
    """
    sqlserver_source_config = self.messages.SqlServerSourceConfig()
    if args.IsKnownAndSpecified('max_concurrent_full_dump_connections'):
      sqlserver_source_config.maxConcurrentFullDumpConnections = (
          args.max_concurrent_full_dump_connections
      )
    if args.IsKnownAndSpecified('max_concurrent_cdc_connections'):
      sqlserver_source_config.maxConcurrentCdcConnections = (
          args.max_concurrent_cdc_connections
      )
    if args.IsKnownAndSpecified('skip_full_dump'):
      sqlserver_source_config.skipFullDump = args.skip_full_dump
      if args.IsKnownAndSpecified('sqlserver_cdc_start_position'):
        sqlserver_source_config.sqlserverCdcStartPosition = (
            args.sqlserver_cdc_start_position
        )
      else:
        raise exceptions.RequiredArgumentException(
            'sqlserver-cdc-start-position',
            (
                'The SQL Server CDC start position should be specified when'
                ' skipping full dump.'
            ),
        )
    return sqlserver_source_config

  def _GetHeterogeneousMigrationJobConfig(
      self, conversion_workspace_name, args
  ):
    """Returns the heterogeneous migration job config.

    Args:
      conversion_workspace_name: str, the name of the conversion workspace.
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Returns:
      A tuple containing the heterogeneous config key and the config object.

    Raises:
      Error: Invalid source or destination engine.
    """
    if self._IsHeterogeneousConfigKnownAndSpecified(args):
      conversion_workspace = self._GetConversionWorkspace(
          conversion_workspace_name
      )
      if (
          conversion_workspace.destination.engine
          == self.messages.DatabaseEngineInfo.EngineValueValuesEnum.POSTGRESQL
      ):
        postgres_destination_config = self._GetPostgresDestinationConfig(
            args
        )
      else:
        raise Error(
            'Cannot create heterogeneous migration job configuration for '
            'destination engine: {engine}'.format(
                engine=conversion_workspace.destination.engine
            )
        )
      if (
          conversion_workspace.source.engine
          == self.messages.DatabaseEngineInfo.EngineValueValuesEnum.ORACLE
      ):
        oracle_to_postgres_config = self.messages.OracleToPostgresConfig(
            oracleSourceConfig=self._GetOracleSourceConfig(args),
            postgresDestinationConfig=postgres_destination_config
            )
        return 'oracleToPostgresConfig', oracle_to_postgres_config
      elif (
          conversion_workspace.source.engine
          == self.messages.DatabaseEngineInfo.EngineValueValuesEnum.SQLSERVER
      ):
        sqlserver_to_postgres_config = self.messages.SqlServerToPostgresConfig(
            sqlserverSourceConfig=self._GetSqlServerSourceConfig(args),
            postgresDestinationConfig=postgres_destination_config
            )
        return 'sqlserverToPostgresConfig', sqlserver_to_postgres_config
      else:
        raise Error(
            'Cannot create heterogeneous migration job configuration for '
            ' source engine: {engine}'.format(
                engine=conversion_workspace.source.engine
            ),
        )
    return None, None

  def _GetMigrationJob(
      self,
      source_ref,
      destination_ref,
      conversion_workspace_ref,
      cmek_key_ref,
      args,
  ):
    """Returns a migration job.

    Args:
      source_ref: a Resource reference to a
        datamigration.projects.locations.connectionProfiles resource.
      destination_ref: a Resource reference to a
        datamigration.projects.locations.connectionProfiles resource.
      conversion_workspace_ref: a Resource reference to a
        datamigration.projects.locations.conversionWorkspaces resource.
      cmek_key_ref: a Resource reference to a
        cloudkms.projects.locations.keyRings.cryptoKeys resource.
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Returns:
      MigrationJob: the migration job.

    Raises:
      RequiredArgumentException: If conversion workspace is not specified for
      heterogeneous migration job.
    """
    migration_job_type = self.messages.MigrationJob
    labels = labels_util.ParseCreateArgs(
        args, self.messages.MigrationJob.LabelsValue
    )
    type_value = self._GetType(migration_job_type, args.type)
    source = source_ref.RelativeName()
    destination = destination_ref.RelativeName()
    params = {}
    if args.IsSpecified('peer_vpc'):
      params['vpcPeeringConnectivity'] = self._GetVpcPeeringConnectivity(args)
    elif args.IsSpecified('vm_ip'):
      params['reverseSshConnectivity'] = self._GetReverseSshConnectivity(args)
    elif args.IsSpecified('static_ip'):
      params['staticIpConnectivity'] = self._GetStaticIpConnectivity()

    if args.IsSpecified('dump_flags'):
      params['dumpFlags'] = self._GetDumpFlags(args.dump_flags)

    if conversion_workspace_ref is not None:
      params['conversionWorkspace'] = self._GetConversionWorkspaceInfo(
          conversion_workspace_ref, args
      )
      heterogeneous_config_key, heterogeneous_config_obj = (
          self._GetHeterogeneousMigrationJobConfig(
              conversion_workspace_ref.RelativeName(), args
          )
      )
      if heterogeneous_config_key is not None:
        params[heterogeneous_config_key] = heterogeneous_config_obj
    else:
      if self._IsHeterogeneousConfigKnownAndSpecified(args):
        raise exceptions.RequiredArgumentException(
            'conversion-workspace',
            (
                'Conversion workspace is required for heterogeneous migration'
                ' job.'
            ),
        )

    migration_job_obj = migration_job_type(
        labels=labels,
        displayName=args.display_name,
        state=migration_job_type.StateValueValuesEnum.CREATING,
        type=type_value,
        dumpPath=args.dump_path,
        source=source,
        destination=destination,
        **params
    )
    if cmek_key_ref is not None:
      migration_job_obj.cmekKeyName = cmek_key_ref.RelativeName()

    if args.IsKnownAndSpecified('filter'):
      args.filter, server_filter = filter_rewrite.Rewriter().Rewrite(
          args.filter
      )
      migration_job_obj.filter = server_filter

    if args.IsKnownAndSpecified('dump_parallel_level'):
      migration_job_obj.performanceConfig = self._GetPerformanceConfig(args)

    if args.IsKnownAndSpecified('dump_type'):
      migration_job_obj.dumpType = self._GetDumpType(
          self.messages.MigrationJob, args.dump_type
      )

    if args.IsKnownAndSpecified('sqlserver_databases'):
      migration_job_obj.sqlserverHomogeneousMigrationJobConfig = (
          self._GetSqlserverHomogeneousMigrationJobConfig(args)
      )

    if args.IsKnownAndSpecified('databases_filter') or args.IsKnownAndSpecified(
        'all_databases'
    ):
      migration_job_obj.objectsConfig = self._GetMigrationJobObjectsConfig(args)

    return migration_job_obj

  def _UpdateHeterogeneousMigrationJobConfigUpdateFields(
      self, args, update_fields, source_engine, destination_engine
  ):
    """Update the heterogeneous migration job config update fields."""
    config_key = '{}To{}Config'.format(
        source_engine, destination_engine.title()
    )
    source_config_key = '{}.{}SourceConfig'.format(config_key, source_engine)
    destination_config_key = '{}.{}DestinationConfig'.format(
        config_key, destination_engine
    )
    if args.IsKnownAndSpecified('max_concurrent_full_dump_connections'):
      update_fields.append(
          '{}.maxConcurrentFullDumpConnections'.format(source_config_key)
      )
    if args.IsKnownAndSpecified('max_concurrent_cdc_connections'):
      update_fields.append(
          '{}.maxConcurrentCdcConnections'.format(source_config_key)
      )
    if args.IsKnownAndSpecified('max_concurrent_destination_connections'):
      update_fields.append(
          '{}.maxConcurrentDestinationConnections'.format(
              destination_config_key
          )
      )
    if args.IsKnownAndSpecified('transaction_timeout'):
      update_fields.append(
          '{}.transactionTimeout'.format(destination_config_key)
      )

  def _UpdateHeterogeneousMigrationJobConfig(
      self, args, migration_job, update_fields
  ):
    """Update the heterogeneous migration job config for the migration job."""
    heterogeneous_config_key, heterogeneous_config_obj = (
        self._GetHeterogeneousMigrationJobConfig(
            migration_job.conversionWorkspace.name, args
        )
    )
    if heterogeneous_config_key == 'oracleToPostgresConfig':
      migration_job.oracleToPostgresConfig = heterogeneous_config_obj
      self._UpdateHeterogeneousMigrationJobConfigUpdateFields(
          args,
          update_fields,
          'oracle',
          'postgres',
      )
    elif heterogeneous_config_key == 'sqlserverToPostgresConfig':
      migration_job.sqlserverToPostgresConfig = heterogeneous_config_obj
      self._UpdateHeterogeneousMigrationJobConfigUpdateFields(
          args,
          update_fields,
          'sqlserver',
          'postgres',
      )
    else:
      raise Error(
          'Cannot update heterogeneous migration job configuration for '
          'source engine: {source_engine} and destination engine: '
          '{destination_engine}'.format(
              source_engine=migration_job.conversionWorkspace.source.engine,
              destination_engine=migration_job.conversionWorkspace.destination.engine,
          )
      )

  def _UpdateConnectivity(self, migration_job, args):
    """Update connectivity method for the migration job."""
    if args.IsSpecified('static_ip'):
      migration_job.staticIpConnectivity = self._GetStaticIpConnectivity()
      migration_job.vpcPeeringConnectivity = None
      migration_job.reverseSshConnectivity = None
      return

    if args.IsSpecified('peer_vpc'):
      migration_job.vpcPeeringConnectivity = self._GetVpcPeeringConnectivity(
          args
      )
      migration_job.reverseSshConnectivity = None
      migration_job.staticIpConnectivity = None
      return

    for field in self._REVERSE_MAP:
      if args.IsSpecified(field):
        migration_job.reverseSshConnectivity = self._GetReverseSshConnectivity(
            args
        )
        migration_job.vpcPeeringConnectivity = None
        migration_job.staticIpConnectivity = None
        return

  def _UpdateSqlserverHomogeneousMigrationJobConfig(self, args, migration_job):
    """Update the sqlserver homogeneous migration job config for the migration job."""

    if migration_job.sqlserverHomogeneousMigrationJobConfig is None:
      raise Error(
          'Cannot update sqlserver homogeneous migration job config when it was'
          ' not set during creation of the migration job.'
      )

    sqlserver_homogeneous_migration_job_config_obj = (
        migration_job.sqlserverHomogeneousMigrationJobConfig
    )

    if args.IsKnownAndSpecified('sqlserver_backup_file_pattern'):
      sqlserver_homogeneous_migration_job_config_obj.backupFilePattern = (
          args.sqlserver_backup_file_pattern
      )
    if args.IsKnownAndSpecified('sqlserver_diff_backup'):
      sqlserver_homogeneous_migration_job_config_obj.useDiffBackup = (
          args.sqlserver_diff_backup
      )
    if args.IsKnownAndSpecified('sqlserver_promote_when_ready'):
      sqlserver_homogeneous_migration_job_config_obj.promoteWhenReady = (
          args.sqlserver_promote_when_ready
      )
    if args.IsKnownAndSpecified('sqlserver_databases'):
      sqlserver_homogeneous_migration_job_config_obj.databaseBackups = (
          self._GetSqlServerDatabaseBackups(
              args.sqlserver_databases, args.sqlserver_encrypted_databases
          )
      )
    elif args.IsKnownAndSpecified('sqlserver_encrypted_databases'):
      raise exceptions.InvalidArgumentException(
          '--sqlserver-encrypted-databases',
          '--sqlserver-encrypted-databases can only be specified when'
          ' --sqlserver-databases is specified.',
      )

  def _UpdateMigrationJobObjectsConfig(self, args, migration_job):
    """Update the migration job objects config for the migration job."""

    if args.IsKnownAndSpecified('databases_filter') or args.IsKnownAndSpecified(
        'all_databases'
    ):
      migration_job.objectsConfig = self._GetMigrationJobObjectsConfig(args)

  def _GetUpdateMask(self, args):
    """Returns update mask for specified fields."""
    update_fields = [
        resource_property.ConvertToCamelCase(field)
        for field in sorted(self._FIELDS_MAP)
        if args.IsSpecified(field)
    ]
    update_fields.extend([
        'reverseSshConnectivity.{0}'.format(
            resource_property.ConvertToCamelCase(field)
        )
        for field in sorted(self._REVERSE_MAP)
        if args.IsSpecified(field)
    ])
    if args.IsSpecified('peer_vpc'):
      update_fields.append('vpcPeeringConnectivity.vpc')
    if args.IsKnownAndSpecified('dump_parallel_level'):
      update_fields.append('performanceConfig.dumpParallelLevel')
    if args.IsKnownAndSpecified('dump_type'):
      update_fields.append('dumpType')
    if args.IsKnownAndSpecified('filter'):
      update_fields.append('filter')
    if args.IsKnownAndSpecified('commit_id') or args.IsKnownAndSpecified(
        'filter'
    ):
      update_fields.append('conversionWorkspace.commitId')

    if args.IsKnownAndSpecified('sqlserver_backup_file_pattern'):
      update_fields.append(
          'sqlserverHomogeneousMigrationJobConfig.backupFilePattern'
      )
    if args.IsKnownAndSpecified('sqlserver_diff_backup'):
      update_fields.append(
          'sqlserverHomogeneousMigrationJobConfig.useDiffBackup'
      )
    if args.IsKnownAndSpecified('sqlserver_promote_when_ready'):
      update_fields.append(
          'sqlserverHomogeneousMigrationJobConfig.promoteWhenReady'
      )
    if args.IsKnownAndSpecified(
        'sqlserver_databases'
    ) or args.IsKnownAndSpecified('sqlserver_encrypted_databases'):
      update_fields.append(
          'sqlserverHomogeneousMigrationJobConfig.databaseBackups'
      )
    if args.IsKnownAndSpecified('databases_filter') or args.IsKnownAndSpecified(
        'all_databases'
    ):
      update_fields.append('objectsConfig.sourceObjectsConfig')
    return update_fields

  def _GetDumpFlags(self, dump_flags):
    """Returns the dump flags for the migration job."""
    dump_flags_list = []
    for name, value in dump_flags.items():
      dump_flags_list.append(
          self.messages.DumpFlag(
              name=name,
              value=value,
          )
      )
    return self.messages.DumpFlags(dumpFlags=dump_flags_list)

  def _GetUpdatedMigrationJob(
      self, migration_job, source_ref, destination_ref, args
  ):
    """Returns updated migration job and list of updated fields."""
    update_fields = self._GetUpdateMask(args)
    if args.IsSpecified('display_name'):
      migration_job.displayName = args.display_name
    if args.IsSpecified('type'):
      migration_job.type = self._GetType(self.messages.MigrationJob, args.type)
    if args.IsKnownAndSpecified('dump_type'):
      migration_job.dumpType = self._GetDumpType(
          self.messages.MigrationJob, args.dump_type
      )
    if args.IsSpecified('dump_path'):
      migration_job.dumpPath = args.dump_path
    if args.IsSpecified('dump_flags'):
      migration_job.dumpFlags = self._GetDumpFlags(args.dump_flags)
    if args.IsSpecified('source'):
      migration_job.source = source_ref.RelativeName()
    if args.IsSpecified('destination'):
      migration_job.destination = destination_ref.RelativeName()
    if args.IsKnownAndSpecified('dump_parallel_level'):
      migration_job.performanceConfig = self._GetPerformanceConfig(args)
    if args.IsKnownAndSpecified('filter'):
      args.filter, server_filter = filter_rewrite.Rewriter().Rewrite(
          args.filter
      )
      migration_job.filter = server_filter
    self._UpdateConnectivity(migration_job, args)
    self._UpdateLabels(args, migration_job, update_fields)
    if (
        args.IsKnownAndSpecified('sqlserver_backup_file_pattern')
        or args.IsKnownAndSpecified('sqlserver_diff_backup')
        or args.IsKnownAndSpecified('sqlserver_promote_when_ready')
        or args.IsKnownAndSpecified('sqlserver_databases')
        or args.IsKnownAndSpecified('sqlserver_encrypted_databases')
    ):
      self._UpdateSqlserverHomogeneousMigrationJobConfig(args, migration_job)

    self._UpdateMigrationJobObjectsConfig(args, migration_job)

    if self._IsHeterogeneousConfigKnownAndSpecified(args):
      self._UpdateHeterogeneousMigrationJobConfig(
          args, migration_job, update_fields
      )

    return migration_job, update_fields

  def _GetExistingMigrationJob(self, name):
    get_req = (
        self.messages.DatamigrationProjectsLocationsMigrationJobsGetRequest(
            name=name
        )
    )
    return self._service.Get(get_req)

  def Create(
      self,
      parent_ref,
      migration_job_id,
      source_ref,
      destination_ref,
      conversion_workspace_ref=None,
      cmek_key_ref=None,
      args=None,
  ):
    """Creates a migration job.

    Args:
      parent_ref: a Resource reference to a parent
        datamigration.projects.locations resource for this migration job.
      migration_job_id: str, the name of the resource to create.
      source_ref: a Resource reference to a
        datamigration.projects.locations.connectionProfiles resource.
      destination_ref: a Resource reference to a
        datamigration.projects.locations.connectionProfiles resource.
      conversion_workspace_ref: a Resource reference to a
        datamigration.projects.locations.conversionWorkspaces resource.
      cmek_key_ref: a Resource reference to a
        cloudkms.projects.locations.keyRings.cryptoKeys resource.
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Returns:
      Operation: the operation for creating the migration job.
    """
    self._ValidateArgs(args)
    self._ValidateConversionWorkspaceArgs(conversion_workspace_ref, args)

    migration_job = self._GetMigrationJob(
        source_ref,
        destination_ref,
        conversion_workspace_ref,
        cmek_key_ref,
        args,
    )

    request_id = api_util.GenerateRequestId()
    create_req_type = (
        self.messages.DatamigrationProjectsLocationsMigrationJobsCreateRequest
    )
    create_req = create_req_type(
        migrationJob=migration_job,
        migrationJobId=migration_job_id,
        parent=parent_ref,
        requestId=request_id,
    )

    return self._service.Create(create_req)

  def Update(self, name, source_ref, destination_ref, args=None):
    """Updates a migration job.

    Args:
      name: str, the reference of the migration job to update.
      source_ref: a Resource reference to a
        datamigration.projects.locations.connectionProfiles resource.
      destination_ref: a Resource reference to a
        datamigration.projects.locations.connectionProfiles resource.
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Returns:
      Operation: the operation for updating the migration job.678888888
    """
    self._ValidateArgs(args)

    current_mj = self._GetExistingMigrationJob(name)

    # since this property doesn't exist in older api versions
    if (
        hasattr(current_mj, 'conversionWorkspace')
        and current_mj.conversionWorkspace is not None
    ):
      self._ValidateConversionWorkspaceMessageArgs(
          current_mj.conversionWorkspace, args
      )

      current_mj.conversionWorkspace = self._ComplementConversionWorkspaceInfo(
          current_mj.conversionWorkspace, args
      )

    migration_job, update_fields = self._GetUpdatedMigrationJob(
        current_mj, source_ref, destination_ref, args
    )

    request_id = api_util.GenerateRequestId()
    update_req_type = (
        self.messages.DatamigrationProjectsLocationsMigrationJobsPatchRequest
    )
    update_req = update_req_type(
        migrationJob=migration_job,
        name=name,
        requestId=request_id,
        updateMask=','.join(update_fields),
    )

    return self._service.Patch(update_req)

  def Promote(
      self,
      name,
      args=None,
  ):
    """Promotes a migration job.

    Args:
      name: str, the name of the resource to promote.
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Returns:
      Operation: the operation for promoting the migration job.
    """
    promote_mj_req = self.messages.PromoteMigrationJobRequest()
    if args.IsKnownAndSpecified('databases_filter'):
      promote_mj_req.objectsFilter = self._GetMigrationJobObjectsConfig(args)

    promote_req = (
        self.messages.DatamigrationProjectsLocationsMigrationJobsPromoteRequest(
            name=name,
            promoteMigrationJobRequest=promote_mj_req,
        )
    )

    return self._service.Promote(promote_req)

  def Restart(
      self,
      name,
      args=None,
  ):
    """Restarts a migration job.

    Args:
      name: str, the name of the resource to restart.
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Returns:
      Operation: the operation for promoting the migration job.
    """
    restart_mj_req = self.messages.RestartMigrationJobRequest()
    if args.IsKnownAndSpecified('databases_filter'):
      restart_mj_req.objectsFilter = self._GetMigrationJobObjectsConfig(args)
    if args.IsKnownAndSpecified('skip_validation'):
      restart_mj_req.skipValidation = True
    if args.IsKnownAndSpecified('restart_failed_objects'):
      restart_mj_req.restartFailedObjects = True

    restart_req = (
        self.messages.DatamigrationProjectsLocationsMigrationJobsRestartRequest(
            name=name,
            restartMigrationJobRequest=restart_mj_req,
        )
    )

    return self._service.Restart(restart_req)

  def FetchSourceObjects(
      self,
      name,
  ):
    """Fetches source objects of a migration job.

    Args:
      name: str, the name of the resource to fetch source objects for.

    Returns:
      Operation: the operation for fetching source objects of the migration job.
    """
    fetch_source_objects_req = self.messages.DatamigrationProjectsLocationsMigrationJobsFetchSourceObjectsRequest(
        name=name,
    )

    return self._service.FetchSourceObjects(fetch_source_objects_req)

  def ListObjects(self, migration_job_ref):
    """Get the list of objects in a migration job.

    Args:
      migration_job_ref: The migration job for which to list objects.

    Returns:
      An iterator over all the matching migration job objects.
    """
    list_req_type = (
        self.messages.DatamigrationProjectsLocationsMigrationJobsObjectsListRequest
    )
    list_req = list_req_type(parent=migration_job_ref.RelativeName())

    return list_pager.YieldFromList(
        service=self._service_objects,
        request=list_req,
        limit=None,
        batch_size=None,
        field='migrationJobObjects',
        batch_size_attribute=None,
    )
