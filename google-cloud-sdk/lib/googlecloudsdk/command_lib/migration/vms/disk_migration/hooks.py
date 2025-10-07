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
"""Argument processors for migration vms disk-migrations surface arguments."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.migration.vms import hooks
from googlecloudsdk.generated_clients.apis.vmmigration.v1 import vmmigration_v1_messages


default_disk_type = (
    vmmigration_v1_messages.ComputeEngineDisk.DiskTypeValueValuesEnum.COMPUTE_ENGINE_DISK_TYPE_STANDARD
)


def GetDiskMigrationJobTargetDetails(value):
  """Returns empty DiskMigrationJobTargetDetails entry.

  Args:
    value: A pointer to the DiskMigrationJobTargetDetails field in the request.

  Returns:
    An empty DiskMigrationJobTargetDetails entry.
  """
  del value
  return hooks.GetMessageClass(
      'DiskMigrationJobTargetDetails'
  )()


def GetComputeEngineDiskTransform(value):
  """Returns empty ComputeEngineDisk entry.

  Args:
    value: A pointer to the ComputeEngineDisk field in the request.

  Returns:
    An empty ComputeEngineDisk entry.
  """
  del value
  return hooks.GetMessageClass('ComputeEngineDisk')()


def GetDefaultZone(ref):
  """Returns the default zone for the given resource reference.

  Args:
    ref: The resource reference.

  Returns:
    The default zone for the given resource reference.
  """
  return ExtractLocation(ref) + '-a'


def ExtractLocation(ref):
  """Extracts the location from the resource reference.

  Args:
    ref: The resource reference.

  Returns:
    The location of the resource reference.
  """
  return ref.Parent().Parent().Name()


def GetProject(ref):
  """Returns the project name for the given resource reference.

  Args:
    ref: The resource reference.

  Returns:
    The project name for the given resource reference.
  """
  return ref.Parent().Parent().Parent()


# Modify Request Hook For Disk Migration
def FixCreateDiskMigrationsRequest(ref, args, req):
  """Fixes the Create Disk Migration request.

  Args:
    ref: The resource reference.
    args: The parsed arguments.
    req: The request message.

  Returns:
    The modified request message.
  """
  if getattr(req.diskMigrationJob, 'targetDetails', None) is None:
    req.diskMigrationJob.targetDetails = (
        GetDiskMigrationJobTargetDetails(
            req.diskMigrationJob.targetDetails
        )
    )

  if getattr(req.diskMigrationJob.targetDetails, 'targetDisk', None) is None:
    req.diskMigrationJob.targetDetails.targetDisk = (
        GetComputeEngineDiskTransform(
            req.diskMigrationJob.targetDetails.targetDisk,
        )
    )

  if not args.disk_id:
    req.diskMigrationJob.targetDetails.targetDisk.diskId = ref.Name()

  if not args.zone:
    req.diskMigrationJob.targetDetails.targetDisk.zone = GetDefaultZone(ref)

  if not args.disk_type:
    req.diskMigrationJob.targetDetails.targetDisk.diskType = default_disk_type

  hooks.FixTargetDetailsCommonFields(
      GetProject(ref), args, req.diskMigrationJob.targetDetails
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
