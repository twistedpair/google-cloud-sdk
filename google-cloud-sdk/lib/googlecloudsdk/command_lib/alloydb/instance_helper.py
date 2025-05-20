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
"""Helper functions for constructing and validating AlloyDB instance requests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.alloydb import api_util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.parser_errors import DetailedArgumentError
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core import properties


def ConstructCreateRequestFromArgsGA(
    client, alloydb_messages, project_ref, args
):
  """Validates command line input arguments and passes parent's resources for GA track.

  Args:
    client: Client for api_utils.py class.
    alloydb_messages: Messages module for the API client.
    project_ref: parent resource path of the resource being created
    args: Command line input arguments.

  Returns:
    Fully-constructed request to create an AlloyDB instance.
  """
  instance_resource = _ConstructInstanceFromArgs(client, alloydb_messages, args)

  return (
      alloydb_messages.AlloydbProjectsLocationsClustersInstancesCreateRequest(
          instance=instance_resource,
          instanceId=args.instance,
          parent=project_ref.RelativeName(),
      )
  )


def ConstructCreateRequestFromArgsBeta(
    client, alloydb_messages, project_ref, args
):
  """Validates command line input arguments and passes parent's resources for beta tracks.

  Args:
    client: Client for api_utils.py class.
    alloydb_messages: Messages module for the API client.
    project_ref: Parent resource path of the resource being created
    args: Command line input arguments.

  Returns:
    Fully-constructed request to create an AlloyDB instance.
  """
  instance_resource = _ConstructInstanceFromArgsBeta(
      client, alloydb_messages, args
  )

  return (
      alloydb_messages.AlloydbProjectsLocationsClustersInstancesCreateRequest(
          instance=instance_resource,
          instanceId=args.instance,
          parent=project_ref.RelativeName(),
      )
  )


def ConstructCreateRequestFromArgsAlpha(
    client, alloydb_messages, project_ref, args
):
  """Validates command line input arguments and passes parent's resources for alpha track.

  Args:
    client: Client for api_utils.py class.
    alloydb_messages: Messages module for the API client.
    project_ref: Parent resource path of the resource being created
    args: Command line input arguments.

  Returns:
    Fully-constructed request to create an AlloyDB instance.
  """
  instance_resource = _ConstructInstanceFromArgsAlpha(
      client, alloydb_messages, args
  )

  return (
      alloydb_messages.AlloydbProjectsLocationsClustersInstancesCreateRequest(
          instance=instance_resource,
          instanceId=args.instance,
          parent=project_ref.RelativeName(),
      )
  )


def ConstructCreateMachineConfigFromArgs(alloydb_messages, args):
  """Validates command line input arguments and creates a MachineConfig object."""
  if args.cpu_count or args.machine_type:
    return alloydb_messages.MachineConfig(
        cpuCount=args.cpu_count, machineType=args.machine_type
    )
  else:
    raise DetailedArgumentError(
        'Either --cpu-count or --machine-type must be specified.'
    )


def _ConstructInstanceFromArgs(client, alloydb_messages, args):
  """Validates command line input arguments and passes parent's resources to create an AlloyDB instance.

  Args:
    client: Client for api_utils.py class.
    alloydb_messages: Messages module for the API client.
    args: Command line input arguments.

  Returns:
    An AlloyDB instance to create with the specified command line arguments.
  """
  instance_resource = alloydb_messages.Instance()

  # set availability-type if provided
  instance_resource.availabilityType = ParseAvailabilityType(
      alloydb_messages, args.availability_type
  )
  instance_resource.machineConfig = ConstructCreateMachineConfigFromArgs(
      alloydb_messages, args
  )
  instance_ref = client.resource_parser.Create(
      'alloydb.projects.locations.clusters.instances',
      projectsId=properties.VALUES.core.project.GetOrFail,
      locationsId=args.region,
      clustersId=args.cluster,
      instancesId=args.instance,
  )
  instance_resource.name = instance_ref.RelativeName()

  instance_resource.databaseFlags = labels_util.ParseCreateArgs(
      args,
      alloydb_messages.Instance.DatabaseFlagsValue,
      labels_dest='database_flags',
  )
  instance_resource.instanceType = _ParseInstanceType(
      alloydb_messages, args.instance_type
  )

  if (
      instance_resource.instanceType
      == alloydb_messages.Instance.InstanceTypeValueValuesEnum.READ_POOL
  ):
    instance_resource.readPoolConfig = alloydb_messages.ReadPoolConfig(
        nodeCount=args.read_pool_node_count
    )

  instance_resource.queryInsightsConfig = _QueryInsightsConfig(
      alloydb_messages,
      insights_config_query_string_length=args.insights_config_query_string_length,
      insights_config_query_plans_per_minute=args.insights_config_query_plans_per_minute,
      insights_config_record_application_tags=args.insights_config_record_application_tags,
      insights_config_record_client_address=args.insights_config_record_client_address,
  )

  instance_resource.clientConnectionConfig = ClientConnectionConfig(
      alloydb_messages,
      args.ssl_mode,
      args.require_connectors,
  )

  instance_resource.networkConfig = NetworkConfig(
      alloydb_messages=alloydb_messages,
      assign_inbound_public_ip=args.assign_inbound_public_ip,
      authorized_external_networks=args.authorized_external_networks,
      outbound_public_ip=args.outbound_public_ip,
  )

  if (
      args.allowed_psc_projects
      or args.psc_network_attachment_uri is not None
      or args.psc_auto_connections is not None
  ):
    instance_resource.pscInstanceConfig = PscInstanceConfig(
        alloydb_messages=alloydb_messages,
        allowed_psc_projects=args.allowed_psc_projects,
        psc_network_attachment_uri=args.psc_network_attachment_uri,
        psc_auto_connections=args.psc_auto_connections,
    )

  return instance_resource


def _ConstructInstanceFromArgsBeta(client, alloydb_messages, args):
  """Validates command line input arguments and passes parent's resources to create an AlloyDB instance for beta track.

  Args:
    client: Client for api_utils.py class.
    alloydb_messages: Messages module for the API client.
    args: Command line input arguments.

  Returns:
    An AlloyDB instance to create with the specified command line arguments.
  """
  instance_resource = _ConstructInstanceFromArgs(client, alloydb_messages, args)
  instance_resource.observabilityConfig = _ObservabilityConfig(
      alloydb_messages,
      observability_config_enabled=args.observability_config_enabled,
      observability_config_preserve_comments=args.observability_config_preserve_comments,
      observability_config_track_wait_events=args.observability_config_track_wait_events,
      observability_config_max_query_string_length=args.observability_config_max_query_string_length,
      observability_config_record_application_tags=args.observability_config_record_application_tags,
      observability_config_query_plans_per_minute=args.observability_config_query_plans_per_minute,
      observability_config_track_active_queries=args.observability_config_track_active_queries,
  )

  return instance_resource


def _ConstructInstanceFromArgsAlpha(client, alloydb_messages, args):
  """Validates command line input arguments and passes parent's resources to create an AlloyDB instance for alpha track.

  Args:
    client: Client for api_utils.py class.
    alloydb_messages: Messages module for the API client.
    args: Command line input arguments.

  Returns:
    An AlloyDB instance to create with the specified command line arguments.
  """
  instance_resource = _ConstructInstanceFromArgsBeta(
      client, alloydb_messages, args
  )

  if args.enable_connection_pooling:
    instance_resource.connectionPoolConfig = _ConnectionPoolConfig(
        alloydb_messages=alloydb_messages,
        enable_connection_pooling=args.enable_connection_pooling,
        connection_pooling_pool_mode=args.connection_pooling_pool_mode,
        connection_pooling_min_pool_size=args.connection_pooling_min_pool_size,
        connection_pooling_max_pool_size=args.connection_pooling_max_pool_size,
        connection_pooling_max_client_conn=args.connection_pooling_max_client_connections,
        connection_pooling_server_idle_timeout=args.connection_pooling_server_idle_timeout,
        connection_pooling_query_wait_timeout=args.connection_pooling_query_wait_timeout,
        connection_pooling_stats_users=args.connection_pooling_stats_users,
        connection_pooling_ignore_startup_parameters=args.connection_pooling_ignore_startup_parameters,
    )

  return instance_resource


def _ConstructSecondaryInstanceFromArgs(client, alloydb_messages, args):
  """Validates command line input arguments and passes parent's resources to create an AlloyDB secondary instance."""

  instance_resource = alloydb_messages.Instance()
  instance_ref = client.resource_parser.Create(
      'alloydb.projects.locations.clusters.instances',
      projectsId=properties.VALUES.core.project.GetOrFail,
      locationsId=args.region,
      clustersId=args.cluster,
      instancesId=args.instance,
  )
  instance_resource.name = instance_ref.RelativeName()
  instance_resource.instanceType = (
      alloydb_messages.Instance.InstanceTypeValueValuesEnum.SECONDARY
  )
  instance_resource.availabilityType = ParseAvailabilityType(
      alloydb_messages, args.availability_type
  )
  instance_resource.clientConnectionConfig = ClientConnectionConfig(
      alloydb_messages, args.ssl_mode, args.require_connectors
  )
  instance_resource.databaseFlags = labels_util.ParseCreateArgs(
      args,
      alloydb_messages.Instance.DatabaseFlagsValue,
      labels_dest='database_flags',
  )
  instance_resource.networkConfig = NetworkConfig(
      alloydb_messages=alloydb_messages,
      assign_inbound_public_ip=args.assign_inbound_public_ip,
      authorized_external_networks=args.authorized_external_networks,
      outbound_public_ip=args.outbound_public_ip,
  )
  if (
      args.allowed_psc_projects
      or args.psc_network_attachment_uri is not None
      or args.psc_auto_connections is not None
  ):
    instance_resource.pscInstanceConfig = PscInstanceConfig(
        alloydb_messages=alloydb_messages,
        allowed_psc_projects=args.allowed_psc_projects,
        psc_network_attachment_uri=args.psc_network_attachment_uri,
        psc_auto_connections=args.psc_auto_connections,
    )
  return instance_resource


def ConstructSecondaryCreateRequestFromArgsGA(
    client, alloydb_messages, cluster_ref, args
):
  """Validates command line input arguments and passes parent's resources for GA track."""

  instance_resource = _ConstructSecondaryInstanceFromArgs(
      client, alloydb_messages, args
  )

  return alloydb_messages.AlloydbProjectsLocationsClustersInstancesCreatesecondaryRequest(
      instance=instance_resource,
      instanceId=args.instance,
      parent=cluster_ref.RelativeName(),
  )


def ConstructSecondaryCreateRequestFromArgsAlphaBeta(
    client, alloydb_messages, cluster_ref, args
):
  """Validates command line input arguments and passes parent's resources for alpha/beta track."""
  instance_resource = _ConstructSecondaryInstanceFromArgs(
      client, alloydb_messages, args
  )
  return alloydb_messages.AlloydbProjectsLocationsClustersInstancesCreatesecondaryRequest(
      instance=instance_resource,
      instanceId=args.instance,
      parent=cluster_ref.RelativeName(),
  )


def ConstructPatchRequestFromArgs(alloydb_messages, instance_ref, args):
  """Constructs the request to update an AlloyDB instance.

  Args:
    alloydb_messages: Messages module for the API client.
    instance_ref: parent resource path of the resource being updated
    args: Command line input arguments.

  Returns:
    Fully-constructed request to update an AlloyDB instance.
  """
  instance_resource, paths = ConstructInstanceAndUpdatePathsFromArgs(
      alloydb_messages, instance_ref, args
  )
  mask = ','.join(paths) if paths else None

  return alloydb_messages.AlloydbProjectsLocationsClustersInstancesPatchRequest(
      instance=instance_resource,
      name=instance_ref.RelativeName(),
      updateMask=mask,
  )


def ConstructInstanceAndUpdatePathsFromArgs(
    alloydb_messages, instance_ref, args
):
  """Validates command line arguments and creates the instance and update paths.

  Args:
    alloydb_messages: Messages module for the API client.
    instance_ref: parent resource path of the resource being updated
    args: Command line input arguments.

  Returns:
    An AlloyDB instance and paths for update.
  """
  availability_type_path = 'availabilityType'
  database_flags_path = 'databaseFlags'
  cpu_count_path = 'machineConfig.cpuCount'
  machine_type_path = 'machineConfig.machineType'
  read_pool_node_count_path = 'readPoolConfig.nodeCount'
  insights_config_query_string_length_path = (
      'queryInsightsConfig.queryStringLength'
  )
  insights_config_query_plans_per_minute_path = (
      'queryInsightsConfig.queryPlansPerMinute'
  )
  insights_config_record_application_tags_path = (
      'queryInsightsConfig.recordApplicationTags'
  )
  insights_config_record_client_address_path = (
      'queryInsightsConfig.recordClientAddress'
  )
  activation_policy_path = 'activationPolicy'

  instance_resource = alloydb_messages.Instance()
  paths = []

  instance_resource.name = instance_ref.RelativeName()
  if args.activation_policy:
    instance_resource.activationPolicy = args.activation_policy
    paths.append(activation_policy_path)

  availability_type = ParseAvailabilityType(
      alloydb_messages, args.availability_type
  )
  if availability_type:
    instance_resource.availabilityType = availability_type
    paths.append(availability_type_path)

  database_flags = labels_util.ParseCreateArgs(
      args,
      alloydb_messages.Instance.DatabaseFlagsValue,
      labels_dest='database_flags',
  )
  if database_flags:
    instance_resource.databaseFlags = database_flags
    paths.append(database_flags_path)

  if args.cpu_count or args.machine_type:
    instance_resource.machineConfig = alloydb_messages.MachineConfig(
        cpuCount=args.cpu_count, machineType=args.machine_type
    )
    if args.cpu_count:
      paths.append(cpu_count_path)
    if args.machine_type:
      paths.append(machine_type_path)

  if args.read_pool_node_count:
    instance_resource.readPoolConfig = alloydb_messages.ReadPoolConfig(
        nodeCount=args.read_pool_node_count
    )
    paths.append(read_pool_node_count_path)

  if args.insights_config_query_string_length:
    paths.append(insights_config_query_string_length_path)
  if args.insights_config_query_plans_per_minute:
    paths.append(insights_config_query_plans_per_minute_path)
  if args.insights_config_record_application_tags is not None:
    paths.append(insights_config_record_application_tags_path)
  if args.insights_config_record_client_address is not None:
    paths.append(insights_config_record_client_address_path)

  instance_resource.queryInsightsConfig = _QueryInsightsConfig(
      alloydb_messages,
      args.insights_config_query_string_length,
      args.insights_config_query_plans_per_minute,
      args.insights_config_record_application_tags,
      args.insights_config_record_client_address,
  )

  # Check if require_connectors is set to True/False, then update
  if args.require_connectors is not None:
    require_connectors_path = 'clientConnectionConfig.requireConnectors'
    paths.append(require_connectors_path)
  if args.ssl_mode:
    ssl_mode_path = 'clientConnectionConfig.sslConfig.sslMode'
    paths.append(ssl_mode_path)
  if args.require_connectors is not None or args.ssl_mode:
    instance_resource.clientConnectionConfig = ClientConnectionConfig(
        alloydb_messages, args.ssl_mode, args.require_connectors
    )

  if (
      args.assign_inbound_public_ip
      or args.authorized_external_networks is not None
      or args.outbound_public_ip is not None
  ):
    instance_resource.networkConfig = NetworkConfig(
        alloydb_messages=alloydb_messages,
        assign_inbound_public_ip=args.assign_inbound_public_ip,
        authorized_external_networks=args.authorized_external_networks,
        outbound_public_ip=args.outbound_public_ip,
    )
  if args.outbound_public_ip is not None:
    outbound_public_ip_path = 'networkConfig.enableOutboundPublicIp'
    paths.append(outbound_public_ip_path)
  # If we are disabling public ip then update both enablePublicIp and
  # authorizedExternalNetworks because we need to clear the list of authorized
  # networks.
  if (
      args.assign_inbound_public_ip
      and not instance_resource.networkConfig.enablePublicIp
  ):
    paths.append('networkConfig.enablePublicIp')
    paths.append('networkConfig.authorizedExternalNetworks')
  else:
    if args.assign_inbound_public_ip:
      paths.append('networkConfig.enablePublicIp')
    if args.authorized_external_networks is not None:
      paths.append('networkConfig.authorizedExternalNetworks')

  # Empty lists are allowed for consumers to remove all PSC allowed projects.
  if (
      args.allowed_psc_projects is not None
      or args.psc_network_attachment_uri is not None
      or args.clear_psc_network_attachment_uri
      or args.psc_auto_connections is not None
      or args.clear_psc_auto_connections
  ):
    instance_resource.pscInstanceConfig = PscInstanceConfig(
        alloydb_messages=alloydb_messages,
        allowed_psc_projects=args.allowed_psc_projects,
        psc_network_attachment_uri=args.psc_network_attachment_uri,
        clear_psc_network_attachment_uri=args.clear_psc_network_attachment_uri,
        psc_auto_connections=args.psc_auto_connections,
        clear_psc_auto_connections=args.clear_psc_auto_connections,
    )
  if (
      args.psc_network_attachment_uri is not None
      or args.clear_psc_network_attachment_uri
  ):
    paths.append('pscInstanceConfig.pscInterfaceConfigs')
  if args.allowed_psc_projects is not None:
    paths.append('pscInstanceConfig.allowedConsumerProjects')
  if args.psc_auto_connections is not None or args.clear_psc_auto_connections:
    paths.append('pscInstanceConfig.pscAutoConnections')
  return instance_resource, paths


def _QueryInsightsConfig(
    alloydb_messages,
    insights_config_query_string_length=None,
    insights_config_query_plans_per_minute=None,
    insights_config_record_application_tags=None,
    insights_config_record_client_address=None,
):
  """Generates the insights config for the instance.

  Args:
    alloydb_messages: module, Message module for the API client.
    insights_config_query_string_length: number, length of the query string to
      be stored.
    insights_config_query_plans_per_minute: number, number of query plans to
      sample every minute.
    insights_config_record_application_tags: boolean, True if application tags
      should be recorded.
    insights_config_record_client_address: boolean, True if client address
      should be recorded.

  Returns:
    alloydb_messages.QueryInsightsInstanceConfig or None
  """

  should_generate_config = any([
      insights_config_query_string_length is not None,
      insights_config_query_plans_per_minute is not None,
      insights_config_record_application_tags is not None,
      insights_config_record_client_address is not None,
  ])
  if not should_generate_config:
    return None

  # Config exists, generate insights config.
  insights_config = alloydb_messages.QueryInsightsInstanceConfig()
  if insights_config_query_string_length is not None:
    insights_config.queryStringLength = insights_config_query_string_length
  if insights_config_query_plans_per_minute is not None:
    insights_config.queryPlansPerMinute = insights_config_query_plans_per_minute
  if insights_config_record_application_tags is not None:
    insights_config.recordApplicationTags = (
        insights_config_record_application_tags
    )
  if insights_config_record_client_address is not None:
    insights_config.recordClientAddress = insights_config_record_client_address

  return insights_config


def _ObservabilityConfig(
    alloydb_messages,
    observability_config_enabled=None,
    observability_config_preserve_comments=None,
    observability_config_track_wait_events=None,
    observability_config_max_query_string_length=None,
    observability_config_record_application_tags=None,
    observability_config_query_plans_per_minute=None,
    observability_config_track_active_queries=None,
):
  """Generates the observability config for the instance.

  Args:
    alloydb_messages: module, Message module for the API client.
    observability_config_enabled: boolean, True if observability should be
      enabled.
    observability_config_preserve_comments: boolean, True if comments should be
      preserved in the query string.
    observability_config_track_wait_events: boolean, True if wait events should
      be tracked.
    observability_config_max_query_string_length: number, length of the query
      string to be stored.
    observability_config_record_application_tags: boolean, True if application
      tags should be recorded.
    observability_config_query_plans_per_minute: number, number of query plans
      to sample every minute.
    observability_config_track_active_queries: boolean, True if active queries
      should be tracked.

  Returns:
    alloydb_messages.ObservabilityInstanceConfig or None
  """

  should_generate_config = any([
      observability_config_enabled is not None,
      observability_config_preserve_comments is not None,
      observability_config_track_wait_events is not None,
      observability_config_max_query_string_length is not None,
      observability_config_record_application_tags is not None,
      observability_config_query_plans_per_minute is not None,
      observability_config_track_active_queries is not None,
  ])
  if not should_generate_config:
    return None

  # Config exists, generate observability config.
  observability_config = alloydb_messages.ObservabilityInstanceConfig()
  if observability_config_enabled is not None:
    observability_config.enabled = observability_config_enabled
  if observability_config_preserve_comments is not None:
    observability_config.preserveComments = (
        observability_config_preserve_comments
    )
  if observability_config_track_wait_events is not None:
    observability_config.trackWaitEvents = (
        observability_config_track_wait_events
    )
  if observability_config_max_query_string_length is not None:
    observability_config.maxQueryStringLength = (
        observability_config_max_query_string_length
    )
  if observability_config_record_application_tags is not None:
    observability_config.recordApplicationTags = (
        observability_config_record_application_tags
    )
  if observability_config_query_plans_per_minute is not None:
    observability_config.queryPlansPerMinute = (
        observability_config_query_plans_per_minute
    )
  if observability_config_track_active_queries is not None:
    observability_config.trackActiveQueries = (
        observability_config_track_active_queries
    )

  return observability_config


def ClientConnectionConfig(
    alloydb_messages,
    ssl_mode=None,
    require_connectors=None,
):
  """Generates the client connection config for the instance.

  Args:
    alloydb_messages: module, Message module for the API client.
    ssl_mode: string, SSL mode to use when connecting to the database.
    require_connectors: boolean, whether or not to enforce connections to the
      database to go through a connector (ex: Auth Proxy).

  Returns:
    alloydb_messages.ClientConnectionConfig
  """

  should_generate_config = any([
      ssl_mode is not None,
      require_connectors is not None,
  ])
  if not should_generate_config:
    return None

  # Config exists, generate client connection config.
  client_connection_config = alloydb_messages.ClientConnectionConfig()
  client_connection_config.requireConnectors = require_connectors
  ssl_config = alloydb_messages.SslConfig()
  # Set SSL mode if provided
  ssl_config.sslMode = _ParseSSLMode(alloydb_messages, ssl_mode)
  client_connection_config.sslConfig = ssl_config

  return client_connection_config


def ParseAvailabilityType(alloydb_messages, availability_type):
  if availability_type:
    return alloydb_messages.Instance.AvailabilityTypeValueValuesEnum.lookup_by_name(
        availability_type.upper()
    )
  return None


def _ParseInstanceType(alloydb_messages, instance_type):
  if instance_type:
    return alloydb_messages.Instance.InstanceTypeValueValuesEnum.lookup_by_name(
        instance_type.upper()
    )
  return None


def _ParseUpdateMode(alloydb_messages, update_mode):
  if update_mode:
    return alloydb_messages.UpdatePolicy.ModeValueValuesEnum.lookup_by_name(
        update_mode.upper()
    )
  return None


def _ParseSSLMode(alloydb_messages, ssl_mode):
  if ssl_mode == 'ENCRYPTED_ONLY':
    return alloydb_messages.SslConfig.SslModeValueValuesEnum.ENCRYPTED_ONLY
  elif ssl_mode == 'ALLOW_UNENCRYPTED_AND_ENCRYPTED':
    return (
        alloydb_messages.SslConfig.SslModeValueValuesEnum.ALLOW_UNENCRYPTED_AND_ENCRYPTED
    )
  return None


def _ParsePoolMode(alloydb_messages, pool_mode):
  if pool_mode == 'TRANSACTION':
    return (
        alloydb_messages.ConnectionPoolConfig.PoolModeValueValuesEnum.POOL_MODE_TRANSACTION
    )
  elif pool_mode == 'SESSION':
    return (
        alloydb_messages.ConnectionPoolConfig.PoolModeValueValuesEnum.POOL_MODE_SESSION
    )
  return None


def NetworkConfig(**kwargs):
  """Generates the network config for the instance."""
  assign_inbound_public_ip = kwargs.get('assign_inbound_public_ip')
  authorized_external_networks = kwargs.get('authorized_external_networks')
  alloydb_messages = kwargs.get('alloydb_messages')
  outbound_public_ip = kwargs.get('outbound_public_ip')

  should_generate_config = any([
      assign_inbound_public_ip,
      outbound_public_ip is not None,
      authorized_external_networks is not None,
  ])
  if not should_generate_config:
    return None

  # Config exists, generate instance network config.
  instance_network_config = alloydb_messages.InstanceNetworkConfig()

  if assign_inbound_public_ip:
    instance_network_config.enablePublicIp = _ParseAssignInboundPublicIp(
        assign_inbound_public_ip
    )
  if outbound_public_ip is not None:
    instance_network_config.enableOutboundPublicIp = outbound_public_ip
  if authorized_external_networks is not None:
    if (
        assign_inbound_public_ip is not None
        and not instance_network_config.enablePublicIp
    ):
      raise DetailedArgumentError(
          "Cannot update an instance's authorized "
          'networks and disable Public-IP. You must do '
          'one or the other. Note, that disabling '
          'Public-IP will clear the list of authorized '
          'networks.'
      )
    instance_network_config.authorizedExternalNetworks = (
        _ParseAuthorizedExternalNetworks(
            alloydb_messages,
            authorized_external_networks,
            instance_network_config.enablePublicIp,
        )
    )
  return instance_network_config


def _ConnectionPoolConfig(**kwargs):
  """Generates the connection pooling config for the instance."""
  enable_connection_pooling = kwargs.get('enable_connection_pooling')
  if not enable_connection_pooling:
    return None

  pool_mode = kwargs.get('connection_pooling_pool_mode')
  min_pool_size = kwargs.get('connection_pooling_min_pool_size')
  default_pool_size = kwargs.get('connection_pooling_max_pool_size')
  max_client_conn = kwargs.get('connection_pooling_max_client_conn')
  server_idle_timeout = kwargs.get('connection_pooling_server_idle_timeout')
  query_wait_timeout = kwargs.get('connection_pooling_query_wait_timeout')
  stats_users = kwargs.get('connection_pooling_stats_users')
  ignore_startup_parameters = kwargs.get(
      'connection_pooling_ignore_startup_parameters'
  )

  alloydb_messages = kwargs.get('alloydb_messages')
  config = alloydb_messages.ConnectionPoolConfig()
  config.enable = enable_connection_pooling
  config.enabled = enable_connection_pooling
  if pool_mode is not None:
    config.poolMode = _ParsePoolMode(alloydb_messages, pool_mode)
  if min_pool_size is not None:
    config.minPoolSize = min_pool_size
  if default_pool_size is not None:
    config.defaultPoolSize = default_pool_size
  if max_client_conn is not None:
    config.maxClientConn = max_client_conn
  if server_idle_timeout is not None:
    config.serverIdleTimeout = server_idle_timeout
  if query_wait_timeout is not None:
    config.queryWaitTimeout = query_wait_timeout
  if stats_users is not None:
    config.statsUsers = stats_users
  if ignore_startup_parameters is not None:
    config.ignoreStartupParameters = ignore_startup_parameters
  return config


def _UpdateConnectionPoolConfig(instance_ref, **kwargs):
  """Updates the connection pooling config for the instance.

  Args:
    instance_ref: A reference to the instance to be updated.
    **kwargs: A map of the managed connection pooling flags and their values to
      be updated.

  Returns:
    alloydb_messages.ConnectionPoolConfig
  """
  enable_connection_pooling = kwargs.get('enable_connection_pooling')
  pool_mode = kwargs.get('connection_pooling_pool_mode')
  min_pool_size = kwargs.get('connection_pooling_min_pool_size')
  default_pool_size = kwargs.get('connection_pooling_max_pool_size')
  max_client_conn = kwargs.get('connection_pooling_max_client_conn')
  server_idle_timeout = kwargs.get('connection_pooling_server_idle_timeout')
  query_wait_timeout = kwargs.get('connection_pooling_query_wait_timeout')
  stats_users = kwargs.get('connection_pooling_stats_users')
  ignore_startup_parameters = kwargs.get(
      'connection_pooling_ignore_startup_parameters'
  )
  alloydb_messages = kwargs.get('alloydb_messages')

  should_update_config = any([
      enable_connection_pooling is not None,
      pool_mode is not None,
      min_pool_size is not None,
      default_pool_size is not None,
      max_client_conn is not None,
      server_idle_timeout is not None,
      query_wait_timeout is not None,
      stats_users is not None,
      ignore_startup_parameters is not None,
  ])
  if not should_update_config:
    return None

  config = alloydb_messages.ConnectionPoolConfig()

  # Disabling managed connection pooling should set all other connection pooling
  # settings to None.
  if not enable_connection_pooling and enable_connection_pooling is not None:
    config.enable = False
    config.enabled = False
    return config

  # Build the connection pooling config based on the existing values that are
  # set in the instance, if they aren't specified in the update.
  client = api_util.AlloyDBClient(base.ReleaseTrack.ALPHA)
  alloydb_client = client.alloydb_client
  req = alloydb_messages.AlloydbProjectsLocationsClustersInstancesGetRequest(
      name=instance_ref.RelativeName()
  )
  existing_instance = (
      alloydb_client.projects_locations_clusters_instances.Get(req)
  )

  if enable_connection_pooling is not None:
    config.enable = enable_connection_pooling
    config.enabled = enable_connection_pooling
  else:
    config.enable = existing_instance.connectionPoolConfig.enable
    config.enabled = existing_instance.connectionPoolConfig.enabled

  if pool_mode is not None:
    config.poolMode = _ParsePoolMode(alloydb_messages, pool_mode)
  else:
    config.poolMode = existing_instance.connectionPoolConfig.poolMode
  if min_pool_size is not None:
    config.minPoolSize = min_pool_size
  else:
    config.minPoolSize = existing_instance.connectionPoolConfig.minPoolSize
  if default_pool_size is not None:
    config.defaultPoolSize = default_pool_size
  else:
    config.defaultPoolSize = (
        existing_instance.connectionPoolConfig.defaultPoolSize
    )
  if max_client_conn is not None:
    config.maxClientConn = max_client_conn
  else:
    config.maxClientConn = existing_instance.connectionPoolConfig.maxClientConn
  if server_idle_timeout is not None:
    config.serverIdleTimeout = server_idle_timeout
  else:
    config.serverIdleTimeout = (
        existing_instance.connectionPoolConfig.serverIdleTimeout
    )
  if query_wait_timeout is not None:
    config.queryWaitTimeout = query_wait_timeout
  else:
    config.queryWaitTimeout = (
        existing_instance.connectionPoolConfig.queryWaitTimeout
    )
  if stats_users is not None:
    config.statsUsers = stats_users
  else:
    config.statsUsers = existing_instance.connectionPoolConfig.statsUsers
  if ignore_startup_parameters is not None:
    config.ignoreStartupParameters = ignore_startup_parameters
  else:
    config.ignoreStartupParameters = (
        existing_instance.connectionPoolConfig.ignoreStartupParameters
    )
  return config


def PscInstanceConfig(**kwargs):
  """Generates the PSC instance config for the instance."""
  alloydb_messages = kwargs.get('alloydb_messages')
  allowed_psc_projects = kwargs.get('allowed_psc_projects')
  psc_network_attachment_uri = kwargs.get('psc_network_attachment_uri')
  clear_psc_network_attachment_uri = kwargs.get(
      'clear_psc_network_attachment_uri'
  )
  psc_auto_connections = kwargs.get('psc_auto_connections')
  clear_psc_auto_connections = kwargs.get('clear_psc_auto_connections')

  psc_instance_config = alloydb_messages.PscInstanceConfig()
  if allowed_psc_projects:
    psc_instance_config.allowedConsumerProjects = allowed_psc_projects
  if clear_psc_network_attachment_uri:
    psc_instance_config.pscInterfaceConfigs = []
  elif psc_network_attachment_uri is not None:
    psc_instance_config.pscInterfaceConfigs.append(
        _PscInterfaceConfig(
            alloydb_messages=alloydb_messages,
            psc_network_attachment_uri=psc_network_attachment_uri,
        )
    )
  if clear_psc_auto_connections:
    psc_instance_config.pscAutoConnections = []
  elif psc_auto_connections is not None:
    psc_instance_config.pscAutoConnections = _PscAutoConnections(
        alloydb_messages=alloydb_messages,
        psc_auto_connections=psc_auto_connections,
    )

  return psc_instance_config


def _PscInterfaceConfig(
    alloydb_messages,
    psc_network_attachment_uri=None,
):
  """Generates the PSC interface config for the instance."""
  psc_interface_config = alloydb_messages.PscInterfaceConfig()
  psc_interface_config.networkAttachmentResource = psc_network_attachment_uri
  return psc_interface_config


def _PscAutoConnections(
    alloydb_messages,
    psc_auto_connections=None,
):
  """Generates the PSC auto connections for the instance."""
  out_psc_auto_connections = []
  for connection in psc_auto_connections:
    config = alloydb_messages.PscAutoConnectionConfig()
    config.consumerProject = connection.get('project')
    config.consumerNetwork = connection.get('network')

    if config.consumerProject and config.consumerNetwork:
      out_psc_auto_connections.append(config)
    else:
      raise DetailedArgumentError(
          'Invalid PSC auto connection. Please provide both project and network'
          ' for the PSC auto connection.'
      )
  return out_psc_auto_connections


def _ParseAssignInboundPublicIp(assign_inbound_public_ip):
  """Parses the assign_inbound_public_ip flag.

  Args:
    assign_inbound_public_ip: string, the Public-IP mode to use.

  Returns:
    boolean, whether or not Public-IP is enabled.

  Raises:
    ValueError if try to use any other value besides NO_PUBLIC_IP during
    instance creation, or if use an unrecognized argument.
  """
  if assign_inbound_public_ip == 'NO_PUBLIC_IP':
    return False
  if assign_inbound_public_ip == 'ASSIGN_IPV4':
    return True
  raise DetailedArgumentError(
      'Unrecognized argument. Please use NO_PUBLIC_IP or ASSIGN_IPV4.'
  )


def _ParseAuthorizedExternalNetworks(
    alloydb_messages, authorized_external_networks, public_ip_enabled
):
  """Parses the authorized_external_networks flag.

  Args:
    alloydb_messages: Messages module for the API client.
    authorized_external_networks: list, list of authorized networks.
    public_ip_enabled: boolean, whether or not Public-IP is enabled.

  Returns:
    list of alloydb_messages.AuthorizedNetwork
  """
  auth_networks = []
  if public_ip_enabled is not None and not public_ip_enabled:
    return auth_networks
  for network in authorized_external_networks:
    network = alloydb_messages.AuthorizedNetwork(cidrRange=str(network))
    auth_networks.append(network)
  return auth_networks


def ConstructPatchRequestFromArgsBeta(alloydb_messages, instance_ref, args):
  """Constructs the request to update an AlloyDB instance."""
  instance_resource, paths = ConstructInstanceAndUpdatePathsFromArgsBeta(
      alloydb_messages, instance_ref, args
  )
  mask = ','.join(paths) if paths else None

  return alloydb_messages.AlloydbProjectsLocationsClustersInstancesPatchRequest(
      instance=instance_resource,
      name=instance_ref.RelativeName(),
      updateMask=mask,
  )


def ConstructPatchRequestFromArgsAlpha(alloydb_messages, instance_ref, args):
  """Constructs the request to update an AlloyDB instance."""
  instance_resource, paths = ConstructInstanceAndUpdatePathsFromArgsAlpha(
      alloydb_messages, instance_ref, args
  )

  mask = ','.join(paths) if paths else None

  return alloydb_messages.AlloydbProjectsLocationsClustersInstancesPatchRequest(
      instance=instance_resource,
      name=instance_ref.RelativeName(),
      updateMask=mask,
  )


def ConstructInstanceAndUpdatePathsFromArgsBeta(
    alloydb_messages, instance_ref, args
):
  """Validates command line arguments and creates the instance and update paths for beta track.

  Args:
    alloydb_messages: Messages module for the API client.
    instance_ref: parent resource path of the resource being updated
    args: Command line input arguments.

  Returns:
    An AlloyDB instance and paths for update.
  """
  observability_config_enabled_path = 'observabilityConfig.enabled'
  observability_config_preserve_comments_path = (
      'observabilityConfig.preserveComments'
  )
  observability_config_track_wait_events_path = (
      'observabilityConfig.trackWaitEvents'
  )
  observability_config_max_query_string_length_path = (
      'observabilityConfig.maxQueryStringLength'
  )
  observability_config_record_application_tags_path = (
      'observabilityConfig.recordApplicationTags'
  )
  observability_config_query_plans_per_minute_path = (
      'observabilityConfig.queryPlansPerMinute'
  )
  observability_config_track_active_queries_path = (
      'observabilityConfig.trackActiveQueries'
  )
  instance_resource, paths = ConstructInstanceAndUpdatePathsFromArgs(
      alloydb_messages, instance_ref, args
  )

  if args.update_mode:
    instance_resource.updatePolicy = alloydb_messages.UpdatePolicy(
        mode=_ParseUpdateMode(alloydb_messages, args.update_mode)
    )
    update_mode_path = 'updatePolicy.mode'
    paths.append(update_mode_path)
  if args.observability_config_enabled is not None:
    paths.append(observability_config_enabled_path)
  if args.observability_config_preserve_comments is not None:
    paths.append(observability_config_preserve_comments_path)
  if args.observability_config_track_wait_events is not None:
    paths.append(observability_config_track_wait_events_path)
  if args.observability_config_max_query_string_length is not None:
    paths.append(observability_config_max_query_string_length_path)
  if args.observability_config_record_application_tags is not None:
    paths.append(observability_config_record_application_tags_path)
  if args.observability_config_query_plans_per_minute is not None:
    paths.append(observability_config_query_plans_per_minute_path)
  if args.observability_config_track_active_queries is not None:
    paths.append(observability_config_track_active_queries_path)

  instance_resource.observabilityConfig = _ObservabilityConfig(
      alloydb_messages,
      args.observability_config_enabled,
      args.observability_config_preserve_comments,
      args.observability_config_track_wait_events,
      args.observability_config_max_query_string_length,
      args.observability_config_record_application_tags,
      args.observability_config_query_plans_per_minute,
      args.observability_config_track_active_queries,
  )

  return instance_resource, paths


def ConstructInstanceAndUpdatePathsFromArgsAlpha(
    alloydb_messages, instance_ref, args
):
  """Validates command line arguments and creates the instance and update paths for alpha track.

  Args:
    alloydb_messages: Messages module for the API client.
    instance_ref: parent resource path of the resource being updated
    args: Command line input arguments.

  Returns:
    An AlloyDB instance and paths for update.
  """
  instance_resource, paths = ConstructInstanceAndUpdatePathsFromArgsBeta(
      alloydb_messages, instance_ref, args
  )

  # We update the whole connection pool config if any of the connection pooling
  # flags are set. Unforunately, we can't update individual fields within the
  # connection pool config due to a bug in the API so this is a workaround.
  if (args.enable_connection_pooling is not None
      or args.connection_pooling_pool_mode is not None
      or args.connection_pooling_min_pool_size is not None
      or args.connection_pooling_max_pool_size is not None
      or args.connection_pooling_max_client_connections is not None
      or args.connection_pooling_server_idle_timeout is not None
      or args.connection_pooling_query_wait_timeout is not None
      or args.connection_pooling_stats_users is not None
      or args.connection_pooling_ignore_startup_parameters is not None):
    paths.append('connectionPoolConfig')

  instance_resource.connectionPoolConfig = _UpdateConnectionPoolConfig(
      instance_ref,
      alloydb_messages=alloydb_messages,
      enable_connection_pooling=args.enable_connection_pooling,
      connection_pooling_pool_mode=args.connection_pooling_pool_mode,
      connection_pooling_min_pool_size=args.connection_pooling_min_pool_size,
      connection_pooling_max_pool_size=args.connection_pooling_max_pool_size,
      connection_pooling_max_client_conn=args.connection_pooling_max_client_connections,
      connection_pooling_server_idle_timeout=args.connection_pooling_server_idle_timeout,
      connection_pooling_query_wait_timeout=args.connection_pooling_query_wait_timeout,
      connection_pooling_stats_users=args.connection_pooling_stats_users,
      connection_pooling_ignore_startup_parameters=args.connection_pooling_ignore_startup_parameters,
  )
  return instance_resource, paths


def ConstructRestartRequestFromArgs(alloydb_messages, project_ref, args):
  """Constructs the request to restart an AlloyDB instance.

  Args:
    alloydb_messages: Messages module for the API client.
    project_ref: parent resource path of the resource being updated
    args: Command line input arguments.

  Returns:
    Fully-constructed request to restart an AlloyDB instance.
  """
  req = (
      alloydb_messages.AlloydbProjectsLocationsClustersInstancesRestartRequest(
          name=project_ref.RelativeName(),
      )
  )
  if args.node_ids:
    restart_request = alloydb_messages.RestartInstanceRequest(
        nodeIds=args.node_ids
    )
    req.restartInstanceRequest = restart_request
  return req
