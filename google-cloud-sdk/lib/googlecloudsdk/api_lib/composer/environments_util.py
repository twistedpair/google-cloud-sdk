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
"""Utilities for calling the Composer Environments API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.composer import util as api_util
from googlecloudsdk.api_lib.util import exceptions
from googlecloudsdk.calliope import base


def GetService(release_track=base.ReleaseTrack.GA):
  return api_util.GetClientInstance(
      release_track).projects_locations_environments


class CreateEnvironmentFlags():
  """Container holding environment creation flag values.

  Attributes:
    node_count: int or None, the number of VMs to create for the environment
    labels: dict(str->str), a dict of user-provided resource labels to apply to
      the environment and its downstream resources
    location: str or None, the Compute Engine zone in which to create the
      environment specified as relative resource name.
    machine_type: str or None, the Compute Engine machine type of the VMs to
      create specified as relative resource name.
    network: str or None, the Compute Engine network to which to connect the
      environment specified as relative resource name.
    subnetwork: str or None, the Compute Engine subnetwork to which to connect
      the environment specified as relative resource name.
    env_variables: dict(str->str), a dict of user-provided environment variables
      to provide to the Airflow scheduler, worker, and webserver processes.
    airflow_config_overrides: dict(str->str), a dict of user-provided Airflow
      configuration overrides.
    service_account: str or None, the user-provided service account
    oauth_scopes: [str], the user-provided OAuth scopes
    tags: [str], the user-provided networking tags
    disk_size_gb: int, the disk size of node VMs, in GB
    python_version: str or None, major python version to use within created
      environment.
    image_version: str or None, the desired image for created environment in the
      format of 'composer-(version)-airflow-(version)'
    airflow_executor_type: str or None, the airflow executor type to run task
      instances.
    use_ip_aliases: bool or None, create env cluster nodes using alias IPs.
    cluster_secondary_range_name: str or None, the name of secondary range to
      allocate IP addresses to pods in GKE cluster.
    services_secondary_range_name: str or None, the name of the secondary range
      to allocate IP addresses to services in GKE cluster.
    cluster_ipv4_cidr_block: str or None, the IP address range to allocate IP
      adresses to pods in GKE cluster.
    services_ipv4_cidr_block: str or None, the IP address range to allocate IP
      addresses to services in GKE cluster.
    max_pods_per_node: int or None, the maximum number of pods that can be
      assigned to a GKE cluster node.
    private_environment: bool or None, create env cluster nodes with no public
      IP addresses.
    private_endpoint: bool or None, managed env cluster using the private IP
      address of the master API endpoint.
    master_ipv4_cidr: IPv4 CIDR range to use for the cluster master network.
    privately_used_public_ips: bool or None, when enabled, GKE pod and services
      can use IPs from public (non-RFC1918) ranges.
    web_server_ipv4_cidr: IPv4 CIDR range to use for Web Server network.
    cloud_sql_ipv4_cidr: IPv4 CIDR range to use for Cloud SQL network.
    web_server_access_control: [{string: string}], List of IP ranges with
      descriptions to allow access to the web server.
    cloud_sql_machine_type: str or None, Cloud SQL machine type used by the
      Airflow database.
    web_server_machine_type: str or None, machine type used by the Airflow web
      server
    kms_key: str or None, the user-provided customer-managed encryption key
      resource name
    scheduler_cpu: float or None, CPU allocated to Airflow scheduler. Can be
      specified only in Composer 2.0.0.
    worker_cpu: float or None, CPU allocated to each Airflow worker. Can be
      specified only in Composer 2.0.0.
    scheduler_memory_gb: float or None, memory allocated to Airflow scheduler.
      Can be specified only in Composer 2.0.0.
    worker_memory_gb: float or None, memory allocated to each Airflow worker.
      Can be specified only in Composer 2.0.0.
    min_workers: int or None, minimum number of workers in the Environment. Can
      be specified only in Composer 2.0.0.
    max_workers: int or None, maximumn number of workers in the Environment. Can
      be specified only in Composer 2.0.0.
    maintenance_window_start: Datetime or None, the starting time of the
      maintenance window
    maintenance_window_end: Datetime or None, the ending time of the maintenance
      window
    maintenance_window_recurrence: str or None, the recurrence of the
      maintenance window
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.
  """

  def __init__(self,
               node_count=None,
               labels=None,
               location=None,
               machine_type=None,
               network=None,
               subnetwork=None,
               env_variables=None,
               airflow_config_overrides=None,
               service_account=None,
               oauth_scopes=None,
               tags=None,
               disk_size_gb=None,
               python_version=None,
               image_version=None,
               airflow_executor_type=None,
               use_ip_aliases=None,
               cluster_secondary_range_name=None,
               services_secondary_range_name=None,
               cluster_ipv4_cidr_block=None,
               services_ipv4_cidr_block=None,
               max_pods_per_node=None,
               private_environment=None,
               private_endpoint=None,
               master_ipv4_cidr=None,
               privately_used_public_ips=None,
               web_server_ipv4_cidr=None,
               cloud_sql_ipv4_cidr=None,
               web_server_access_control=None,
               cloud_sql_machine_type=None,
               web_server_machine_type=None,
               kms_key=None,
               scheduler_cpu=None,
               worker_cpu=None,
               scheduler_memory_gb=None,
               worker_memory_gb=None,
               min_workers=None,
               max_workers=None,
               maintenance_window_start=None,
               maintenance_window_end=None,
               maintenance_window_recurrence=None,
               release_track=base.ReleaseTrack.GA):
    self.node_count = node_count
    self.labels = labels
    self.location = location
    self.machine_type = machine_type
    self.network = network
    self.subnetwork = subnetwork
    self.env_variables = env_variables
    self.airflow_config_overrides = airflow_config_overrides
    self.service_account = service_account
    self.oauth_scopes = oauth_scopes
    self.tags = tags
    self.disk_size_gb = disk_size_gb
    self.python_version = python_version
    self.image_version = image_version
    self.airflow_executor_type = airflow_executor_type
    self.use_ip_aliases = use_ip_aliases
    self.cluster_secondary_range_name = cluster_secondary_range_name
    self.services_secondary_range_name = services_secondary_range_name
    self.cluster_ipv4_cidr_block = cluster_ipv4_cidr_block
    self.services_ipv4_cidr_block = services_ipv4_cidr_block
    self.max_pods_per_node = max_pods_per_node
    self.private_environment = private_environment
    self.private_endpoint = private_endpoint
    self.master_ipv4_cidr = master_ipv4_cidr
    self.privately_used_public_ips = privately_used_public_ips
    self.web_server_ipv4_cidr = web_server_ipv4_cidr
    self.cloud_sql_ipv4_cidr = cloud_sql_ipv4_cidr
    self.web_server_access_control = web_server_access_control
    self.cloud_sql_machine_type = cloud_sql_machine_type
    self.web_server_machine_type = web_server_machine_type
    self.kms_key = kms_key
    self.scheduler_cpu = scheduler_cpu
    self.worker_cpu = worker_cpu
    self.scheduler_memory_gb = scheduler_memory_gb
    self.worker_memory_gb = worker_memory_gb
    self.min_workers = min_workers
    self.max_workers = max_workers
    self.maintenance_window_start = maintenance_window_start
    self.maintenance_window_end = maintenance_window_end
    self.maintenance_window_recurrence = maintenance_window_recurrence
    self.release_track = release_track


def _CreateNodeConfig(messages, flags):
  """Creates node config from parameters, returns None if config is empty."""
  if not (flags.location or flags.machine_type or flags.network or
          flags.subnetwork or flags.service_account or flags.oauth_scopes or
          flags.tags or flags.disk_size_gb or flags.use_ip_aliases):
    return None

  config = messages.NodeConfig(
      location=flags.location,
      machineType=flags.machine_type,
      network=flags.network,
      subnetwork=flags.subnetwork,
      serviceAccount=flags.service_account,
      diskSizeGb=flags.disk_size_gb)
  if flags.oauth_scopes:
    config.oauthScopes = sorted([s.strip() for s in flags.oauth_scopes])
  if flags.tags:
    config.tags = sorted([t.strip() for t in flags.tags])
  if flags.use_ip_aliases:
    config.ipAllocationPolicy = messages.IPAllocationPolicy(
        useIpAliases=flags.use_ip_aliases,
        clusterSecondaryRangeName=flags.cluster_secondary_range_name,
        servicesSecondaryRangeName=flags.services_secondary_range_name,
        clusterIpv4CidrBlock=flags.cluster_ipv4_cidr_block,
        servicesIpv4CidrBlock=flags.services_ipv4_cidr_block,
    )

    if flags.max_pods_per_node:
      config.maxPodsPerNode = flags.max_pods_per_node

  return config


def _CreateConfig(messages, flags):
  """Creates environment config from parameters, returns None if config is empty."""
  node_config = _CreateNodeConfig(messages, flags)
  if not (node_config or flags.node_count or flags.kms_key or
          flags.image_version or flags.env_variables or
          flags.airflow_config_overrides or flags.python_version or
          flags.airflow_executor_type or flags.maintenance_window_start or
          flags.maintenance_window_end or flags.maintenance_window_recurrence or
          flags.private_environment or flags.web_server_access_control or
          flags.cloud_sql_machine_type or flags.web_server_machine_type or
          flags.scheduler_cpu or flags.worker_cpu or flags.scheduler_memory_gb
          or flags.worker_memory_gb or flags.min_workers or flags.max_workers):
    return None

  config = messages.EnvironmentConfig()
  if flags.node_count:
    config.nodeCount = flags.node_count
  if node_config:
    config.nodeConfig = node_config
  if flags.kms_key:
    config.encryptionConfig = messages.EncryptionConfig(
        kmsKeyName=flags.kms_key)
  if (flags.image_version or flags.env_variables or
      flags.airflow_config_overrides or flags.python_version or
      flags.airflow_executor_type):
    config.softwareConfig = messages.SoftwareConfig()
    if flags.image_version:
      config.softwareConfig.imageVersion = flags.image_version
    if flags.env_variables:
      config.softwareConfig.envVariables = api_util.DictToMessage(
          flags.env_variables, messages.SoftwareConfig.EnvVariablesValue)
    if flags.airflow_config_overrides:
      config.softwareConfig.airflowConfigOverrides = api_util.DictToMessage(
          flags.airflow_config_overrides,
          messages.SoftwareConfig.AirflowConfigOverridesValue)
    if flags.python_version:
      config.softwareConfig.pythonVersion = flags.python_version
    if flags.airflow_executor_type:
      config.softwareConfig.airflowExecutorType = ConvertToTypeEnum(
          messages.SoftwareConfig.AirflowExecutorTypeValueValuesEnum,
          flags.airflow_executor_type)

  if flags.maintenance_window_start:
    assert flags.maintenance_window_end, 'maintenance_window_end is missing'
    assert flags.maintenance_window_recurrence, (
        'maintenance_window_recurrence is missing')
    config.maintenanceWindow = messages.MaintenanceWindow(
        startTime=flags.maintenance_window_start.isoformat(),
        endTime=flags.maintenance_window_end.isoformat(),
        recurrence=flags.maintenance_window_recurrence)

  if flags.use_ip_aliases and flags.private_environment:
    # Adds a PrivateClusterConfig, if necessary.
    private_cluster_config = None
    if flags.private_endpoint or flags.master_ipv4_cidr:
      private_cluster_config = messages.PrivateClusterConfig(
          enablePrivateEndpoint=flags.private_endpoint,
          masterIpv4CidrBlock=flags.master_ipv4_cidr)

    private_env_config_args = {
        'enablePrivateEnvironment': flags.private_environment,
        'privateClusterConfig': private_cluster_config,
    }

    if flags.web_server_ipv4_cidr is not None:
      private_env_config_args[
          'webServerIpv4CidrBlock'] = flags.web_server_ipv4_cidr
    if flags.cloud_sql_ipv4_cidr is not None:
      private_env_config_args[
          'cloudSqlIpv4CidrBlock'] = flags.cloud_sql_ipv4_cidr
    if flags.privately_used_public_ips is not None:
      private_env_config_args[
          'enablePrivatelyUsedPublicIps'] = flags.privately_used_public_ips
    config.privateEnvironmentConfig = messages.PrivateEnvironmentConfig(
        **private_env_config_args)

  # Builds webServerNetworkAccessControl, if necessary.
  if flags.web_server_access_control is not None:
    config.webServerNetworkAccessControl = BuildWebServerNetworkAccessControl(
        flags.web_server_access_control, flags.release_track)

  if flags.cloud_sql_machine_type:
    config.databaseConfig = messages.DatabaseConfig(
        machineType=flags.cloud_sql_machine_type)
  if flags.web_server_machine_type:
    config.webServerConfig = messages.WebServerConfig(
        machineType=flags.web_server_machine_type)
  if (flags.scheduler_cpu or flags.worker_cpu or flags.scheduler_memory_gb or
      flags.worker_memory_gb or flags.min_workers or flags.max_workers):
    config.workloadsConfig = messages.WorkloadsConfig(
        scheduler=messages.SchedulerResource(
            cpu=flags.scheduler_cpu, memoryGb=flags.scheduler_memory_gb),
        worker=messages.WorkerResource(
            cpu=flags.worker_cpu,
            memoryGb=flags.worker_memory_gb,
            minCount=flags.min_workers,
            maxCount=flags.max_workers))

  return config


def Create(environment_ref, flags):
  """Calls the Composer Environments.Create method.

  Args:
    environment_ref: Resource, the Composer environment resource to create.
    flags: CreateEnvironmentFlags, the flags provided for environment creation.

  Returns:
    Operation: the operation corresponding to the creation of the environment
  """
  messages = api_util.GetMessagesModule(release_track=flags.release_track)
  # Builds environment message and attaches the configuration
  environment = messages.Environment(name=environment_ref.RelativeName())
  environment.config = _CreateConfig(messages, flags)

  if flags.labels:
    environment.labels = api_util.DictToMessage(
        flags.labels, messages.Environment.LabelsValue)

  try:
    return GetService(release_track=flags.release_track).Create(
        api_util.GetMessagesModule(release_track=flags.release_track)
        .ComposerProjectsLocationsEnvironmentsCreateRequest(
            environment=environment,
            parent=environment_ref.Parent().RelativeName()))
  except apitools_exceptions.HttpForbiddenError as e:
    raise exceptions.HttpException(
        e,
        error_format=(
            'Creation operation failed because of lack of proper '
            'permissions. Please, refer to '
            'https://cloud.google.com/composer/docs/how-to/managing/creating '
            'and Composer Creation Troubleshooting pages to resolve this issue.'
        ))


def ConvertToTypeEnum(type_enum, airflow_executor_type):
  """Converts airflow executor type string to enum.

  Args:
    type_enum: AirflowExecutorTypeValueValuesEnum, executor type enum value.
    airflow_executor_type: string, executor type string value.

  Returns:
    AirflowExecutorTypeValueValuesEnum: the executor type enum value.
  """
  return type_enum(airflow_executor_type)


def Delete(environment_ref, release_track=base.ReleaseTrack.GA):
  """Calls the Composer Environments.Delete method.

  Args:
    environment_ref: Resource, the Composer environment resource to
        delete.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
        which Composer client library will be used.

  Returns:
    Operation: the operation corresponding to the deletion of the environment
  """
  return GetService(release_track=release_track).Delete(
      api_util.GetMessagesModule(release_track=release_track)
      .ComposerProjectsLocationsEnvironmentsDeleteRequest(
          name=environment_ref.RelativeName()))


def RestartWebServer(environment_ref, release_track=base.ReleaseTrack.BETA):
  """Calls the Composer Environments.RestartWebServer method.

  Args:
    environment_ref: Resource, the Composer environment resource to restart the
      web server for.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    Operation: the operation corresponding to the restart of the web server
  """
  message_module = api_util.GetMessagesModule(release_track=release_track)
  request_message = message_module.ComposerProjectsLocationsEnvironmentsRestartWebServerRequest(
      name=environment_ref.RelativeName())
  return GetService(
      release_track=release_track).RestartWebServer(request_message)


def Get(environment_ref, release_track=base.ReleaseTrack.GA):
  """Calls the Composer Environments.Get method.

  Args:
    environment_ref: Resource, the Composer environment resource to retrieve.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    Environment: the requested environment
  """
  return GetService(release_track=release_track).Get(
      api_util.GetMessagesModule(release_track=release_track)
      .ComposerProjectsLocationsEnvironmentsGetRequest(
          name=environment_ref.RelativeName()))


def List(location_refs,
         page_size,
         limit=None,
         release_track=base.ReleaseTrack.GA):
  """Lists Composer Environments across all locations.

  Uses a hardcoded list of locations, as there is no way to dynamically
  discover the list of supported locations. Support for new locations
  will be aligned with Cloud SDK releases.

  Args:
    location_refs: [core.resources.Resource], a list of resource reference to
        locations in which to list environments.
    page_size: An integer specifying the maximum number of resources to be
      returned in a single list call.
    limit: An integer specifying the maximum number of environments to list.
        None if all available environments should be returned.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
        which Composer client library will be used.

  Returns:
    list: a generator over Environments in the locations in `location_refs`
  """
  return api_util.AggregateListResults(
      api_util.GetMessagesModule(release_track=release_track)
      .ComposerProjectsLocationsEnvironmentsListRequest,
      GetService(release_track=release_track),
      location_refs,
      'environments',
      page_size,
      limit=limit)


def Patch(environment_ref,
          environment_patch,
          update_mask,
          release_track=base.ReleaseTrack.GA):
  """Calls the Composer Environments.Update method.

  Args:
    environment_ref: Resource, the Composer environment resource to update.
    environment_patch: The Environment message specifying the patch associated
      with the update_mask.
    update_mask: A field mask defining the patch.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
        which Composer client library will be used.
  Returns:
    Operation: the operation corresponding to the environment update
  """
  try:
    return GetService(release_track=release_track).Patch(
        api_util.GetMessagesModule(release_track=release_track)
        .ComposerProjectsLocationsEnvironmentsPatchRequest(
            name=environment_ref.RelativeName(),
            environment=environment_patch,
            updateMask=update_mask))
  except apitools_exceptions.HttpForbiddenError as e:
    raise exceptions.HttpException(
        e,
        error_format=(
            'Update operation failed because of lack of proper '
            'permissions. Please, refer to '
            'https://cloud.google.com/composer/docs/how-to/managing/updating '
            'and Composer Update Troubleshooting pages to resolve this issue.'))


def BuildWebServerNetworkAccessControl(web_server_access_control,
                                       release_track):
  """Builds a WebServerNetworkAccessControl proto given an IP range list.

  If the list is empty, the returned policy is set to ALLOW by default.
  Otherwise, the default policy is DENY with a list of ALLOW rules for each
  of the IP ranges.

  Args:
    web_server_access_control: [{string: string}], list of IP ranges with
      descriptions.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
      which Composer client library will be used.

  Returns:
    WebServerNetworkAccessControl: proto to be sent to the API.
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  return messages.WebServerNetworkAccessControl(allowedIpRanges=[
      messages.AllowedIpRange(
          value=ip_range['ip_range'], description=ip_range.get('description'))
      for ip_range in web_server_access_control
  ])


def BuildWebServerAllowedIps(allowed_ip_list, allow_all, deny_all):
  """Returns the list of IP ranges that will be sent to the API.

  The resulting IP range list is determined by the options specified in
  environment create or update flags.

  Args:
    allowed_ip_list: [{string: string}], list of IP ranges with descriptions.
    allow_all: bool, True if allow all flag was set.
    deny_all: bool, True if deny all flag was set.

  Returns:
    [{string: string}]: list of IP ranges that will be sent to the API, taking
        into account the values of allow all and deny all flags.
  """
  if deny_all:
    return []
  if allow_all:
    return [{
        'ip_range': '0.0.0.0/0',
        'description': 'Allows access from all IPv4 addresses (default value)',
    }, {
        'ip_range': '::0/0',
        'description': 'Allows access from all IPv6 addresses (default value)',
    }]
  return allowed_ip_list


def DiskSizeBytesToGB(disk_size):
  """Returns a disk size value in GB.

  Args:
    disk_size: int, size in bytes, or None for default value

  Returns:
    int, size in GB
  """
  return disk_size >> 30 if disk_size else disk_size


def MemorySizeBytesToGB(memory_size):
  """Returns a memory size value in GB.

  Args:
    memory_size: int, size in bytes, or None for default value

  Returns:
    float, size in GB rounded to 3 decimal places
  """
  if not memory_size:
    return memory_size
  return round(memory_size / float(1 << 30), 3)
