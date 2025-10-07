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
"""Argument processors for disk/machine image import surface arguments."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.migration.vms import hooks


# Argument Processors
def GetDataDiskImageImportTransform(value):
  """Returns empty DataDiskImageImport entry.

  Args:
    value: A pointer to the DataDiskImageImport field in the request.

  Returns:
    An empty DataDiskImageImport message.
  """
  del value
  return hooks.GetMessageClass('DataDiskImageImport')()


# Argument Processors
def GetSkipOsAdaptationTransform(value):
  """Returns empty SkipOsAdaptationTransform entry.

  Args:
    value: A pointer to the SkipOsAdaptation field in the request.

  Returns:
    An empty SkipOsAdaptation message.
  """
  del value
  return hooks.GetMessageClass('SkipOsAdaptation')()


def GetEncryptionTransform(value):
  """Returns empty Encryption entry.

  Args:
    value: A pointer to the Encryption field in the request.

  Returns:
    An empty Encryption message.
  """
  del value
  return hooks.GetMessageClass('Encryption')()


def GetProject(ref):
  """Returns the project name for the given resource reference.

  Args:
    ref: The resource reference.
  Returns:
    The project name for the given resource reference.
  """
  return ref.Parent().Parent()


# Modify Request Hook For Disk Image Import
def FixCreateDiskImageImportRequest(ref, args, req):
  """Fixes the Create Image Import request for disk image import.

  Args:
    ref: The resource reference.
    args: The parsed arguments.
    req: The request message.

  Returns:
    The modified request message.
  """
  if not (
      args.generalize
      or args.license_type
      or args.boot_conversion
      or args.adaptation_modifiers
      or args.rootfs_uuid
  ):
    req.imageImport.diskImageTargetDefaults.osAdaptationParameters = None

  if not args.image_name:
    req.imageImport.diskImageTargetDefaults.imageName = ref.Name()

  if args.kms_key:
    req.imageImport.diskImageTargetDefaults.encryption = (
        GetEncryptionTransform(
            req.imageImport.diskImageTargetDefaults.encryption
        )
    )
    req.imageImport.diskImageTargetDefaults.encryption.kmsKey = args.kms_key

    req.imageImport.encryption = (
        GetEncryptionTransform(req.imageImport.encryption)
        )
    req.imageImport.encryption.kmsKey = args.kms_key
  adaptation_modifiers = []
  if args.adaptation_modifiers:
    if not req.imageImport.diskImageTargetDefaults.osAdaptationParameters:
      req.imageImport.diskImageTargetDefaults.osAdaptationParameters = (
          hooks.GetMessageClass('ImageImportOsAdaptationParameters')()
      )
    adaptation_modifiers = ProcessAdaptationModifiers(args.adaptation_modifiers)
    req.imageImport.diskImageTargetDefaults.osAdaptationParameters.adaptationModifiers = ProcessAdaptationModifiers(
        args.adaptation_modifiers
    )
  if args.rootfs_uuid:
    adaptation_modifiers.append(
        hooks.GetMessageClass('AdaptationModifier')(
            modifier='rootfs-uuid', value=args.rootfs_uuid
        )
    )
  if adaptation_modifiers:
    req.imageImport.diskImageTargetDefaults.osAdaptationParameters.adaptationModifiers = (
        adaptation_modifiers
    )
  hooks.FixTargetDetailsCommonFields(
      GetProject(ref), args, req.imageImport.diskImageTargetDefaults
  )

  return req


# Modify Request Hook For Machine Image Import
def FixCreateMachineImageImportRequest(ref, args, req):
  """Fixes the Create Image Import request machine image import.

  Args:
    ref: The resource reference.
    args: The parsed arguments.
    req: The request message.

  Returns:
    The modified request message.
  """

  if not args.machine_image_name:
    req.imageImport.machineImageTargetDefaults.machineImageName = ref.Name()

  if (
      not args.generalize
      and not args.license_type
      and not args.boot_conversion
      and not args.adaptation_modifiers
      and not args.rootfs_uuid
  ):
    req.imageImport.machineImageTargetDefaults.osAdaptationParameters = None

  if (
      not args.secure_boot
      and not args.enable_vtpm
      and not args.enable_integrity_monitoring
  ):
    req.imageImport.machineImageTargetDefaults.shieldedInstanceConfig = None

  if args.kms_key:
    req.imageImport.machineImageTargetDefaults.encryption = (
        GetEncryptionTransform(
            req.imageImport.machineImageTargetDefaults.encryption
        )
    )
    req.imageImport.machineImageTargetDefaults.encryption.kmsKey = args.kms_key

    req.imageImport.encryption = (
        GetEncryptionTransform(req.imageImport.encryption)
        )
    req.imageImport.encryption.kmsKey = args.kms_key
  adaptation_modifiers = []
  if args.adaptation_modifiers:
    if not req.imageImport.machineImageTargetDefaults.osAdaptationParameters:
      req.imageImport.machineImageTargetDefaults.osAdaptationParameters = (
          hooks.GetMessageClass('ImageImportOsAdaptationParameters')()
      )
    adaptation_modifiers = ProcessAdaptationModifiers(args.adaptation_modifiers)
  if args.rootfs_uuid:
    adaptation_modifiers.append(
        hooks.GetMessageClass('AdaptationModifier')(
            modifier='rootfs-uuid', value=args.rootfs_uuid
        )
    )
  if adaptation_modifiers:
    req.imageImport.machineImageTargetDefaults.osAdaptationParameters.adaptationModifiers = (
        adaptation_modifiers
    )
  hooks.FixTargetDetailsCommonFields(
      GetProject(ref), args, req.imageImport.machineImageTargetDefaults
  )

  return req


# convert the gcloud flags to the api format#
# i.e. --adaptation-modifiers=flag1,flag2=value2
# will be converted to:
# [AdaptationModifier{'modifier': 'flag1'},
# AdaptationModifier{'modifier': 'flag2', 'value': 'value2'}]
def ProcessAdaptationModifiers(adaptation_modifiers):
  """Processes the adaptation modifiers to match the API format.

  Args:
    adaptation_modifiers: A string or a list of strings representing the
      adaptation flags.

  Returns:
    A list of dictionaries, where each dictionary represents a key-value
    pair with 'key' and 'value' fields.
  """
  if not adaptation_modifiers:
    return []

  if isinstance(adaptation_modifiers, str):
    flags_list = adaptation_modifiers.split(',')
  elif isinstance(adaptation_modifiers, list):
    flags_list = adaptation_modifiers
  else:
    raise arg_parsers.ArgumentTypeError(
        'adaptation-modifiers must be a string or a list of strings.'
    )
  result = []
  for flag in flags_list:
    if not flag:
      continue
    if '=' not in flag:
      adaptation_flag_message = hooks.GetMessageClass('AdaptationModifier')(
          modifier=flag.strip()
      )
    else:
      key, value = flag.split('=', 1)
      adaptation_flag_message = hooks.GetMessageClass('AdaptationModifier')(
          modifier=key.strip(), value=value.strip()
      )
    result.append(adaptation_flag_message)
  return result
