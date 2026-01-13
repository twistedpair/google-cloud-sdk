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
"""Cloud Workstations configs API utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.api_lib.workstations.util import GetClientInstance
from googlecloudsdk.api_lib.workstations.util import GetMessagesModule
from googlecloudsdk.api_lib.workstations.util import VERSION_MAP
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
import six


IMAGE_URL_MAP = {
    'base-image': (
        '{location}-docker.pkg.dev/cloud-workstations-images/predefined/base:latest'
    ),
    'clion': (
        '{location}-docker.pkg.dev/cloud-workstations-images/predefined/clion:latest'
    ),
    'codeoss': (
        '{location}-docker.pkg.dev/cloud-workstations-images/predefined/code-oss:latest'
    ),
    'codeoss-cuda': (
        '{location}-docker.pkg.dev/cloud-workstations-images/predefined/code-oss-cuda:latest'
    ),
    'goland': (
        '{location}-docker.pkg.dev/cloud-workstations-images/predefined/goland:latest'
    ),
    'intellij': (
        '{location}-docker.pkg.dev/cloud-workstations-images/predefined/intellij-ultimate:latest'
    ),
    'phpstorm': (
        '{location}-docker.pkg.dev/cloud-workstations-images/predefined/phpstorm:latest'
    ),
    'pycharm': (
        '{location}-docker.pkg.dev/cloud-workstations-images/predefined/pycharm:latest'
    ),
    'rider': (
        '{location}-docker.pkg.dev/cloud-workstations-images/predefined/rider:latest'
    ),
    'rubymine': (
        '{location}-docker.pkg.dev/cloud-workstations-images/predefined/rubymine:latest'
    ),
    'webstorm': (
        '{location}-docker.pkg.dev/cloud-workstations-images/predefined/webstorm:latest'
    ),
}

BOOST_CONFIG_MAP = {
    'id': 'id',
    'machine-type': 'machineType',
    'pool-size': 'poolSize',
    'boot-disk-size': 'bootDiskSizeGb',
    'enable-nested-virtualization': 'enableNestedVirtualization',
    'reservation-affinity': 'reservationAffinity',
}

RESERVATION_AFFINITY_MAP = {
    'key': 'key',
    'consume-reservation-type': 'consumeReservationType',
    'values': 'values',
}


class Configs:
  """The Configs set of Cloud Workstations API functions."""

  def __init__(self, release_track=base.ReleaseTrack.BETA):
    self.api_version = VERSION_MAP.get(release_track)
    self.client = GetClientInstance(release_track)
    self.messages = GetMessagesModule(release_track)
    self._service = (
        self.client.projects_locations_workstationClusters_workstationConfigs
    )

  def Create(self, args):  # pylint: disable=invalid-name
    """Create a new workstation configuration.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Returns:
      Workstation configuration that was created.
    """
    config_name = args.CONCEPTS.config.Parse().RelativeName()
    parent = config_name.split('/workstationConfigs/')[0]
    location = re.search(r'/locations/(?P<location>[^/]+)/', config_name).group(
        'location'
    )
    config_id = config_name.split('/workstationConfigs/')[1]

    config = self.messages.WorkstationConfig()
    config.name = config_name
    config.idleTimeout = '{}s'.format(args.idle_timeout)
    config.runningTimeout = '{}s'.format(args.running_timeout)
    if args.labels:
      config.labels = self.messages.WorkstationConfig.LabelsValue(
          additionalProperties=[
              self.messages.WorkstationConfig.LabelsValue.AdditionalProperty(
                  key=key, value=value
              )
              for key, value in sorted(six.iteritems(args.labels))
          ]
      )
    config.disableTcpConnections = args.disable_tcp_connections
    config.maxUsableWorkstations = args.max_usable_workstations_count

    # GCE Instance Config
    config.host = self.messages.Host()
    config.host.gceInstance = self.messages.GceInstance()
    config.host.gceInstance.machineType = args.machine_type
    config.host.gceInstance.serviceAccount = args.service_account
    if args.service_account_scopes:
      config.host.gceInstance.serviceAccountScopes = args.service_account_scopes
    if args.network_tags:
      config.host.gceInstance.tags = args.network_tags
    config.host.gceInstance.poolSize = args.pool_size
    config.host.gceInstance.disablePublicIpAddresses = (
        args.disable_public_ip_addresses
    )
    config.host.gceInstance.shieldedInstanceConfig = (
        self.messages.GceShieldedInstanceConfig(
            enableSecureBoot=args.shielded_secure_boot,
            enableVtpm=args.shielded_vtpm,
            enableIntegrityMonitoring=args.shielded_integrity_monitoring,
        )
    )
    config.host.gceInstance.confidentialInstanceConfig = (
        self.messages.GceConfidentialInstanceConfig(
            enableConfidentialCompute=args.enable_confidential_compute
        )
    )
    config.host.gceInstance.enableNestedVirtualization = (
        args.enable_nested_virtualization
    )
    config.host.gceInstance.bootDiskSizeGb = args.boot_disk_size
    if args.IsSpecified('disable_ssh_to_vm'):
      config.host.gceInstance.disableSsh = args.disable_ssh_to_vm
    else:
      config.host.gceInstance.disableSsh = not args.enable_ssh_to_vm
    if args.accelerator_type and args.accelerator_count:
      accelerators = [
          self.messages.Accelerator(
              type=args.accelerator_type,
              count=args.accelerator_count,
          )
      ]
      config.host.gceInstance.accelerators = accelerators
    if args.startup_script_uri:
      config.host.gceInstance.startupScriptUri = args.startup_script_uri

    if args.instance_metadata:
      instance_metadata_value_message = (
          self.messages.GceInstance.InstanceMetadataValue
      )
      additional_property_message = (
          self.messages.GceInstance.InstanceMetadataValue.AdditionalProperty
      )
      config.host.gceInstance.instanceMetadata = (
          instance_metadata_value_message(
              additionalProperties=[
                  additional_property_message(key=key, value=value)
                  for key, value in args.instance_metadata.items()
              ]
          )
      )

    if self.api_version != VERSION_MAP.get(base.ReleaseTrack.GA):
      config.httpOptions = self.messages.HttpOptions()
      if args.allow_unauthenticated_cors_preflight_requests:
        config.httpOptions.allowedUnauthenticatedCorsPreflightRequests = True
      if args.disable_localhost_replacement:
        config.httpOptions.disableLocalhostReplacement = True

    if (
        self.api_version != VERSION_MAP.get(base.ReleaseTrack.GA)
        and args.boost_config
    ):
      for boost_config in args.boost_config:
        desired_boost_config = self.messages.BoostConfig()
        for key, value in boost_config.items():
          if key == 'accelerator-type' or key == 'accelerator-count':
            desired_boost_config.accelerators = [
                self.messages.Accelerator(
                    type=boost_config.get('accelerator-type', ''),
                    count=boost_config.get('accelerator-count', 0),
                )
            ]
          elif key == 'reservation-affinity':
            desired_reservation_affinity = self.messages.ReservationAffinity()
            for key, value in boost_config.get(
                'reservation-affinity', {}
            ).items():
              if key == 'consume-reservation-type':
                value = self.messages.ReservationAffinity.ConsumeReservationTypeValueValuesEnum(
                    value
                )
              setattr(
                  desired_reservation_affinity,
                  RESERVATION_AFFINITY_MAP.get(key),
                  value,
              )
            desired_boost_config.reservationAffinity = (
                desired_reservation_affinity
            )
          else:
            setattr(desired_boost_config, BOOST_CONFIG_MAP.get(key), value)
        config.host.gceInstance.boostConfigs.append(desired_boost_config)

    if (
        self.api_version != VERSION_MAP.get(base.ReleaseTrack.GA)
        and args.reservation_affinity
    ):
      desired_reservation_affinity = self.messages.ReservationAffinity()
      for key, value in args.reservation_affinity.items():
        if key == 'consume-reservation-type':
          value = self.messages.ReservationAffinity.ConsumeReservationTypeValueValuesEnum(
              value
          )
        setattr(
            desired_reservation_affinity,
            RESERVATION_AFFINITY_MAP.get(key),
            value,
        )
      config.host.gceInstance.reservationAffinity = desired_reservation_affinity

    if args.allowed_ports:
      for port_range in args.allowed_ports:
        desired_port_range = self.messages.PortRange()
        for key, value in port_range.items():
          setattr(desired_port_range, key, value)
        config.allowedPorts.append(desired_port_range)

    # Persistent directory
    if not args.no_persistent_storage:
      pd = self.messages.PersistentDirectory()
      pd.mountPath = '/home'

      use_disk_flags = (
          (args.IsKnownAndSpecified('disk_type'))
          or (args.IsKnownAndSpecified('disk_size'))
          or (args.IsKnownAndSpecified('disk_source_snapshot'))
          or (args.IsKnownAndSpecified('disk_reclaim_policy'))
      )

      if use_disk_flags:
        disk_type = (
            args.disk_type if args.IsSpecified('disk_type') else 'pd-standard'
        )
        source_snapshot = (
            args.disk_source_snapshot
            if args.IsSpecified('disk_source_snapshot')
            else None
        )
        disk_size = args.disk_size if args.IsSpecified('disk_size') else 200
        reclaim_policy = (
            args.disk_reclaim_policy
            if args.IsSpecified('disk_reclaim_policy')
            else 'delete'
        )
      else:
        disk_type = args.pd_disk_type
        disk_size = args.pd_disk_size
        source_snapshot = args.pd_source_snapshot
        reclaim_policy = args.pd_reclaim_policy

      # Not all instance types can take Hyperdisks, but this is validated on the
      # backend.
      if disk_type == 'hyperdisk-balanced-ha':
        pd.gceHd = self.messages.GceHyperdiskBalancedHighAvailability(
            sizeGb=0 if source_snapshot else disk_size,
            reclaimPolicy=(
                self.messages.GceHyperdiskBalancedHighAvailability.ReclaimPolicyValueValuesEnum.RETAIN
                if reclaim_policy == 'retain'
                else self.messages.GceHyperdiskBalancedHighAvailability.ReclaimPolicyValueValuesEnum.DELETE
            ),
            sourceSnapshot=source_snapshot,
        )
      else:
        pd.gcePd = self.messages.GceRegionalPersistentDisk(
            sizeGb=0 if source_snapshot else disk_size,
            fsType='' if source_snapshot else 'ext4',
            diskType=disk_type,
            reclaimPolicy=(
                self.messages.GceRegionalPersistentDisk.ReclaimPolicyValueValuesEnum.RETAIN
                if reclaim_policy == 'retain'
                else self.messages.GceRegionalPersistentDisk.ReclaimPolicyValueValuesEnum.DELETE
            ),
            sourceSnapshot=source_snapshot,
        )
      config.persistentDirectories.append(pd)

    # Ephemeral directory
    if args.ephemeral_directory:
      for directory in args.ephemeral_directory:
        pd = self.messages.EphemeralDirectory()
        pd.mountPath = directory.get('mount-path')
        pd.gcePd = self.messages.GcePersistentDisk(
            diskType=directory.get('disk-type'),
            sourceSnapshot=directory.get('source-snapshot'),
            sourceImage=directory.get('source-image'),
            readOnly=directory.get('read-only'),
        )
        config.ephemeralDirectories.append(pd)

    # Container
    config.container = self.messages.Container()
    if args.container_custom_image:
      config.container.image = args.container_custom_image
    elif args.container_predefined_image:
      config.container.image = IMAGE_URL_MAP.get(
          args.container_predefined_image
      ).format(location=location)
    if args.container_command:
      config.container.command = args.container_command
    if args.container_args:
      config.container.args = args.container_args
    if args.container_env:
      env_val = self.messages.Container.EnvValue()
      for key, value in args.container_env.items():
        env_val.additionalProperties.append(
            self.messages.Container.EnvValue.AdditionalProperty(
                key=key, value=value
            )
        )
      config.container.env = env_val
    config.container.workingDir = args.container_working_dir
    config.container.runAsUser = args.container_run_as_user

    # Encryption key
    encryption_key = self.messages.CustomerEncryptionKey()
    if args.kms_key:
      encryption_key.kmsKey = args.kms_key
    if args.kms_key_service_account:
      encryption_key.kmsKeyServiceAccount = args.kms_key_service_account
    config.encryptionKey = encryption_key

    if args.enable_audit_agent:
      config.enableAuditAgent = args.enable_audit_agent

    if args.grant_workstation_admin_role_on_create:
      config.grantWorkstationAdminRoleOnCreate = (
          args.grant_workstation_admin_role_on_create
      )

    if args.replica_zones:
      config.replicaZones = args.replica_zones

    if args.vm_tags:
      tags_val = self.messages.GceInstance.VmTagsValue()
      for key, value in args.vm_tags.items():
        tags_val.additionalProperties.append(
            self.messages.GceInstance.VmTagsValue.AdditionalProperty(
                key=key, value=value
            )
        )
      config.host.gceInstance.vmTags = tags_val

    create_req = self.messages.WorkstationsProjectsLocationsWorkstationClustersWorkstationConfigsCreateRequest(
        parent=parent, workstationConfigId=config_id, workstationConfig=config
    )
    op_ref = self._service.Create(create_req)

    log.status.Print('Create request issued for: [{}]'.format(config_id))

    if args.async_:
      log.status.Print('Check operation [{}] for status.'.format(op_ref.name))
      return op_ref

    op_resource = resources.REGISTRY.ParseRelativeName(
        op_ref.name,
        collection='workstations.projects.locations.operations',
        api_version=self.api_version,
    )
    poller = waiter.CloudOperationPoller(
        self._service, self.client.projects_locations_operations
    )

    result = waiter.WaitFor(
        poller,
        op_resource,
        'Waiting for operation [{}] to complete'.format(op_ref.name),
    )
    log.status.Print('Created configuration [{}].'.format(config_id))

    return result

  def Update(self, args):  # pylint: disable=invalid-name
    """Updates an existing workstation configuration.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Returns:
      Workstation configuration that was updated.
    """
    config_name = args.CONCEPTS.config.Parse().RelativeName()
    location = re.search(r'/locations/(?P<location>[^/]+)/', config_name).group(
        'location'
    )
    config_id = config_name.split('/workstationConfigs/')[1]

    config = self.messages.WorkstationConfig()
    config.name = config_name
    get_req = self.messages.WorkstationsProjectsLocationsWorkstationClustersWorkstationConfigsGetRequest(
        name=config_name
    )
    old_config = self._service.Get(get_req)
    update_mask = []

    if args.IsSpecified('idle_timeout'):
      config.idleTimeout = '{}s'.format(args.idle_timeout)
      update_mask.append('idle_timeout')

    if args.IsSpecified('running_timeout'):
      config.runningTimeout = '{}s'.format(args.running_timeout)
      update_mask.append('running_timeout')

    if args.IsSpecified('labels'):
      config.labels = self.messages.WorkstationConfig.LabelsValue(
          additionalProperties=[
              self.messages.WorkstationConfig.LabelsValue.AdditionalProperty(
                  key=key, value=value
              )
              for key, value in sorted(six.iteritems(args.labels))
          ]
      )
      update_mask.append('labels')

    if args.IsSpecified('max_usable_workstations_count'):
      config.maxUsableWorkstations = args.max_usable_workstations_count
      update_mask.append('max_usable_workstations')

    if self.api_version != VERSION_MAP.get(base.ReleaseTrack.GA):
      config.httpOptions = self.messages.HttpOptions()
      if args.allow_unauthenticated_cors_preflight_requests:
        config.httpOptions.allowedUnauthenticatedCorsPreflightRequests = True
        update_mask.append(
            'http_options.allowed_unauthenticated_cors_preflight_requests'
        )
      if args.disallow_unauthenticated_cors_preflight_requests:
        config.httpOptions.allowedUnauthenticatedCorsPreflightRequests = False
        update_mask.append(
            'http_options.allowed_unauthenticated_cors_preflight_requests'
        )

      if args.enable_localhost_replacement:
        config.httpOptions.disableLocalhostReplacement = False
        update_mask.append('http_options.disable_localhost_replacement')
      if args.disable_localhost_replacement:
        config.httpOptions.disableLocalhostReplacement = True
        update_mask.append('http_options.disable_localhost_replacement')

    # GCE Instance Config
    config.host = self.messages.Host()
    config.host.gceInstance = self.messages.GceInstance()
    if args.IsSpecified('machine_type'):
      config.host.gceInstance.machineType = args.machine_type
      update_mask.append('host.gce_instance.machine_type')

    if self.api_version != VERSION_MAP.get(
        base.ReleaseTrack.GA
    ) and args.IsSpecified('reservation_affinity'):
      desired_reservation_affinity = self.messages.ReservationAffinity()
      for key, value in args.reservation_affinity.items():
        if key == 'consume-reservation-type':
          value = self.messages.ReservationAffinity.ConsumeReservationTypeValueValuesEnum(
              value
          )
        setattr(
            desired_reservation_affinity,
            RESERVATION_AFFINITY_MAP.get(key),
            value,
        )
      config.host.gceInstance.reservationAffinity = desired_reservation_affinity
      update_mask.append('host.gce_instance.reservation_affinity')

    if args.IsSpecified('service_account'):
      config.host.gceInstance.serviceAccount = args.service_account
      update_mask.append('host.gce_instance.service_account')

    if args.IsSpecified('service_account_scopes'):
      config.host.gceInstance.serviceAccountScopes = args.service_account_scopes
      update_mask.append('host.gce_instance.service_account_scopes')

    if args.IsSpecified('network_tags'):
      config.host.gceInstance.tags = args.network_tags
      update_mask.append('host.gce_instance.tags')

    if args.IsSpecified('pool_size'):
      config.host.gceInstance.poolSize = args.pool_size
      update_mask.append('host.gce_instance.pool_size')

    if args.IsSpecified('disable_public_ip_addresses'):
      config.host.gceInstance.disablePublicIpAddresses = (
          args.disable_public_ip_addresses
      )
      update_mask.append('host.gce_instance.disable_public_ip_addresses')

    if args.IsSpecified('boot_disk_size'):
      config.host.gceInstance.bootDiskSizeGb = args.boot_disk_size
      update_mask.append('host.gce_instance.boot_disk_size_gb')

    if args.IsKnownAndSpecified('disable_ssh_to_vm'):
      config.host.gceInstance.disableSsh = args.disable_ssh_to_vm
      update_mask.append('host.gce_instance.disable_ssh')

    if args.IsKnownAndSpecified('enable_ssh_to_vm'):
      config.host.gceInstance.disableSsh = not args.enable_ssh_to_vm
      update_mask.append('host.gce_instance.disable_ssh')

    if args.IsSpecified('enable_confidential_compute'):
      config.host.gceInstance.confidentialInstanceConfig = (
          self.messages.GceConfidentialInstanceConfig(
              enableConfidentialCompute=args.enable_confidential_compute
          )
      )
      update_mask.append(
          'host.gce_instance.confidential_instance_config.enable_confidential_compute'
      )

    if args.IsSpecified('enable_audit_agent'):
      config.enableAuditAgent = args.enable_audit_agent
      update_mask.append('enable_audit_agent')

    if args.IsSpecified('grant_workstation_admin_role_on_create'):
      config.grantWorkstationAdminRoleOnCreate = (
          args.grant_workstation_admin_role_on_create
      )
      update_mask.append('grant_workstation_admin_role_on_create')

    if args.IsSpecified('disable_tcp_connections'):
      config.disableTcpConnections = args.disable_tcp_connections
      update_mask.append('disable_tcp_connections')

    if args.IsSpecified('enable_tcp_connections'):
      config.disableTcpConnections = not args.enable_tcp_connections
      update_mask.append('disable_tcp_connections')

    if args.IsSpecified('enable_nested_virtualization'):
      config.host.gceInstance.enableNestedVirtualization = (
          args.enable_nested_virtualization
      )
      update_mask.append('host.gce_instance.enable_nested_virtualization')

    if args.startup_script_uri:
      config.host.gceInstance.startupScriptUri = args.startup_script_uri
      update_mask.append('host.gce_instance.startup_script_uri')

    if args.instance_metadata:
      instance_metadata_value_message = (
          self.messages.GceInstance.InstanceMetadataValue
      )
      additional_property_message = (
          self.messages.GceInstance.InstanceMetadataValue.AdditionalProperty
      )
      config.host.gceInstance.instanceMetadata = (
          instance_metadata_value_message(
              additionalProperties=[
                  additional_property_message(key=key, value=value)
                  for key, value in args.instance_metadata.items()
              ]
          )
      )
      update_mask.append('host.gce_instance.instance_metadata')

    # Shielded Instance Config
    gce_shielded_instance_config = self.messages.GceShieldedInstanceConfig()
    if args.IsSpecified('shielded_secure_boot'):
      gce_shielded_instance_config.enableSecureBoot = args.shielded_secure_boot
      update_mask.append(
          'host.gce_instance.shielded_instance_config.enable_secure_boot'
      )

    if args.IsSpecified('shielded_vtpm'):
      gce_shielded_instance_config.enableVtpm = args.shielded_vtpm
      update_mask.append(
          'host.gce_instance.shielded_instance_config.enable_vtpm'
      )

    if args.IsSpecified('shielded_integrity_monitoring'):
      gce_shielded_instance_config.enableIntegrityMonitoring = (
          args.shielded_integrity_monitoring
      )
      update_mask.append(
          'host.gce_instance.shielded_instance_config.enable_integrity_monitoring'
      )

    config.host.gceInstance.shieldedInstanceConfig = (
        gce_shielded_instance_config
    )

    if args.IsSpecified('accelerator_type') or args.IsSpecified(
        'accelerator_count'
    ):
      accelerators = [
          self.messages.Accelerator(
              type=args.accelerator_type,
              count=args.accelerator_count,
          )
      ]
      config.host.gceInstance.accelerators = accelerators
      update_mask.append('host.gce_instance.accelerators')

    if self.api_version != VERSION_MAP.get(
        base.ReleaseTrack.GA
    ) and args.IsSpecified('boost_config'):
      for boost_config in args.boost_config:
        desired_boost_config = self.messages.BoostConfig()
        for key, value in boost_config.items():
          if key == 'accelerator-type' or key == 'accelerator-count':
            desired_boost_config.accelerators = [
                self.messages.Accelerator(
                    type=boost_config['accelerator-type'],
                    count=boost_config['accelerator-count'],
                )
            ]
          elif key == 'reservation-affinity':
            desired_reservation_affinity = self.messages.ReservationAffinity()
            for key, value in boost_config['reservation-affinity'].items():
              if key == 'consume-reservation-type':
                value = self.messages.ReservationAffinity.ConsumeReservationTypeValueValuesEnum(
                    value
                )
              setattr(
                  desired_reservation_affinity,
                  RESERVATION_AFFINITY_MAP.get(key),
                  value,
              )
            desired_boost_config.reservationAffinity = (
                desired_reservation_affinity
            )
          else:
            setattr(desired_boost_config, BOOST_CONFIG_MAP.get(key), value)
        config.host.gceInstance.boostConfigs.append(desired_boost_config)
      update_mask.append('host.gce_instance.boost_configs')

    if args.IsSpecified('allowed_ports'):
      config.allowedPorts = []
      for port_range in args.allowed_ports:
        desired_port_range = self.messages.PortRange()
        for key, value in port_range.items():
          setattr(desired_port_range, key, value)
        config.allowedPorts.append(desired_port_range)
      update_mask.append('allowed_ports')

    # Container
    config.container = self.messages.Container()
    if args.IsSpecified('container_custom_image'):
      config.container.image = args.container_custom_image
      update_mask.append('container.image')
    elif args.IsSpecified('container_predefined_image'):
      config.container.image = IMAGE_URL_MAP.get(
          args.container_predefined_image
      ).format(location=location)
      update_mask.append('container.image')

    if args.IsSpecified('container_command'):
      config.container.command = args.container_command
      update_mask.append('container.command')

    if args.IsSpecified('container_args'):
      config.container.args = args.container_args
      update_mask.append('container.args')

    if args.IsSpecified('container_env'):
      env_val = self.messages.Container.EnvValue()
      for key, value in args.container_env.items():
        env_val.additionalProperties.append(
            self.messages.Container.EnvValue.AdditionalProperty(
                key=key, value=value
            )
        )
      config.container.env = env_val
      update_mask.append('container.env')

    if args.IsSpecified('container_working_dir'):
      config.container.workingDir = args.container_working_dir
      update_mask.append('container.working_dir')

    if args.IsSpecified('container_run_as_user'):
      config.container.runAsUser = args.container_run_as_user
      update_mask.append('container.run_as_user')

    use_disk_type = args.IsKnownAndSpecified(
        'disk_type'
    ) or args.IsKnownAndSpecified('pd_disk_type')
    use_disk_size = args.IsKnownAndSpecified(
        'disk_size'
    ) or args.IsKnownAndSpecified('pd_disk_size')
    use_source_snapshot = args.IsKnownAndSpecified(
        'disk_source_snapshot'
    ) or args.IsKnownAndSpecified('pd_source_snapshot')
    update_disk = use_disk_type or use_disk_size or use_source_snapshot
    if use_disk_type:
      disk_type: str = (
          args.disk_type
          if args.IsKnownAndSpecified('disk_type')
          else args.pd_disk_type
      )
    else:
      disk_type: str = extract_disk_type(old_config)
    if use_disk_size:
      disk_size: int = (
          args.disk_size
          if args.IsKnownAndSpecified('disk_size')
          else args.pd_disk_size
      )
    else:
      disk_size: int = extract_disk_size(old_config)
    if use_source_snapshot:
      source_snapshot: str = (
          args.disk_source_snapshot
          if args.IsKnownAndSpecified('disk_source_snapshot')
          else args.pd_source_snapshot
      )
    else:
      source_snapshot: str = extract_source_snapshot(old_config)
    if (
        old_config.persistentDirectories
        and old_config.persistentDirectories[0].gcePd
        and disk_type == 'hyperdisk-balanced-ha'
    ):
      log.err.Print("Can't update persistent directory from PD to HD")

    if (
        old_config.persistentDirectories
        and hasattr(old_config.persistentDirectories[0], 'gceHd')
        and old_config.persistentDirectories[0].gceHd
        and disk_type != 'hyperdisk-balanced-ha'
    ):
      log.err.Print("Can't update persistent directory from HD to PD")

    if update_disk:
      update_mask.append('persistent_directories')

    config.persistentDirectories = old_config.persistentDirectories
    if not old_config.persistentDirectories:
      config.persistentDirectories = [self.messages.PersistentDirectory()]

    if use_source_snapshot:
      if disk_type == 'hyperdisk-balanced-ha':
        config.persistentDirectories[0].gceHd = (
            self.messages.GceHyperdiskBalancedHighAvailability(
                sizeGb=0,
                sourceSnapshot=source_snapshot,
            )
        )
      else:
        config.persistentDirectories[0].gcePd = (
            self.messages.GceRegionalPersistentDisk(
                sizeGb=0,
                fsType='',
                sourceSnapshot=source_snapshot,
                diskType=disk_type,
            )
        )
    elif disk_type == 'hyperdisk-balanced-ha':
      config.persistentDirectories[0].gceHd = (
          self.messages.GceHyperdiskBalancedHighAvailability(
              sizeGb=disk_size,
          )
      )
    else:
      config.persistentDirectories[0].gcePd = (
          self.messages.GceRegionalPersistentDisk(
              sizeGb=disk_size, diskType=disk_type
          )
      )

    if args.IsSpecified('vm_tags'):
      tags_val = self.messages.GceInstance.VmTagsValue()
      for key, value in args.vm_tags.items():
        tags_val.additionalProperties.append(
            self.messages.GceInstance.VmTagsValue.AdditionalProperty(
                key=key, value=value
            )
        )
      config.host.gceInstance.vmTags = tags_val
      update_mask.append('host.gce_instance.vm_tags')

    if not update_mask:
      log.error('No fields were specified.')
      return

    update_req = self.messages.WorkstationsProjectsLocationsWorkstationClustersWorkstationConfigsPatchRequest(
        name=config_name,
        workstationConfig=config,
        updateMask=','.join(update_mask),
    )
    op_ref = self._service.Patch(update_req)

    log.status.Print('Update request issued for: [{}]'.format(config_id))

    if args.async_:
      log.status.Print('Check operation [{}] for status.'.format(op_ref.name))
      return op_ref

    op_resource = resources.REGISTRY.ParseRelativeName(
        op_ref.name,
        collection='workstations.projects.locations.operations',
        api_version=self.api_version,
    )
    poller = waiter.CloudOperationPoller(
        self._service, self.client.projects_locations_operations
    )

    result = waiter.WaitFor(
        poller,
        op_resource,
        'Waiting for operation [{}] to complete'.format(op_ref.name),
    )
    log.status.Print('Updated configuration [{}].'.format(config_id))
    return result


def extract_disk_type(old_config) -> str:
  if old_config.persistentDirectories and getattr(
      old_config.persistentDirectories[0], 'gceHd', False
  ):
    return 'hyperdisk-balanced-ha'
  if old_config.persistentDirectories and getattr(
      old_config.persistentDirectories[0], 'gcePd', False
  ):
    return old_config.persistentDirectories[0].gcePd.diskType
  return ''


def extract_disk_size(old_config) -> int:
  if old_config.persistentDirectories and getattr(
      old_config.persistentDirectories[0], 'gceHd', False
  ):
    return old_config.persistentDirectories[0].gceHd.sizeGb
  if old_config.persistentDirectories and getattr(
      old_config.persistentDirectories[0], 'gcePd', False
  ):
    return old_config.persistentDirectories[0].gcePd.sizeGb
  return 0


def extract_source_snapshot(old_config) -> str:
  if old_config.persistentDirectories and getattr(
      old_config.persistentDirectories[0], 'gceHd', False
  ):
    return old_config.persistentDirectories[0].gceHd.sourceSnapshot
  if old_config.persistentDirectories and getattr(
      old_config.persistentDirectories[0], 'gcePd', False
  ):
    return old_config.persistentDirectories[0].gcePd.sourceSnapshot
  return ''
