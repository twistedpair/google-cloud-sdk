# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""workbench instances api helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum

from googlecloudsdk.api_lib.workbench import util
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.workbench import flags
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources


_RESERVATION_AFFINITY_KEY = 'compute.googleapis.com/reservation-name'


def GetNetworkRelativeName(args):
  if args.IsSpecified('network'):
    return args.CONCEPTS.network.Parse().RelativeName()


def GetSubnetRelativeName(args):
  if args.IsSpecified('subnet'):
    try:
      return args.CONCEPTS.subnet.Parse().RelativeName()
    except AttributeError:
      raise exceptions.Error(
          'Subnet is not formatted correctly. Expected format:'
          ' projects/{project-id}/regions/{region}/subnetworks/{subnet-name}'
      )


def CreateNetworkConfigMessage(args, messages):
  """Creates the network config for the instance.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    A list of NetworkInterface messages for the instance.
  """
  if not (
      args.IsSpecified('network')
      or args.IsSpecified('subnet')
      or args.IsSpecified('nic_type')
  ):
    return []

  network_name = None
  subnet_name = None
  nic_type = None
  if args.IsSpecified('network'):
    network_name = GetNetworkRelativeName(args)
  if args.IsSpecified('subnet'):
    subnet_name = GetSubnetRelativeName(args)
  if args.IsSpecified('nic_type'):
    nic_type = arg_utils.ChoiceEnumMapper(
        arg_name='nic-type',
        message_enum=messages.NetworkInterface.NicTypeValueValuesEnum,
        include_filter=lambda x: 'UNSPECIFIED' not in x,
    ).GetEnumForChoice(arg_utils.EnumNameToChoice(args.nic_type))
  return [messages.NetworkInterface(
      network=network_name,
      subnet=subnet_name,
      nicType=nic_type,
  )]


def CreateAcceleratorConfigMessage(args, messages):
  """Creates the accelerator config for the instance.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    A list of AcceleratorConfig messages for the instance.
  """
  if not (
      args.IsSpecified('accelerator_type')
      or args.IsSpecified('accelerator_core_count')
  ):
    return []

  type_enum = None
  if args.IsSpecified('accelerator_type'):
    type_enum = arg_utils.ChoiceEnumMapper(
        arg_name='accelerator-type',
        message_enum=messages.AcceleratorConfig.TypeValueValuesEnum,
        include_filter=lambda x: 'UNSPECIFIED' not in x,
    ).GetEnumForChoice(arg_utils.EnumNameToChoice(args.accelerator_type))
  return [messages.AcceleratorConfig(
      type=type_enum, coreCount=args.accelerator_core_count
  )]


def CreateServiceAccountConfigMessage(args, messages):
  if not args.IsSpecified('service_account_email'):
    return []

  return [messages.ServiceAccount(email=args.service_account_email)]


def CreateGPUDriverConfigMessage(args, messages):
  if not (
      args.IsSpecified('custom_gpu_driver_path')
      or args.IsSpecified('install_gpu_driver')
  ):
    return None

  return messages.GPUDriverConfig(
      customGpuDriverPath=args.custom_gpu_driver_path,
      enableGpuDriver=args.install_gpu_driver,
  )


def CreateReservationConfigMessage(args, messages):
  """Creates the reservation config for the instance.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Reservation config for the instance.
  """
  if not (
      args.IsSpecified('reservation_type')
      or args.IsSpecified('reservation_key')
      or args.IsSpecified('reservation_values')
  ):
    return None

  reservation_type_enum = None
  if args.IsSpecified('reservation_type'):
    reservation_type_enum = flags.GetReservationTypeMapper(
        messages
    ).GetEnumForChoice(args.reservation_type)
  reservation_values = []
  if args.IsSpecified('reservation_values'):
    reservation_values = args.reservation_values
  return messages.ReservationAffinity(
      consumeReservationType=reservation_type_enum,
      key=args.reservation_key,
      values=reservation_values,
  )


def GetBootDisk(args, messages):
  """Creates the boot disk config for the instance.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Boot disk config for the instance.
  """
  if not (
      args.IsSpecified('boot_disk_size')
      or args.IsSpecified('boot_disk_type')
      or args.IsSpecified('boot_disk_encryption')
      or args.IsSpecified('boot_disk_kms_key')
  ):
    return None

  boot_disk_message = messages.BootDisk
  boot_disk_encryption_enum = None
  boot_disk_type_enum = None
  kms_key = None
  if args.IsSpecified('boot_disk_type'):
    boot_disk_type_enum = arg_utils.ChoiceEnumMapper(
        arg_name='boot-disk-type',
        message_enum=boot_disk_message.DiskTypeValueValuesEnum,
        include_filter=lambda x: 'UNSPECIFIED' not in x,
    ).GetEnumForChoice(arg_utils.EnumNameToChoice(args.boot_disk_type))
  if args.IsSpecified('boot_disk_encryption'):
    boot_disk_encryption_enum = arg_utils.ChoiceEnumMapper(
        arg_name='boot-disk-encryption',
        message_enum=boot_disk_message.DiskEncryptionValueValuesEnum,
        include_filter=lambda x: 'UNSPECIFIED' not in x,
    ).GetEnumForChoice(arg_utils.EnumNameToChoice(args.boot_disk_encryption))
  if args.IsSpecified('boot_disk_kms_key'):
    kms_key = args.CONCEPTS.boot_disk_kms_key.Parse().RelativeName()
  return boot_disk_message(
      diskType=boot_disk_type_enum,
      diskEncryption=boot_disk_encryption_enum,
      diskSizeGb=args.boot_disk_size,
      kmsKey=kms_key,
  )


def GetDataDisk(args, messages):
  """Creates the data disk config for the instance.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Data disk config for the instance.
  """
  if not (
      args.IsSpecified('data_disk_size')
      or args.IsSpecified('data_disk_type')
      or args.IsSpecified('data_disk_encryption')
      or args.IsSpecified('data_disk_kms_key')
      or args.IsSpecified('data_disk_resource_policies')
  ):
    return []

  data_disk_message = messages.DataDisk
  data_disk_encryption_enum = None
  data_disk_type_enum = None
  kms_key = None
  resource_policies = []
  if args.IsSpecified('data_disk_type'):
    data_disk_type_enum = arg_utils.ChoiceEnumMapper(
        arg_name='data-disk-type',
        message_enum=data_disk_message.DiskTypeValueValuesEnum,
        include_filter=lambda x: 'UNSPECIFIED' not in x,
    ).GetEnumForChoice(arg_utils.EnumNameToChoice(args.data_disk_type))
  if args.IsSpecified('data_disk_encryption'):
    data_disk_encryption_enum = arg_utils.ChoiceEnumMapper(
        arg_name='data-disk-encryption',
        message_enum=data_disk_message.DiskEncryptionValueValuesEnum,
        include_filter=lambda x: 'UNSPECIFIED' not in x,
    ).GetEnumForChoice(arg_utils.EnumNameToChoice(args.data_disk_encryption))
  if args.IsSpecified('data_disk_kms_key'):
    kms_key = args.CONCEPTS.data_disk_kms_key.Parse().RelativeName()
  if args.IsSpecified('data_disk_resource_policies'):
    resource_policies = args.data_disk_resource_policies
  return [
      data_disk_message(
          diskType=data_disk_type_enum,
          diskEncryption=data_disk_encryption_enum,
          diskSizeGb=args.data_disk_size,
          kmsKey=kms_key,
          resourcePolicies=resource_policies,
      )
  ]


def CreateContainerImageFromArgs(args, messages):
  if not (
      args.IsSpecified('container_repository')
      or args.IsSpecified('container_tag')
  ):
    return None

  container_image = messages.ContainerImage(
      repository=args.container_repository, tag=args.container_tag
  )
  return container_image


def CreateVmImageFromArgs(args, messages):
  """Create VmImage Message from an environment or from args."""
  if not (
      args.IsSpecified('vm_image_project')
      or args.IsSpecified('vm_image_family')
      or args.IsSpecified('vm_image_name')
  ):
    return None

  vm_image = messages.VmImage()
  vm_image.project = args.vm_image_project
  if args.IsSpecified('vm_image_family'):
    vm_image.family = args.vm_image_family
  else:
    vm_image.name = args.vm_image_name
  return vm_image


def GetInstanceOwnersFromArgs(args):
  if not args.IsSpecified('instance_owners'):
    return []

  return [args.instance_owners]


def GetLabelsFromArgs(args, messages):
  if not args.IsSpecified('labels'):
    return None

  labels_message = messages.Instance.LabelsValue
  return labels_message(additionalProperties=[
      labels_message.AdditionalProperty(key=key, value=value)
      for key, value in args.labels.items()
  ])


def GetTagsFromArgs(args):
  if not args.IsSpecified('tags'):
    return []

  return args.tags


def GetMetadataFromArgs(args, messages):
  if not args.IsSpecified('metadata'):
    return None

  metadata_message = messages.GceSetup.MetadataValue
  return metadata_message(
      additionalProperties=[
          metadata_message.AdditionalProperty(key=key, value=value)
          for key, value in args.metadata.items()
      ]
  )


def GetShieldedInstanceConfigFromArgs(args, messages):
  """Creates the Shielded Instance Config message for the create/update request.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Shielded Instance Config of the Instance message.
  """
  if not (
      args.IsSpecified('shielded_secure_boot')
      or args.IsSpecified('shielded_vtpm')
      or args.IsSpecified('shielded_integrity_monitoring')
  ):
    return None

  true_values = ['1', 'true', 'on', 'yes', 'y']
  if args.IsSpecified('shielded_secure_boot'):
    shielded_secure_boot = args.shielded_secure_boot.lower() in true_values
  else:
    shielded_secure_boot = None
  if args.IsSpecified('shielded_vtpm'):
    shielded_vtpm = args.shielded_vtpm.lower() in true_values
  else:
    shielded_vtpm = None
  if args.IsSpecified('shielded_integrity_monitoring'):
    shielded_integrity_monitoring = (
        args.shielded_integrity_monitoring.lower() in true_values
    )
  else:
    shielded_integrity_monitoring = None
  shielded_instance_config_message = messages.ShieldedInstanceConfig
  return shielded_instance_config_message(
      enableIntegrityMonitoring=shielded_integrity_monitoring,
      enableSecureBoot=shielded_secure_boot,
      enableVtpm=shielded_vtpm,
  )


def GetConfidentialInstanceConfigFromArgs(args, messages):
  """Creates the Confidential Instance Config message for the create request.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Confidential Instance Config of the Instance message.
  """
  if not args.IsSpecified('confidential_compute_type'):
    return None

  confidential_instance_type = arg_utils.ChoiceEnumMapper(
      arg_name='confidential-compute-type',
      message_enum=messages.ConfidentialInstanceConfig.ConfidentialInstanceTypeValueValuesEnum,
      include_filter=lambda x: 'UNSPECIFIED' not in x,
  ).GetEnumForChoice(
      arg_utils.EnumNameToChoice(args.confidential_compute_type)
  )

  return messages.ConfidentialInstanceConfig(
      confidentialInstanceType=confidential_instance_type,
  )


def GetMachineTypeFromArgs(args):
  if not args.IsSpecified('machine_type'):
    return None
  return args.machine_type


def GetMinCpuPlatformFromArgs(args):
  if not args.IsSpecified('min_cpu_platform'):
    return None
  return args.min_cpu_platform


def GetDisablePublicIpFromArgs(args):
  if not args.IsSpecified('disable_public_ip'):
    return None
  return args.disable_public_ip


def GetEnableIpForwardingFromArgs(args):
  if not args.IsSpecified('enable_ip_forwarding'):
    return None
  return args.enable_ip_forwarding


def GetEnableThirdPartyIdentityFromArgs(args):
  if not args.IsSpecified('enable_third_party_identity'):
    return None
  return args.enable_third_party_identity


def GetEnableManagedEucFromArgs(args):
  if not args.IsSpecified('enable_managed_euc'):
    return None
  return args.enable_managed_euc


def GetDisableProxyAccessFromArgs(args):
  if not args.IsSpecified('disable_proxy_access'):
    return None
  return args.disable_proxy_access


def CreateInstance(args, messages):
  """Creates the Instance message for the create request.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the Instance message.
  """

  gce_setup = messages.GceSetup(
      acceleratorConfigs=CreateAcceleratorConfigMessage(args, messages),
      bootDisk=GetBootDisk(args, messages),
      containerImage=CreateContainerImageFromArgs(args, messages),
      dataDisks=GetDataDisk(args, messages),
      disablePublicIp=GetDisablePublicIpFromArgs(args),
      enableIpForwarding=GetEnableIpForwardingFromArgs(args),
      gpuDriverConfig=CreateGPUDriverConfigMessage(args, messages),
      machineType=GetMachineTypeFromArgs(args),
      minCpuPlatform=GetMinCpuPlatformFromArgs(args),
      metadata=GetMetadataFromArgs(args, messages),
      networkInterfaces=CreateNetworkConfigMessage(args, messages),
      reservationAffinity=CreateReservationConfigMessage(args, messages),
      serviceAccounts=CreateServiceAccountConfigMessage(args, messages),
      shieldedInstanceConfig=GetShieldedInstanceConfigFromArgs(args, messages),
      confidentialInstanceConfig=GetConfidentialInstanceConfigFromArgs(
          args, messages
      ),
      tags=GetTagsFromArgs(args),
      vmImage=CreateVmImageFromArgs(args, messages),
  )
  instance = messages.Instance(
      name=args.instance,
      disableProxyAccess=GetDisableProxyAccessFromArgs(args),
      gceSetup=gce_setup if gce_setup != messages.GceSetup() else None,
      instanceOwners=GetInstanceOwnersFromArgs(args),
      labels=GetLabelsFromArgs(args, messages),
      enableThirdPartyIdentity=GetEnableThirdPartyIdentityFromArgs(args),
      enableManagedEuc=GetEnableManagedEucFromArgs(args)
  )
  return instance


def CreateInstanceCreateRequest(args, messages):
  """Creates the update mask for update Instance request.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the API.

  Returns:
    Update mask of the Instance message.
  """
  parent = util.GetParentForInstance(args)
  instance = CreateInstance(args, messages)
  return messages.NotebooksProjectsLocationsInstancesCreateRequest(
      parent=parent, instance=instance, instanceId=args.instance)


def CreateUpdateMask(args):
  """Creates the update mask for update Instance request.

  Args:
    args: Argparse object from Command.Run

  Returns:
    Update mask of the Instance message.
  """
  mask_array = []
  field_mask_dict = {
      'accelerator_type': 'gce_setup.accelerator_configs.type',
      'accelerator_core_count': 'gce_setup.accelerator_configs.core_count',
      'install_gpu_driver': 'gce_setup.gpu_driver_config.enable_gpu_driver',
      'custom_gpu_driver_path': (
          'gce_setup.gpu_driver_config.custom_gpu_driver_path'
      ),
      'shielded_secure_boot': (
          'gce_setup.shielded_instance_config.enable_secure_boot'
      ),
      'shielded_vtpm': 'gce_setup.shielded_instance_config.enable_vtpm',
      'shielded_integrity_monitoring': (
          'gce_setup.shielded_instance_config.enable_integrity_monitoring'
      ),
      'labels': 'labels',
      'metadata': 'gce_setup.metadata',
      'machine_type': 'gce_setup.machine_type',
      'tags': 'gce_setup.tags',
      'container_repository': 'gce_setup.container_image.repository',
      'container_tag': 'gce_setup.container_image.tag',
  }
  for key, value in sorted(field_mask_dict.items()):
    if args.IsSpecified(key):
      mask_array.append(value)
  return ','.join(map(str, mask_array))


def GetInstanceResource(args):
  return args.CONCEPTS.instance.Parse()


def CreateInstanceListRequest(args, messages):
  parent = util.GetParentFromArgs(args)
  return messages.NotebooksProjectsLocationsInstancesListRequest(parent=parent)


def CreateInstanceDeleteRequest(args, messages):
  instance = GetInstanceResource(args).RelativeName()
  return messages.NotebooksProjectsLocationsInstancesDeleteRequest(
      name=instance)


def CreateInstanceDescribeRequest(args, messages):
  instance = GetInstanceResource(args).RelativeName()
  return messages.NotebooksProjectsLocationsInstancesGetRequest(name=instance)


def CreateInstanceResetRequest(args, messages):
  instance = GetInstanceResource(args).RelativeName()
  reset_request = messages.ResetInstanceRequest()
  return messages.NotebooksProjectsLocationsInstancesResetRequest(
      name=instance, resetInstanceRequest=reset_request)


def CreateInstanceRollbackRequest(args, messages):
  instance = GetInstanceResource(args).RelativeName()
  rollback_request = messages.RollbackInstanceRequest(
      targetSnapshot=args.target_snapshot)
  return messages.NotebooksProjectsLocationsInstancesRollbackRequest(
      name=instance, rollbackInstanceRequest=rollback_request)


def CreateInstanceStartRequest(args, messages):
  instance = GetInstanceResource(args).RelativeName()
  start_request = messages.StartInstanceRequest()
  return messages.NotebooksProjectsLocationsInstancesStartRequest(
      name=instance, startInstanceRequest=start_request)


def CreateInstanceStopRequest(args, messages):
  instance = GetInstanceResource(args).RelativeName()
  stop_request = messages.StopInstanceRequest()
  return messages.NotebooksProjectsLocationsInstancesStopRequest(
      name=instance, stopInstanceRequest=stop_request)


def CreateGetConfigRequest(args, messages):
  name = util.GetParentFromArgs(args)
  return messages.NotebooksProjectsLocationsInstancesGetConfigRequest(name=name)


def CreateInstanceRestoreRequest(args, messages):
  instance = GetInstanceResource(args).RelativeName()
  restore_request = messages.RestoreInstanceRequest(
      snapshot=messages.Snapshot(
          projectId=args.snapshot_project, snapshotId=args.snapshot
      )
  )
  return messages.NotebooksProjectsLocationsInstancesRestoreRequest(
      name=instance, restoreInstanceRequest=restore_request
  )


def UpdateInstance(args, messages):
  """Creates the Instance message for the update request.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the Instance message.
  """
  gce_setup = messages.GceSetup(
      acceleratorConfigs=CreateAcceleratorConfigMessage(args, messages),
      gpuDriverConfig=CreateGPUDriverConfigMessage(args, messages),
      machineType=GetMachineTypeFromArgs(args),
      metadata=GetMetadataFromArgs(args, messages),
      shieldedInstanceConfig=GetShieldedInstanceConfigFromArgs(args, messages),
      tags=GetTagsFromArgs(args),
      containerImage=CreateContainerImageFromArgs(args, messages),
  )

  instance = messages.Instance(
      name=args.instance,
      gceSetup=gce_setup if gce_setup != messages.GceSetup() else None,
      labels=GetLabelsFromArgs(args, messages),
  )
  return instance


def CreateInstanceUpdateRequest(args, messages):
  instance = UpdateInstance(args, messages)
  name = GetInstanceResource(args).RelativeName()
  update_mask = CreateUpdateMask(args)
  return messages.NotebooksProjectsLocationsInstancesPatchRequest(
      instance=instance,
      name=name,
      updateMask=update_mask)


def CreateInstanceDiagnoseRequest(args, messages):
  """"Create and return Diagnose request."""
  instance = GetInstanceResource(args).RelativeName()
  diagnostic_config = messages.DiagnosticConfig(
      gcsBucket=args.gcs_bucket,
  )
  if args.IsSpecified('relative_path'):
    diagnostic_config.relativePath = args.relative_path
  if args.IsSpecified('enable_repair'):
    diagnostic_config.enableRepairFlag = True
  if args.IsSpecified('enable_packet_capture'):
    diagnostic_config.enablePacketCaptureFlag = True
  if args.IsSpecified('enable_copy_home_files'):
    diagnostic_config.enableCopyHomeFilesFlag = True
  return messages.NotebooksProjectsLocationsInstancesDiagnoseRequest(
      name=instance, diagnoseInstanceRequest=messages.DiagnoseInstanceRequest(
          diagnosticConfig=diagnostic_config))


def CreateInstanceResizeDisk(args, messages):
  """Create and return ResizeDisk request."""
  instance = GetInstanceResource(args).RelativeName()
  request = None
  if args.IsSpecified('boot_disk_size'):
    request = messages.ResizeDiskRequest(
        bootDisk=messages.BootDisk(
            diskSizeGb=args.boot_disk_size,
        )
    )
  elif args.IsSpecified('data_disk_size'):
    request = messages.ResizeDiskRequest(
        dataDisk=messages.DataDisk(
            diskSizeGb=args.data_disk_size,
        )
    )
  return messages.NotebooksProjectsLocationsInstancesResizeDiskRequest(
      notebookInstance=instance, resizeDiskRequest=request)


def CreateInstanceUpgradeRequest(args, messages):
  instance = GetInstanceResource(args).RelativeName()
  upgrade_request = messages.UpgradeInstanceRequest()
  return messages.NotebooksProjectsLocationsInstancesUpgradeRequest(
      name=instance, upgradeInstanceRequest=upgrade_request)


def CreateInstanceCheckUpgradabilityRequest(args, messages):
  instance = GetInstanceResource(args).RelativeName()
  return messages.NotebooksProjectsLocationsInstancesCheckUpgradabilityRequest(
      notebookInstance=instance)


def GetInstanceURI(resource):
  instance = resources.REGISTRY.ParseRelativeName(
      resource.name, collection='notebooks.projects.locations.instances')
  return instance.SelfLink()


class OperationType(enum.Enum):
  CREATE = (log.CreatedResource, 'created')
  UPDATE = (log.UpdatedResource, 'updated')
  RESTORE = (log.RestoredResource, 'restored')
  UPGRADE = (log.UpdatedResource, 'upgraded')
  ROLLBACK = (log.UpdatedResource, 'rolled back')
  DELETE = (log.DeletedResource, 'deleted')
  RESET = (log.ResetResource, 'reset')


def HandleLRO(operation,
              args,
              instance_service,
              release_track,
              operation_type=OperationType.UPDATE):
  """Handles Long-running Operations for both cases of async.

  Args:
    operation: The operation to poll.
    args: ArgParse instance containing user entered arguments.
    instance_service: The service to get the resource after the long-running
      operation completes.
    release_track: base.ReleaseTrack object.
    operation_type: Enum value of type OperationType indicating the kind of
      operation to wait for.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error

  Returns:
    The Instance resource if synchronous, else the Operation Resource.
  """
  logging_method = operation_type.value[0]
  if args.async_:
    logging_method(
        util.GetOperationResource(operation.name, release_track),
        kind='workbench instance {0}'.format(args.instance),
        is_async=True)
    return operation
  else:
    response = util.WaitForOperation(
        operation,
        'Waiting for operation on Instance [{}] to be {} with [{}]'.format(
            args.instance, operation_type.value[1], operation.name),
        service=instance_service,
        release_track=release_track,
        is_delete=(operation_type.value[1] == 'deleted'))
    logging_method(
        util.GetOperationResource(operation.name, release_track),
        kind='workbench instance {0}'.format(args.instance),
        is_async=False)
    return response
