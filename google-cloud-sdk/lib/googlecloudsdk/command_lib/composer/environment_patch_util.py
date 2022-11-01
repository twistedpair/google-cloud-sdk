# -*- coding: utf-8 -*- #
# Copyright 2018 Google LLC. All Rights Reserved.
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
"""Common utility functions for Composer environment patch commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.composer import environments_util as environments_api_util
from googlecloudsdk.api_lib.composer import operations_util as operations_api_util
from googlecloudsdk.api_lib.composer import util as api_util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.composer import util as command_util
from googlecloudsdk.core import log
import six


def _ConstructAirflowDatabaseRetentionDaysPatch(airflow_database_retention_days,
                                                release_track):
  """Constructs an environment patch for Airflow Database Retention feature.

  Args:
    airflow_database_retention_days: int or None, the number of retention days
      for airflow database data retention mechanism
    release_track: base.ReleaseTrack, the release track of command. It dictates
      which Composer client library is used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  config = messages.EnvironmentConfig()
  config.dataRetentionConfig = messages.DataRetentionConfig(
      airflowDatabaseRetentionDays=airflow_database_retention_days)
  return ('config.data_retention_configuration.airflow_database_retention_days',
          messages.Environment(config=config))


def Patch(env_resource,
          field_mask,
          patch,
          is_async,
          release_track=base.ReleaseTrack.GA):
  """Patches an Environment, optionally waiting for the operation to complete.

  This function is intended to perform the common work of an Environment
  patching command's Run method. That is, calling the patch API method and
  waiting for the result or immediately returning the Operation.

  Args:
    env_resource: googlecloudsdk.core.resources.Resource, Resource representing
      the Environment to be patched
    field_mask: str, a field mask string containing comma-separated paths to be
      patched
    patch: Environment, a patch Environment containing updated values to apply
    is_async: bool, whether or not to perform the patch asynchronously
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    an Operation corresponding to the Patch call if `is_async` is True;
    otherwise None is returned after the operation is complete

  Raises:
    command_util.Error: if `is_async` is False and the operation encounters
    an error
  """
  operation = environments_api_util.Patch(
      env_resource, patch, field_mask, release_track=release_track)
  details = 'with operation [{0}]'.format(operation.name)
  if is_async:
    log.UpdatedResource(
        env_resource.RelativeName(),
        kind='environment',
        is_async=True,
        details=details)
    return operation

  try:
    operations_api_util.WaitForOperation(
        operation,
        'Waiting for [{}] to be updated with [{}]'.format(
            env_resource.RelativeName(), operation.name),
        release_track=release_track)
  except command_util.Error as e:
    raise command_util.Error('Error updating [{}]: {}'.format(
        env_resource.RelativeName(), six.text_type(e)))


def ConstructPatch(is_composer_v1,
                   env_ref=None,
                   node_count=None,
                   update_pypi_packages_from_file=None,
                   clear_pypi_packages=None,
                   remove_pypi_packages=None,
                   update_pypi_packages=None,
                   clear_labels=None,
                   remove_labels=None,
                   update_labels=None,
                   clear_airflow_configs=None,
                   remove_airflow_configs=None,
                   update_airflow_configs=None,
                   clear_env_variables=None,
                   remove_env_variables=None,
                   update_env_variables=None,
                   update_image_version=None,
                   update_web_server_access_control=None,
                   cloud_sql_machine_type=None,
                   web_server_machine_type=None,
                   scheduler_cpu=None,
                   worker_cpu=None,
                   web_server_cpu=None,
                   scheduler_memory_gb=None,
                   worker_memory_gb=None,
                   web_server_memory_gb=None,
                   scheduler_storage_gb=None,
                   worker_storage_gb=None,
                   web_server_storage_gb=None,
                   min_workers=None,
                   max_workers=None,
                   scheduler_count=None,
                   maintenance_window_start=None,
                   maintenance_window_end=None,
                   maintenance_window_recurrence=None,
                   environment_size=None,
                   master_authorized_networks_enabled=None,
                   master_authorized_networks=None,
                   airflow_database_retention_days=None,
                   release_track=base.ReleaseTrack.GA,
                   triggerer_cpu=None,
                   triggerer_memory_gb=None,
                   triggerer_count=None,
                   enable_scheduled_snapshot_creation=None,
                   snapshot_location=None,
                   snapshot_schedule_timezone=None,
                   snapshot_creation_schedule=None,
                   cloud_data_lineage_integration_enabled=None):
  """Constructs an environment patch.

  Args:
    is_composer_v1: boolean representing if patch request is for Composer 1.*.*
      Environment.
    env_ref: resource argument, Environment resource argument for environment
      being updated.
    node_count: int, the desired node count
    update_pypi_packages_from_file: str, path to local requirements file
      containing desired pypi dependencies.
    clear_pypi_packages: bool, whether to uninstall all PyPI packages.
    remove_pypi_packages: iterable(string), Iterable of PyPI packages to
      uninstall.
    update_pypi_packages: {string: string}, dict mapping PyPI package name to
      extras and version specifier.
    clear_labels: bool, whether to clear the labels dictionary.
    remove_labels: iterable(string), Iterable of label names to remove.
    update_labels: {string: string}, dict of label names and values to set.
    clear_airflow_configs: bool, whether to clear the Airflow configs
      dictionary.
    remove_airflow_configs: iterable(string), Iterable of Airflow config
      property names to remove.
    update_airflow_configs: {string: string}, dict of Airflow config property
      names and values to set.
    clear_env_variables: bool, whether to clear the environment variables
      dictionary.
    remove_env_variables: iterable(string), Iterable of environment variables to
      remove.
    update_env_variables: {string: string}, dict of environment variable names
      and values to set.
    update_image_version: string, image version to use for environment upgrade
    update_web_server_access_control: [{string: string}], Webserver access
      control to set
    cloud_sql_machine_type: str or None, Cloud SQL machine type used by the
      Airflow database.
    web_server_machine_type: str or None, machine type used by the Airflow web
      server
    scheduler_cpu: float or None, CPU allocated to Airflow scheduler. Can be
      specified only in Composer 2.0.0.
    worker_cpu: float or None, CPU allocated to each Airflow worker. Can be
      specified only in Composer 2.0.0.
    web_server_cpu: float or None, CPU allocated to Airflow web server. Can be
      specified only in Composer 2.0.0.
    scheduler_memory_gb: float or None, memory allocated to Airflow scheduler.
      Can be specified only in Composer 2.0.0.
    worker_memory_gb: float or None, memory allocated to each Airflow worker.
      Can be specified only in Composer 2.0.0.
    web_server_memory_gb: float or None, memory allocated to Airflow web server.
      Can be specified only in Composer 2.0.0.
    scheduler_storage_gb: float or None, storage allocated to Airflow scheduler.
      Can be specified only in Composer 2.0.0.
    worker_storage_gb: float or None, storage allocated to each Airflow worker.
      Can be specified only in Composer 2.0.0.
    web_server_storage_gb: float or None, storage allocated to Airflow web
      server. Can be specified only in Composer 2.0.0.
    min_workers: int or None, minimum number of workers in the Environment. Can
      be specified only in Composer 2.0.0.
    max_workers: int or None, maximumn number of workers in the Environment. Can
      be specified only in Composer 2.0.0.
    scheduler_count: int or None, number of schedulers in the Environment. Can
      be specified only in Composer 2.0.0.
    maintenance_window_start: Datetime or None, a starting date of the
      maintenance window.
    maintenance_window_end: Datetime or None, an ending date of the maintenance
      window.
    maintenance_window_recurrence: str or None, recurrence RRULE for the
      maintenance window.
    environment_size: str or None, one of small, medium and large.
    master_authorized_networks_enabled: bool or None, whether the feature should
      be enabled
    master_authorized_networks: iterable(string) or None, iterable of master
      authorized networks.
    airflow_database_retention_days: Optional[int], the number of retention days
      for airflow database data retention mechanism. Infinite retention will be
      applied in case `0` or no integer is provided.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.
    triggerer_cpu: float or None, CPU allocated to Airflow triggerer. Can be
      specified only in Airflow 2.2.x and greater.
    triggerer_memory_gb: float or None, memory allocated to Airflow triggerer.
      Can be specified only in Airflow 2.2.x and greater.
    triggerer_count: int or None, number of triggerers in the Environment. Can
      be specified only in Airflow 2.2.x and greater
    enable_scheduled_snapshot_creation: bool, whether the automatic snapshot
      creation should be enabled
    snapshot_location: str, a Cloud Storage location used to store automatically
      created snapshots
    snapshot_schedule_timezone: str, time zone that sets the context to
      interpret snapshot_creation_schedule.
    snapshot_creation_schedule: str, cron expression that specifies when
      snapshots will be created
    cloud_data_lineage_integration_enabled: bool or None, whether the feature
      should be enabled

  Returns:
    (str, Environment), the field mask and environment to use for update.

  Raises:
    command_util.Error: if no update type is specified
  """
  if node_count:
    return _ConstructNodeCountPatch(node_count, release_track=release_track)
  if environment_size:
    return _ConstructEnvironmentSizePatch(
        environment_size, release_track=release_track)
  if update_pypi_packages_from_file:
    return _ConstructPyPiPackagesPatch(
        True, [],
        command_util.ParseRequirementsFile(update_pypi_packages_from_file),
        release_track=release_track)
  if clear_pypi_packages or remove_pypi_packages or update_pypi_packages:
    return _ConstructPyPiPackagesPatch(
        clear_pypi_packages,
        remove_pypi_packages,
        update_pypi_packages,
        release_track=release_track)
  if clear_labels or remove_labels or update_labels:
    return _ConstructLabelsPatch(
        clear_labels, remove_labels, update_labels, release_track=release_track)
  if (clear_airflow_configs or remove_airflow_configs or
      update_airflow_configs):
    return _ConstructAirflowConfigsPatch(
        clear_airflow_configs,
        remove_airflow_configs,
        update_airflow_configs,
        release_track=release_track)
  if clear_env_variables or remove_env_variables or update_env_variables:
    return _ConstructEnvVariablesPatch(
        env_ref,
        clear_env_variables,
        remove_env_variables,
        update_env_variables,
        release_track=release_track)
  if update_image_version:
    return _ConstructImageVersionPatch(
        update_image_version, release_track=release_track)
  if update_web_server_access_control is not None:
    return _ConstructWebServerAccessControlPatch(
        update_web_server_access_control, release_track=release_track)
  if cloud_sql_machine_type:
    return _ConstructCloudSqlMachineTypePatch(
        cloud_sql_machine_type, release_track=release_track)
  if web_server_machine_type:
    return _ConstructWebServerMachineTypePatch(
        web_server_machine_type, release_track=release_track)
  if master_authorized_networks_enabled is not None:
    return _ConstructMasterAuthorizedNetworksTypePatch(
        master_authorized_networks_enabled, master_authorized_networks,
        release_track)
  if enable_scheduled_snapshot_creation is not None:
    return _ConstructScheduledSnapshotPatch(enable_scheduled_snapshot_creation,
                                            snapshot_creation_schedule,
                                            snapshot_location,
                                            snapshot_schedule_timezone,
                                            release_track)
  if airflow_database_retention_days is not None:
    return _ConstructAirflowDatabaseRetentionDaysPatch(
        airflow_database_retention_days, release_track)
  if is_composer_v1 and scheduler_count:
    return _ConstructSoftwareConfigurationSchedulerCountPatch(
        scheduler_count=scheduler_count, release_track=release_track)
  if (scheduler_cpu or worker_cpu or web_server_cpu or scheduler_memory_gb or
      worker_memory_gb or web_server_memory_gb or scheduler_storage_gb or
      worker_storage_gb or web_server_storage_gb or min_workers or
      max_workers or scheduler_count or triggerer_cpu or triggerer_memory_gb or
      triggerer_count is not None):
    if is_composer_v1:
      raise command_util.Error(
          'You cannot use Workloads Config flags introduced in Composer 2.X'
          ' when updating Composer 1.X environments.')
    else:
      return _ConstructAutoscalingPatch(
          scheduler_cpu=scheduler_cpu,
          worker_cpu=worker_cpu,
          web_server_cpu=web_server_cpu,
          scheduler_memory_gb=scheduler_memory_gb,
          worker_memory_gb=worker_memory_gb,
          web_server_memory_gb=web_server_memory_gb,
          scheduler_storage_gb=scheduler_storage_gb,
          worker_storage_gb=worker_storage_gb,
          web_server_storage_gb=web_server_storage_gb,
          worker_min_count=min_workers,
          worker_max_count=max_workers,
          scheduler_count=scheduler_count,
          release_track=release_track,
          triggerer_cpu=triggerer_cpu,
          triggerer_memory_gb=triggerer_memory_gb,
          triggerer_count=triggerer_count)
  if maintenance_window_start and maintenance_window_end and maintenance_window_recurrence:
    return _ConstructMaintenanceWindowPatch(
        maintenance_window_start,
        maintenance_window_end,
        maintenance_window_recurrence,
        release_track=release_track)
  if cloud_data_lineage_integration_enabled is not None:
    return _ConstructSoftwareConfigurationCloudDataLineageIntegrationPatch(
        cloud_data_lineage_integration_enabled, release_track)
  raise command_util.Error(
      'Cannot update Environment with no update type specified.')


def _ConstructNodeCountPatch(node_count, release_track=base.ReleaseTrack.GA):
  """Constructs an environment patch for node count.

  Args:
    node_count: int, the desired node count
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  config = messages.EnvironmentConfig(nodeCount=node_count)
  return 'config.node_count', messages.Environment(config=config)


def _ConstructEnvironmentSizePatch(environment_size,
                                   release_track=base.ReleaseTrack.GA):
  """Constructs an environment patch for environment size.

  Args:
    environment_size: str, the desired environment size.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  config = messages.EnvironmentConfig(environmentSize=environment_size)
  return 'config.environment_size', messages.Environment(config=config)


def _ConstructPyPiPackagesPatch(clear_pypi_packages,
                                remove_pypi_packages,
                                update_pypi_packages,
                                release_track=base.ReleaseTrack.GA):
  """Constructs an environment patch for partially updating PyPI packages.

  Args:
    clear_pypi_packages: bool, whether to clear the PyPI packages dictionary.
    remove_pypi_packages: iterable(string), Iterable of PyPI package names to
      remove.
    update_pypi_packages: {string: string}, dict mapping PyPI package name to
      optional extras and version specifier.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  env_cls = messages.Environment
  pypi_packages_cls = (messages.SoftwareConfig.PypiPackagesValue)
  entry_cls = pypi_packages_cls.AdditionalProperty

  def _BuildEnv(entries):
    software_config = messages.SoftwareConfig(
        pypiPackages=pypi_packages_cls(additionalProperties=entries))
    config = messages.EnvironmentConfig(softwareConfig=software_config)
    return env_cls(config=config)

  return command_util.BuildPartialUpdate(
      clear_pypi_packages, remove_pypi_packages, update_pypi_packages,
      'config.software_config.pypi_packages', entry_cls, _BuildEnv)


def _ConstructLabelsPatch(clear_labels,
                          remove_labels,
                          update_labels,
                          release_track=base.ReleaseTrack.GA):
  """Constructs an environment patch for updating labels.

  Args:
    clear_labels: bool, whether to clear the labels dictionary.
    remove_labels: iterable(string), Iterable of label names to remove.
    update_labels: {string: string}, dict of label names and values to set.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  env_cls = messages.Environment
  entry_cls = env_cls.LabelsValue.AdditionalProperty

  def _BuildEnv(entries):
    return env_cls(labels=env_cls.LabelsValue(additionalProperties=entries))

  return command_util.BuildPartialUpdate(clear_labels, remove_labels,
                                         update_labels, 'labels', entry_cls,
                                         _BuildEnv)


def _ConstructAirflowConfigsPatch(clear_airflow_configs,
                                  remove_airflow_configs,
                                  update_airflow_configs,
                                  release_track=base.ReleaseTrack.GA):
  """Constructs an environment patch for updating Airflow configs.

  Args:
    clear_airflow_configs: bool, whether to clear the Airflow configs
      dictionary.
    remove_airflow_configs: iterable(string), Iterable of Airflow config
      property names to remove.
    update_airflow_configs: {string: string}, dict of Airflow config property
      names and values to set.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  env_cls = messages.Environment
  airflow_config_overrides_cls = (
      messages.SoftwareConfig.AirflowConfigOverridesValue)
  entry_cls = airflow_config_overrides_cls.AdditionalProperty

  def _BuildEnv(entries):
    software_config = messages.SoftwareConfig(
        airflowConfigOverrides=airflow_config_overrides_cls(
            additionalProperties=entries))
    config = messages.EnvironmentConfig(softwareConfig=software_config)
    return env_cls(config=config)

  return command_util.BuildPartialUpdate(
      clear_airflow_configs, remove_airflow_configs, update_airflow_configs,
      'config.software_config.airflow_config_overrides', entry_cls, _BuildEnv)


def _ConstructEnvVariablesPatch(env_ref,
                                clear_env_variables,
                                remove_env_variables,
                                update_env_variables,
                                release_track=base.ReleaseTrack.GA):
  """Constructs an environment patch for updating environment variables.

  Note that environment variable updates do not support partial update masks
  unlike other map updates due to comments in (b/78298321). For this reason, we
  need to retrieve the Environment, apply an update on EnvVariable dictionary,
  and patch the entire dictionary. The potential race condition here
  (environment variables being updated between when we retrieve them and when we
  send patch request)is not a concern since environment variable updates take
  5 mins to complete, and environments cannot be updated while already in the
  updating state.

  Args:
    env_ref: resource argument, Environment resource argument for environment
      being updated.
    clear_env_variables: bool, whether to clear the environment variables
      dictionary.
    remove_env_variables: iterable(string), Iterable of environment variable
      names to remove.
    update_env_variables: {string: string}, dict of environment variable names
      and values to set.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  env_obj = environments_api_util.Get(env_ref, release_track=release_track)
  initial_env_var_value = env_obj.config.softwareConfig.envVariables
  initial_env_var_list = (
      initial_env_var_value.additionalProperties
      if initial_env_var_value else [])

  messages = api_util.GetMessagesModule(release_track=release_track)
  env_cls = messages.Environment
  env_variables_cls = messages.SoftwareConfig.EnvVariablesValue
  entry_cls = env_variables_cls.AdditionalProperty

  def _BuildEnv(entries):
    software_config = messages.SoftwareConfig(
        envVariables=env_variables_cls(additionalProperties=entries))
    config = messages.EnvironmentConfig(softwareConfig=software_config)
    return env_cls(config=config)

  return ('config.software_config.env_variables',
          command_util.BuildFullMapUpdate(clear_env_variables,
                                          remove_env_variables,
                                          update_env_variables,
                                          initial_env_var_list, entry_cls,
                                          _BuildEnv))


def _ConstructScheduledSnapshotPatch(enable_scheduled_snapshot_creation,
                                     snapshot_creation_schedule,
                                     snapshot_location,
                                     snapshot_schedule_timezone,
                                     release_track=base.ReleaseTrack.GA):
  """Constructs an environment patch for environment image version.

  Args:
    enable_scheduled_snapshot_creation: bool, whether the automatic snapshot
      creation should be enabled
    snapshot_creation_schedule: str, cron expression that specifies when
      snapshots will be created
    snapshot_location: str, a Cloud Storage location used to store automatically
      created snapshots
    snapshot_schedule_timezone: str, time zone that sets the context to
      interpret snapshot_creation_schedule.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  config = messages.EnvironmentConfig(
      recoveryConfig=messages.RecoveryConfig(
          scheduledSnapshotsConfig=messages.ScheduledSnapshotsConfig(
              enabled=enable_scheduled_snapshot_creation,
              snapshotCreationSchedule=snapshot_creation_schedule,
              snapshotLocation=snapshot_location,
              timeZone=snapshot_schedule_timezone)))

  return 'config.recovery_config.scheduled_snapshots_config', messages.Environment(
      config=config)


def _ConstructImageVersionPatch(update_image_version,
                                release_track=base.ReleaseTrack.GA):
  """Constructs an environment patch for environment image version.

  Args:
    update_image_version: string, the target image version.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  software_config = messages.SoftwareConfig(imageVersion=update_image_version)
  config = messages.EnvironmentConfig(softwareConfig=software_config)

  return 'config.software_config.image_version', messages.Environment(
      config=config)


def _ConstructWebServerAccessControlPatch(web_server_access_control,
                                          release_track):
  """Constructs an environment patch for web server network access control.

  Args:
    web_server_access_control: [{string: string}], the target list of IP ranges.
    release_track: base.ReleaseTrack, the release track of command. It dictates
      which Composer client library is used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  config = messages.EnvironmentConfig(
      webServerNetworkAccessControl=environments_api_util
      .BuildWebServerNetworkAccessControl(web_server_access_control,
                                          release_track))
  return 'config.web_server_network_access_control', messages.Environment(
      config=config)


def _ConstructCloudSqlMachineTypePatch(cloud_sql_machine_type, release_track):
  """Constructs an environment patch for Cloud SQL machine type.

  Args:
    cloud_sql_machine_type: str or None, Cloud SQL machine type used by the
      Airflow database.
    release_track: base.ReleaseTrack, the release track of command. It dictates
      which Composer client library is used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  config = messages.EnvironmentConfig(
      databaseConfig=messages.DatabaseConfig(
          machineType=cloud_sql_machine_type))
  return 'config.database_config.machine_type', messages.Environment(
      config=config)


def _ConstructWebServerMachineTypePatch(web_server_machine_type, release_track):
  """Constructs an environment patch for Airflow web server machine type.

  Args:
    web_server_machine_type: str or None, machine type used by the Airflow web
      server.
    release_track: base.ReleaseTrack, the release track of command. It dictates
      which Composer client library is used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  config = messages.EnvironmentConfig(
      webServerConfig=messages.WebServerConfig(
          machineType=web_server_machine_type))
  return 'config.web_server_config.machine_type', messages.Environment(
      config=config)


def _ConstructMasterAuthorizedNetworksTypePatch(enabled, networks,
                                                release_track):
  """Constructs an environment patch for Master authorized networks feature.

  Args:
    enabled: bool, whether master authorized networks should be enabled.
    networks: Iterable(string), master authorized networks.
    release_track: base.ReleaseTrack, the release track of command. It dictates
      which Composer client library is used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  config = messages.EnvironmentConfig()
  networks = [] if networks is None else networks
  config.masterAuthorizedNetworksConfig = messages.MasterAuthorizedNetworksConfig(
      enabled=enabled,
      cidrBlocks=[
          messages.CidrBlock(cidrBlock=network) for network in networks
      ])
  return 'config.master_authorized_networks_config', messages.Environment(
      config=config)


def _ConstructAutoscalingPatch(scheduler_cpu, worker_cpu, web_server_cpu,
                               scheduler_memory_gb, worker_memory_gb,
                               web_server_memory_gb, scheduler_storage_gb,
                               worker_storage_gb, web_server_storage_gb,
                               worker_min_count, worker_max_count,
                               scheduler_count, release_track, triggerer_cpu,
                               triggerer_memory_gb, triggerer_count):
  """Constructs an environment patch for Airflow web server machine type.

  Args:
    scheduler_cpu: float or None, CPU allocated to Airflow scheduler. Can be
      specified only in Composer 2.0.0.
    worker_cpu: float or None, CPU allocated to each Airflow worker. Can be
      specified only in Composer 2.0.0.
    web_server_cpu: float or None, CPU allocated to Airflow web server. Can be
      specified only in Composer 2.0.0.
    scheduler_memory_gb: float or None, memory allocated to Airflow scheduler.
      Can be specified only in Composer 2.0.0.
    worker_memory_gb: float or None, memory allocated to each Airflow worker.
      Can be specified only in Composer 2.0.0.
    web_server_memory_gb: float or None, memory allocated to Airflow web server.
      Can be specified only in Composer 2.0.0.
    scheduler_storage_gb: float or None, storage allocated to Airflow scheduler.
      Can be specified only in Composer 2.0.0.
    worker_storage_gb: float or None, storage allocated to each Airflow worker.
      Can be specified only in Composer 2.0.0.
    web_server_storage_gb: float or None, storage allocated to Airflow web
      server. Can be specified only in Composer 2.0.0.
    worker_min_count: int or None, minimum number of workers in the Environment.
      Can be specified only in Composer 2.0.0.
    worker_max_count: int or None, maximumn number of workers in the
      Environment. Can be specified only in Composer 2.0.0.
    scheduler_count: int or None, number of schedulers in the Environment. Can
      be specified only in Composer 2.0.0.
    release_track: base.ReleaseTrack, the release track of command. It dictates
      which Composer client library is used.
    triggerer_cpu: float or None, CPU allocated to Airflow triggerer. Can be
      specified only in Airflow 2.2.x and greater.
    triggerer_memory_gb: float or None, memory allocated to Airflow triggerer.
      Can be specified only in Airflow 2.2.x and greater.
    triggerer_count: int or None, number of triggerers in the Environment. Can
      be specified only in Airflow 2.2.x and greater

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)

  workload_resources = dict(
      scheduler=messages.SchedulerResource(
          cpu=scheduler_cpu,
          memoryGb=scheduler_memory_gb,
          storageGb=scheduler_storage_gb,
          count=scheduler_count),
      webServer=messages.WebServerResource(
          cpu=web_server_cpu,
          memoryGb=web_server_memory_gb,
          storageGb=web_server_storage_gb),
      worker=messages.WorkerResource(
          cpu=worker_cpu,
          memoryGb=worker_memory_gb,
          storageGb=worker_storage_gb,
          minCount=worker_min_count,
          maxCount=worker_max_count))
  if release_track != base.ReleaseTrack.GA and (triggerer_count is not None or
                                                triggerer_cpu or
                                                triggerer_memory_gb):
    workload_resources['triggerer'] = messages.TriggererResource(
        cpu=triggerer_cpu, memoryGb=triggerer_memory_gb, count=triggerer_count)

  config = messages.EnvironmentConfig(
      workloadsConfig=messages.WorkloadsConfig(**workload_resources))
  if all([
      scheduler_cpu, worker_cpu, web_server_cpu, scheduler_memory_gb,
      worker_memory_gb, web_server_memory_gb, scheduler_storage_gb,
      worker_storage_gb, web_server_storage_gb, worker_min_count,
      worker_max_count
  ]) and (release_track == base.ReleaseTrack.GA or
          all([triggerer_count, triggerer_cpu, triggerer_memory_gb])):
    return 'config.workloads_config', messages.Environment(config=config)
  else:
    mask = []
    if scheduler_cpu:
      mask.append('config.workloads_config.scheduler.cpu')
    if worker_cpu:
      mask.append('config.workloads_config.worker.cpu')
    if web_server_cpu:
      mask.append('config.workloads_config.web_server.cpu')
    if scheduler_memory_gb:
      mask.append('config.workloads_config.scheduler.memory_gb')
    if worker_memory_gb:
      mask.append('config.workloads_config.worker.memory_gb')
    if web_server_memory_gb:
      mask.append('config.workloads_config.web_server.memory_gb')
    if scheduler_storage_gb:
      mask.append('config.workloads_config.scheduler.storage_gb')
    if worker_storage_gb:
      mask.append('config.workloads_config.worker.storage_gb')
    if web_server_storage_gb:
      mask.append('config.workloads_config.web_server.storage_gb')
    if worker_min_count:
      mask.append('config.workloads_config.worker.min_count')
    if worker_max_count:
      mask.append('config.workloads_config.worker.max_count')
    if scheduler_count:
      mask.append('config.workloads_config.scheduler.count')
    if triggerer_cpu or triggerer_memory_gb:
      mask.append('config.workloads_config.triggerer')
    return ','.join(mask), messages.Environment(config=config)


def _ConstructMaintenanceWindowPatch(maintenance_window_start,
                                     maintenance_window_end,
                                     maintenance_window_recurrence,
                                     release_track=base.ReleaseTrack.GA):
  """Constructs an environment patch for updating maintenance window.

  Args:
    maintenance_window_start: Datetime or None, a starting date of the
      maintenance window.
    maintenance_window_end: Datetime or None, an ending date of the maintenance
      window.
    maintenance_window_recurrence: str or None, recurrence RRULE for the
      maintenance window.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)

  window_value = messages.MaintenanceWindow(
      startTime=maintenance_window_start.isoformat(),
      endTime=maintenance_window_end.isoformat(),
      recurrence=maintenance_window_recurrence)
  config = messages.EnvironmentConfig(maintenanceWindow=window_value)

  return 'config.maintenance_window', messages.Environment(config=config)


def _ConstructSoftwareConfigurationSchedulerCountPatch(
    scheduler_count, release_track=base.ReleaseTrack.GA):
  """Constructs a patch for updating scheduler count for Composer 1.*.*.

  Args:
    scheduler_count: number of schedulers.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)

  return 'config.software_config.scheduler_count', messages.Environment(
      config=messages.EnvironmentConfig(
          softwareConfig=messages.SoftwareConfig(
              schedulerCount=scheduler_count)))


def _ConstructSoftwareConfigurationCloudDataLineageIntegrationPatch(
    enabled, release_track):
  """Constructs a patch for updating Cloud Data Lineage integration config.

  Args:
    enabled: bool, whether Cloud Data Lineage integration should be enabled.
    release_track: base.ReleaseTrack, the release track of command. It dictates
      which Composer client library is used.

  Returns:
    (str, Environment), the field mask and environment to use for update.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)

  return 'config.software_config.cloud_data_lineage_integration', messages.Environment(
      config=messages.EnvironmentConfig(
          softwareConfig=messages.SoftwareConfig(
              cloudDataLineageIntegration=messages.CloudDataLineageIntegration(
                  enabled=enabled))))
