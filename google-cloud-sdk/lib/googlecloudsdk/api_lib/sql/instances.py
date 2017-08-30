# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Common utility functions for sql instances."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.sql import api_util
from googlecloudsdk.api_lib.sql import instance_prop_reducers as reducers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.util import labels_util
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io


# TODO(b/35104889): Migrate methods containing Namespace args to command_lib
# TODO(b/35930151): Make methods in api_lib command-agnostic
class _BaseInstances(object):
  """Common utility functions for sql instances."""

  @staticmethod
  def GetDatabaseInstances():
    """Gets SQL instances in a given project.

    Modifies current state of an individual instance to 'STOPPED' if
    activationPolicy is 'NEVER'.

    Returns:
      List of yielded sql_messages.DatabaseInstance instances.
    """

    client = api_util.SqlClient(api_util.API_VERSION_DEFAULT)
    sql_client = client.sql_client
    sql_messages = client.sql_messages
    project_id = properties.VALUES.core.project.Get(required=True)

    yielded = list_pager.YieldFromList(
        sql_client.instances,
        sql_messages.SqlInstancesListRequest(project=project_id))

    def YieldInstancesWithAModifiedState():
      for result in yielded:
        # TODO(b/63139112): Investigate impact of instances without settings.
        if result.settings and result.settings.activationPolicy == 'NEVER':
          result.state = 'STOPPED'
        yield result

    return YieldInstancesWithAModifiedState()

  @classmethod
  def _ConstructSettingsFromArgs(cls, sql_messages, args, instance=None):
    """Constructs instance settings from the command line arguments.

    Args:
      sql_messages: module, The messages module that should be used.
      args: argparse.Namespace, The arguments that this command was invoked
          with.
      instance: sql_messages.DatabaseInstance, The original instance, for
          settings that depend on the previous state.

    Returns:
      A settings object representing the instance settings.

    Raises:
      ToolException: An error other than http error occured while executing the
          command.
    """
    settings = sql_messages.Settings(
        tier=reducers.MachineType(instance, args.tier, args.memory, args.cpu),
        pricingPlan=args.pricing_plan,
        replicationType=args.replication,
        activationPolicy=args.activation_policy)

    labels = None
    if hasattr(args, 'labels'):
      labels = reducers.UserLabels(sql_messages, instance, labels=args.labels)
    elif (hasattr(args, 'update_labels') and args.update_labels or
          hasattr(args, 'remove_labels') and args.remove_labels):
      update_labels, remove_labels = labels_util.GetAndValidateOpsFromArgs(args)
      labels = reducers.UserLabels(
          sql_messages,
          instance,
          update_labels=update_labels,
          remove_labels=remove_labels)
    elif hasattr(args, 'clear_labels'):
      labels = reducers.UserLabels(
          sql_messages, instance, clear_labels=args.clear_labels)
    if labels:
      settings.userLabels = labels

    # these args are only present for the patch command
    clear_authorized_networks = getattr(args, 'clear_authorized_networks',
                                        False)
    clear_gae_apps = getattr(args, 'clear_gae_apps', False)

    if args.authorized_gae_apps:
      settings.authorizedGaeApplications = args.authorized_gae_apps
    elif clear_gae_apps:
      settings.authorizedGaeApplications = []

    if any([
        args.assign_ip is not None, args.require_ssl is not None,
        args.authorized_networks, clear_authorized_networks
    ]):
      settings.ipConfiguration = sql_messages.IpConfiguration()
      if args.assign_ip is not None:
        if hasattr(settings.ipConfiguration, 'enabled'):
          # v1beta3 is being used; use 'enabled' instead of 'ipv4Enabled'.
          settings.ipConfiguration.enabled = args.assign_ip
        else:
          settings.ipConfiguration.ipv4Enabled = args.assign_ip

      if args.authorized_networks:
        # AclEntry is only available in the v1beta4 version of the API. If it is
        # present, the API expects an AclEntry for the authorizedNetworks list;
        # otherwise, it expects a string.
        if getattr(sql_messages, 'AclEntry', None) is not None:
          authorized_networks = [
              sql_messages.AclEntry(value=n) for n in args.authorized_networks
          ]
        else:
          authorized_networks = args.authorized_networks
        settings.ipConfiguration.authorizedNetworks = authorized_networks
      if clear_authorized_networks:
        # For patch requests, this field needs to be labeled explicitly cleared.
        settings.ipConfiguration.authorizedNetworks = []

      if args.require_ssl is not None:
        settings.ipConfiguration.requireSsl = args.require_ssl

    if any([args.follow_gae_app, args.gce_zone]):
      settings.locationPreference = sql_messages.LocationPreference(
          followGaeApplication=args.follow_gae_app, zone=args.gce_zone)

    if getattr(args, 'enable_database_replication', None) is not None:
      settings.databaseReplicationEnabled = args.enable_database_replication

    return settings

  @classmethod
  def ConstructInstanceFromArgs(cls,
                                sql_messages,
                                args,
                                original=None,
                                instance_ref=None):
    """Construct a Cloud SQL instance from command line args.

    Args:
      sql_messages: module, The messages module that should be used.
      args: argparse.Namespace, The CLI arg namespace.
      original: sql_messages.DatabaseInstance, The original instance, if some of
          it might be used to fill fields in the new one.
      instance_ref: reference to DatabaseInstance object, used to fill project
          and instance information.

    Returns:
      sql_messages.DatabaseInstance, The constructed (and possibly partial)
      database instance.

    Raises:
      ToolException: An error other than http error occured while executing the
          command.
    """
    original_settings = original.settings if original else None
    settings = cls._ConstructSettingsFromArgs(sql_messages, args, original)
    backup_configuration = (reducers.BackupConfiguration(
        sql_messages, original,
        getattr(args, 'backup', None),
        getattr(args, 'no_backup', None),
        getattr(args, 'backup_start_time', None),
        getattr(args, 'enable_bin_log', None)))
    if backup_configuration:
      cls.AddBackupConfigToSettings(settings, backup_configuration)
    settings.databaseFlags = (reducers.DatabaseFlags(
        sql_messages, original_settings,
        getattr(args, 'database_flags', None),
        getattr(args, 'clear_database_flags', None)))
    settings.maintenanceWindow = (reducers.MaintenanceWindow(
        sql_messages, original,
        getattr(args, 'maintenance_release_channel', None),
        getattr(args, 'maintenance_window_day', None),
        getattr(args, 'maintenance_window_hour', None)))

    on_premises_host_port = getattr(args, 'on_premises_host_port', None)
    if on_premises_host_port:
      if args.require_ssl:
        raise exceptions.ToolException('Argument --on-premises-host-port not '
                                       'allowed with --require_ssl')
      settings.onPremisesConfiguration = sql_messages.OnPremisesConfiguration(
          hostPort=on_premises_host_port)

    storage_size = getattr(args, 'storage_size', None)
    if storage_size:
      settings.dataDiskSizeGb = int(storage_size / (1 << 30))

    # these flags are only present for the create command
    region = getattr(args, 'region', None)
    database_version = getattr(args, 'database_version', None)

    instance_resource = sql_messages.DatabaseInstance(
        region=region,
        databaseVersion=database_version,
        masterInstanceName=getattr(args, 'master_instance_name', None),
        settings=settings)

    if hasattr(args, 'master_instance_name'):
      if args.master_instance_name:
        replication = 'ASYNCHRONOUS'
        if hasattr(args, 'replica_type') and args.replica_type == 'FAILOVER':
          instance_resource.replicaConfiguration = (
              sql_messages.ReplicaConfiguration(failoverTarget=True))
      else:
        replication = 'SYNCHRONOUS'
      if not args.replication:
        instance_resource.settings.replicationType = replication

    if instance_ref:
      cls.SetProjectAndInstanceFromRef(instance_resource, instance_ref)

    if hasattr(args, 'storage_type') and args.storage_type:
      instance_resource.settings.dataDiskType = 'PD_' + args.storage_type

    if hasattr(args, 'failover_replica_name') and args.failover_replica_name:
      instance_resource.failoverReplica = (
          sql_messages.DatabaseInstance.FailoverReplicaValue(
              name=args.failover_replica_name))

    if (hasattr(args, 'storage_auto_increase') and
        args.storage_auto_increase is not None):
      instance_resource.settings.storageAutoResize = args.storage_auto_increase

    if (hasattr(args, 'storage_auto_increase_limit') and
        args.IsSpecified('storage_auto_increase_limit')):
      # Resize limit should be settable if the original instance has resize
      # turned on, or if the instance to be created has resize flag.
      if (original and original.settings.storageAutoResize) or (
          args.storage_auto_increase):
        # If the limit is set to None, we want it to be set to 0. This is a
        # backend requirement.
        instance_resource.settings.storageAutoResizeLimit = (
            args.storage_auto_increase_limit) or 0
      else:
        raise exceptions.RequiredArgumentException(
            '--storage-auto-increase', 'To set the storage capacity limit '
            'using [--storage-auto-increase-limit], [--storage-auto-increase] '
            'must be enabled.')

    return instance_resource

  @staticmethod
  def PrintAndConfirmAuthorizedNetworksOverwrite():
    console_io.PromptContinue(
        message='When adding a new IP address to authorized networks, '
        'make sure to also include any IP addresses that have already been '
        'authorized. Otherwise, they will be overwritten and de-authorized.',
        default=True,
        cancel_on_no=True)


class InstancesV1Beta3(_BaseInstances):
  """Common utility functions for sql instances V1Beta3."""

  @staticmethod
  def SetProjectAndInstanceFromRef(instance_resource, instance_ref):
    instance_resource.project = instance_ref.project
    instance_resource.instance = instance_ref.instance

  @staticmethod
  def AddBackupConfigToSettings(settings, backup_config):
    settings.backupConfiguration = [backup_config]


class InstancesV1Beta4(_BaseInstances):
  """Common utility functions for sql instances V1Beta4."""

  @staticmethod
  def SetProjectAndInstanceFromRef(instance_resource, instance_ref):
    instance_resource.project = instance_ref.project
    instance_resource.name = instance_ref.instance

  @staticmethod
  def AddBackupConfigToSettings(settings, backup_config):
    settings.backupConfiguration = backup_config
