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
  return hooks.GetMessageClass(
      'DataDiskImageImport'
  )()


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
  if not (args.generalize or args.license_type or args.boot_conversion):
    req.imageImport.diskImageTargetDefaults.osAdaptationParameters = None

  if not args.image_name:
    req.imageImport.diskImageTargetDefaults.imageName = ref.Name()

  if args.kms_key:
    req.imageImport.diskImageTargetDefaults.encryption = (
        hooks.GetEncryptionTransform(
            req.imageImport.diskImageTargetDefaults.encryption
            )
        )
    req.imageImport.diskImageTargetDefaults.encryption.kmsKey = args.kms_key

    req.imageImport.encryption = (
        hooks.GetEncryptionTransform(req.imageImport.encryption)
        )
    req.imageImport.encryption.kmsKey = args.kms_key

  hooks.FixTargetDetailsCommonFields(
      ref, args, req.imageImport.diskImageTargetDefaults
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

  if not args.generalize and not args.license_type and not args.boot_conversion:
    req.imageImport.machineImageTargetDefaults.osAdaptationParameters = None

  if (
      not args.secure_boot
      and not args.enable_vtpm
      and not args.enable_integrity_monitoring
  ):
    req.imageImport.machineImageTargetDefaults.shieldedInstanceConfig = None

  if args.kms_key:
    req.imageImport.machineImageTargetDefaults.encryption = (
        hooks.GetEncryptionTransform(
            req.imageImport.machineImageTargetDefaults.encryption
            )
        )
    req.imageImport.machineImageTargetDefaults.encryption.kmsKey = args.kms_key

    req.imageImport.encryption = (
        hooks.GetEncryptionTransform(req.imageImport.encryption)
        )
    req.imageImport.encryption.kmsKey = args.kms_key

  hooks.FixTargetDetailsCommonFields(
      ref, args, req.imageImport.machineImageTargetDefaults
  )

  return req
