# -*- coding: utf-8 -*- #
# Copyright 2016 Google LLC. All Rights Reserved.
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
"""Spanner instance API helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import re

from apitools.base.py import list_pager
from cloudsdk.google.protobuf import timestamp_pb2
from googlecloudsdk.api_lib.spanner import response_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io


# The list of pre-defined IAM roles in Spanner.
KNOWN_ROLES = [
    'roles/spanner.admin', 'roles/spanner.databaseAdmin',
    'roles/spanner.databaseReader', 'roles/spanner.databaseUser',
    'roles/spanner.viewer'
]

# Timeout to use in ListInstances for unreachable instances.
UNREACHABLE_INSTANCE_TIMEOUT = datetime.timedelta(seconds=20)

_SPANNER_API_NAME = 'spanner'
_SPANNER_API_VERSION = 'v1'

_FIELD_MASK_AUTOSCALING_CONFIG = 'autoscalingConfig'


def MaybeGetAutoscalingOverride(msgs, asymmetric_autoscaling_option):
  """Returns AutoscalingConfigOverrides object if any override is found in the parsed command-line flag key-value pairs, otherwise returns None."""
  if (
      'min_nodes' not in asymmetric_autoscaling_option
      and 'max_nodes' not in asymmetric_autoscaling_option
      and 'min_processing_units' not in asymmetric_autoscaling_option
      and 'max_processing_units' not in asymmetric_autoscaling_option
      and 'high_priority_cpu_target' not in asymmetric_autoscaling_option
  ):
    return None

  obj = msgs.AutoscalingConfigOverrides(
      autoscalingLimits=msgs.AutoscalingLimits()
  )
  if 'min_nodes' in asymmetric_autoscaling_option:
    obj.autoscalingLimits.minNodes = asymmetric_autoscaling_option['min_nodes']
  if 'max_nodes' in asymmetric_autoscaling_option:
    obj.autoscalingLimits.maxNodes = asymmetric_autoscaling_option['max_nodes']
  if 'min_processing_units' in asymmetric_autoscaling_option:
    obj.autoscalingLimits.minProcessingUnits = asymmetric_autoscaling_option[
        'min_processing_units'
    ]
  if 'max_processing_units' in asymmetric_autoscaling_option:
    obj.autoscalingLimits.maxProcessingUnits = asymmetric_autoscaling_option[
        'max_processing_units'
    ]
  if 'high_priority_cpu_target' in asymmetric_autoscaling_option:
    obj.autoscalingTargetHighPriorityCpuUtilizationPercent = (
        asymmetric_autoscaling_option['high_priority_cpu_target']
    )
  return obj


# Merges existing_overrides with new_overrides and returned the merged result.
def MergeAutoscalingConfigOverride(msgs, existing_overrides, new_overrides):
  if existing_overrides is None and new_overrides is None:
    return None

  if existing_overrides is None:
    return new_overrides

  if new_overrides is None:
    return existing_overrides

  # First, copy the existing values.
  result = existing_overrides
  # Next, assign any new limits overrides if any.
  if new_overrides.autoscalingLimits is not None:
    # Make sure autoscalingLimits is not None in the result.
    if result.autoscalingLimits is None:
      result.autoscalingLimits = msgs.AutoscalingLimits()
    if new_overrides.autoscalingLimits.minNodes is not None:
      result.autoscalingLimits.minNodes = (
          new_overrides.autoscalingLimits.minNodes
      )
    if new_overrides.autoscalingLimits.maxNodes is not None:
      result.autoscalingLimits.maxNodes = (
          new_overrides.autoscalingLimits.maxNodes
      )
    if new_overrides.autoscalingLimits.minProcessingUnits is not None:
      result.autoscalingLimits.minProcessingUnits = (
          new_overrides.autoscalingLimits.minProcessingUnits
      )
    if new_overrides.autoscalingLimits.maxProcessingUnits is not None:
      result.autoscalingLimits.maxProcessingUnits = (
          new_overrides.autoscalingLimits.maxProcessingUnits
      )

  # Finally, assign any target overrides if any.
  if (
      new_overrides.autoscalingTargetHighPriorityCpuUtilizationPercent
      is not None
  ):
    result.autoscalingTargetHighPriorityCpuUtilizationPercent = (
        new_overrides.autoscalingTargetHighPriorityCpuUtilizationPercent
    )

  return result


# Set instance_obj.autoscalingConfig.asymmetricAutoscalingOptions by merging
# options found in the current_instance and patch requested, asym_option_patch.
def PatchAsymmetricAutoscalingOptions(
    msgs, instance_obj, current_instance, asym_options_patch
):
  option_by_location = {}
  if config := current_instance.autoscalingConfig:
    for existing_option in config.asymmetricAutoscalingOptions:
      option_by_location[existing_option.replicaSelection.location] = (
          existing_option
      )

  for patch_option in asym_options_patch:
    location = patch_option.replicaSelection.location
    if location in option_by_location:
      # Update existing option
      existing_option = option_by_location[location]
      option_by_location[location].overrides = MergeAutoscalingConfigOverride(
          msgs, existing_option.overrides, patch_option.overrides
      )
    else:
      # Add new option
      option_by_location[location] = patch_option

  instance_obj.autoscalingConfig.asymmetricAutoscalingOptions.clear()
  for opt in option_by_location.values():
    instance_obj.autoscalingConfig.asymmetricAutoscalingOptions.append(opt)


def Create(
    instance,
    config,
    description,
    nodes,
    processing_units=None,
    autoscaling_min_nodes=None,
    autoscaling_max_nodes=None,
    autoscaling_min_processing_units=None,
    autoscaling_max_processing_units=None,
    autoscaling_high_priority_cpu_target=None,
    autoscaling_storage_target=None,
    asymmetric_autoscaling_options=None,
    instance_type=None,
    expire_behavior=None,
    default_storage_type=None,
    ssd_cache=None,
    edition=None,
    default_backup_schedule_type=None,
):
  """Create a new instance.

  Args:
    instance: The instance to create.
    config: The instance config to use.
    description: The instance description.
    nodes: The number of nodes to use.
    processing_units: The number of processing units to use.
    autoscaling_min_nodes: The minimum number of nodes to use.
    autoscaling_max_nodes: The maximum number of nodes to use.
    autoscaling_min_processing_units: The minimum number of processing units to
      use.
    autoscaling_max_processing_units: The maximum number of processing units to
      use.
    autoscaling_high_priority_cpu_target: The high priority CPU target to use.
    autoscaling_storage_target: The storage target to use.
    asymmetric_autoscaling_options: A list of ordered dict of key-value pairs
      representing the asymmetric autoscaling options.
    instance_type: The instance type to use.
    expire_behavior: The expire behavior to use.
    default_storage_type: The default storage type to use.
    ssd_cache: The ssd cache to use.
    edition: The edition to use.
    default_backup_schedule_type: The type of default backup schedule to use.

  Returns:
    The created instance.
  """
  client = apis.GetClientInstance(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  # Module containing the definitions of messages for the specified API.
  msgs = apis.GetMessagesModule(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  config_ref = resources.REGISTRY.Parse(
      config,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instanceConfigs',
  )
  project_ref = resources.REGISTRY.Create(
      'spanner.projects', projectsId=properties.VALUES.core.project.GetOrFail
  )
  instance_obj = msgs.Instance(
      config=config_ref.RelativeName(), displayName=description
  )
  if nodes:
    instance_obj.nodeCount = nodes
  elif processing_units:
    instance_obj.processingUnits = processing_units
  elif (
      autoscaling_min_nodes
      or autoscaling_max_nodes
      or autoscaling_min_processing_units
      or autoscaling_max_processing_units
      or autoscaling_high_priority_cpu_target
      or autoscaling_storage_target
  ):
    instance_obj.autoscalingConfig = msgs.AutoscalingConfig(
        autoscalingLimits=msgs.AutoscalingLimits(
            minNodes=autoscaling_min_nodes,
            maxNodes=autoscaling_max_nodes,
            minProcessingUnits=autoscaling_min_processing_units,
            maxProcessingUnits=autoscaling_max_processing_units,
        ),
        autoscalingTargets=msgs.AutoscalingTargets(
            highPriorityCpuUtilizationPercent=autoscaling_high_priority_cpu_target,
            storageUtilizationPercent=autoscaling_storage_target,
        ),
    )
  if instance_type is not None:
    instance_obj.instanceType = instance_type
  if expire_behavior is not None:
    instance_obj.freeInstanceMetadata = msgs.FreeInstanceMetadata(
        expireBehavior=expire_behavior
    )
  if default_storage_type is not None:
    instance_obj.defaultStorageType = default_storage_type
  if ssd_cache and ssd_cache.strip():
    instance_obj.ssdCache = (
        config_ref.RelativeName() + '/ssdCaches/' + ssd_cache.strip()
    )
  if edition is not None:
    instance_obj.edition = msgs.Instance.EditionValueValuesEnum(edition)
  if default_backup_schedule_type is not None:
    instance_obj.defaultBackupScheduleType = (
        msgs.Instance.DefaultBackupScheduleTypeValueValuesEnum(
            default_backup_schedule_type
        )
    )
  # Add asymmetric autoscaling options, if present.
  if asymmetric_autoscaling_options is not None:
    for asym_option in asymmetric_autoscaling_options:
      instance_obj.autoscalingConfig.asymmetricAutoscalingOptions.append(
          msgs.AsymmetricAutoscalingOption(
              overrides=MaybeGetAutoscalingOverride(msgs, asym_option),
              replicaSelection=msgs.InstanceReplicaSelection(
                  location=asym_option['location']
              ),
          )
      )
  req = msgs.SpannerProjectsInstancesCreateRequest(
      parent=project_ref.RelativeName(),
      createInstanceRequest=msgs.CreateInstanceRequest(
          instanceId=instance, instance=instance_obj
      ),
  )
  return client.projects_instances.Create(req)


def SetPolicy(instance_ref, policy, field_mask=None):
  """Saves the given policy on the instance, overwriting whatever exists."""
  client = apis.GetClientInstance(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  msgs = apis.GetMessagesModule(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  policy.version = iam_util.MAX_LIBRARY_IAM_SUPPORTED_VERSION
  req = msgs.SpannerProjectsInstancesSetIamPolicyRequest(
      resource=instance_ref.RelativeName(),
      setIamPolicyRequest=msgs.SetIamPolicyRequest(policy=policy,
                                                   updateMask=field_mask))
  return client.projects_instances.SetIamPolicy(req)


def GetIamPolicy(instance_ref):
  """Gets the IAM policy on an instance."""
  client = apis.GetClientInstance(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  msgs = apis.GetMessagesModule(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  req = msgs.SpannerProjectsInstancesGetIamPolicyRequest(
      resource=instance_ref.RelativeName(),
      getIamPolicyRequest=msgs.GetIamPolicyRequest(
          options=msgs.GetPolicyOptions(
              requestedPolicyVersion=
              iam_util.MAX_LIBRARY_IAM_SUPPORTED_VERSION)))
  return client.projects_instances.GetIamPolicy(req)


def Delete(instance):
  """Delete an instance."""
  client = apis.GetClientInstance(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  msgs = apis.GetMessagesModule(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  ref = resources.REGISTRY.Parse(
      instance,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instances')
  req = msgs.SpannerProjectsInstancesDeleteRequest(name=ref.RelativeName())
  return client.projects_instances.Delete(req)


def Get(instance):
  """Get an instance by name."""
  client = apis.GetClientInstance(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  msgs = apis.GetMessagesModule(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  ref = resources.REGISTRY.Parse(
      instance,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instances')
  req = msgs.SpannerProjectsInstancesGetRequest(name=ref.RelativeName())
  return client.projects_instances.Get(req)


def List():
  """List instances in the project."""
  client = apis.GetClientInstance(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  msgs = apis.GetMessagesModule(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  project_ref = resources.REGISTRY.Create(
      'spanner.projects', projectsId=properties.VALUES.core.project.GetOrFail)
  tp_proto = timestamp_pb2.Timestamp()
  tp_proto.FromDatetime(
      datetime.datetime.utcnow() + UNREACHABLE_INSTANCE_TIMEOUT)
  req = msgs.SpannerProjectsInstancesListRequest(
      parent=project_ref.RelativeName(),
      instanceDeadline=tp_proto.ToJsonString())
  return list_pager.YieldFromList(
      client.projects_instances,
      req,
      field='instances',
      batch_size_attribute='pageSize',
      get_field_func=response_util.GetFieldAndLogUnreachable)


def Patch(
    instance,
    description=None,
    nodes=None,
    processing_units=None,
    autoscaling_min_nodes=None,
    autoscaling_max_nodes=None,
    autoscaling_min_processing_units=None,
    autoscaling_max_processing_units=None,
    autoscaling_high_priority_cpu_target=None,
    autoscaling_storage_target=None,
    asymmetric_autoscaling_options=None,
    clear_asymmetric_autoscaling_options=None,
    instance_type=None,
    expire_behavior=None,
    ssd_cache_id=None,
    edition=None,
    default_backup_schedule_type=None,
):
  """Update an instance."""
  fields = []
  if description is not None:
    fields.append('displayName')
  if nodes is not None:
    fields.append('nodeCount,autoscalingConfig')
  if processing_units is not None:
    fields.append('processingUnits,autoscalingConfig')

  if (
      (autoscaling_min_nodes and autoscaling_max_nodes)
      or (autoscaling_min_processing_units and autoscaling_max_processing_units)
  ) and (autoscaling_high_priority_cpu_target and autoscaling_storage_target):
    fields.append(_FIELD_MASK_AUTOSCALING_CONFIG)
  else:
    if autoscaling_min_nodes:
      fields.append('autoscalingConfig.autoscalingLimits.minNodes')
    if autoscaling_max_nodes:
      fields.append('autoscalingConfig.autoscalingLimits.maxNodes')
    if autoscaling_min_processing_units:
      fields.append('autoscalingConfig.autoscalingLimits.minProcessingUnits')
    if autoscaling_max_processing_units:
      fields.append('autoscalingConfig.autoscalingLimits.maxProcessingUnits')
    if autoscaling_high_priority_cpu_target:
      fields.append(
          'autoscalingConfig.autoscalingTargets.highPriorityCpuUtilizationPercent'
      )
    if autoscaling_storage_target:
      fields.append(
          'autoscalingConfig.autoscalingTargets.storageUtilizationPercent'
      )
  client = apis.GetClientInstance(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  msgs = apis.GetMessagesModule(_SPANNER_API_NAME, _SPANNER_API_VERSION)

  instance_obj = msgs.Instance(displayName=description)
  if processing_units:
    instance_obj.processingUnits = processing_units
  elif nodes:
    instance_obj.nodeCount = nodes
  elif (
      autoscaling_min_nodes
      or autoscaling_max_nodes
      or autoscaling_min_processing_units
      or autoscaling_max_processing_units
      or autoscaling_high_priority_cpu_target
      or autoscaling_storage_target
  ):
    instance_obj.autoscalingConfig = msgs.AutoscalingConfig(
        autoscalingLimits=msgs.AutoscalingLimits(
            minNodes=autoscaling_min_nodes,
            maxNodes=autoscaling_max_nodes,
            minProcessingUnits=autoscaling_min_processing_units,
            maxProcessingUnits=autoscaling_max_processing_units,
        ),
        autoscalingTargets=msgs.AutoscalingTargets(
            highPriorityCpuUtilizationPercent=autoscaling_high_priority_cpu_target,
            storageUtilizationPercent=autoscaling_storage_target,
        ),
    )

  if asymmetric_autoscaling_options is not None:
    if _FIELD_MASK_AUTOSCALING_CONFIG not in fields:
      fields.append('autoscalingConfig.asymmetricAutoscalingOptions')
    current_instance = Get(instance)
    asym_options_patch = []
    # Create AsymmetricAutoscalingOption objects from the flag value (key-value
    # pairs).
    for asym_option in asymmetric_autoscaling_options:
      asym_options_patch.append(
          msgs.AsymmetricAutoscalingOption(
              replicaSelection=msgs.InstanceReplicaSelection(
                  location=asym_option['location']
              ),
              overrides=MaybeGetAutoscalingOverride(msgs, asym_option),
          )
      )
    if instance_obj.autoscalingConfig is None:
      instance_obj.autoscalingConfig = msgs.AutoscalingConfig()
    PatchAsymmetricAutoscalingOptions(
        msgs, instance_obj, current_instance, asym_options_patch
    )

  if clear_asymmetric_autoscaling_options is not None:
    if _FIELD_MASK_AUTOSCALING_CONFIG not in fields:
      fields.append('autoscalingConfig.asymmetricAutoscalingOptions')
    current_instance = Get(instance)
    locations_to_remove = set(clear_asymmetric_autoscaling_options)
    if instance_obj.autoscalingConfig is None:
      instance_obj.autoscalingConfig = msgs.AutoscalingConfig()
    instance_obj.autoscalingConfig.asymmetricAutoscalingOptions = []
    for (
        asym_option
    ) in current_instance.autoscalingConfig.asymmetricAutoscalingOptions:
      if asym_option.replicaSelection.location not in locations_to_remove:
        instance_obj.autoscalingConfig.asymmetricAutoscalingOptions.append(
            asym_option
        )

  if instance_type is not None:
    fields.append('instanceType')
    instance_obj.instanceType = instance_type
  if expire_behavior is not None:
    fields.append('freeInstanceMetadata.expireBehavior')
    instance_obj.freeInstanceMetadata = msgs.FreeInstanceMetadata(
        expireBehavior=expire_behavior)

  if ssd_cache_id is not None:
    fields.append('ssdCache')
    ssd_cache = ''
    if ssd_cache_id.strip():
      instance_res = Get(instance)
      ssd_cache = instance_res.config + '/ssdCaches/' + ssd_cache_id.strip()
    instance_obj.ssdCache = ssd_cache
  if edition is not None:
    fields.append('edition')
    instance_obj.edition = msgs.Instance.EditionValueValuesEnum(edition)
  if default_backup_schedule_type is not None:
    fields.append('defaultBackupScheduleType')
    instance_obj.defaultBackupScheduleType = (
        msgs.Instance.DefaultBackupScheduleTypeValueValuesEnum(
            default_backup_schedule_type
        )
    )

  ref = resources.REGISTRY.Parse(
      instance,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instances')
  req = msgs.SpannerProjectsInstancesPatchRequest(
      name=ref.RelativeName(),
      updateInstanceRequest=msgs.UpdateInstanceRequest(
          fieldMask=','.join(fields), instance=instance_obj))
  return client.projects_instances.Patch(req)


def GetLocations(instance, verbose_flag):
  """Get all the replica regions for an instance."""
  client = apis.GetClientInstance(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  msgs = apis.GetMessagesModule(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  instance_res = Get(instance)
  config_req = msgs.SpannerProjectsInstanceConfigsGetRequest(
      name=instance_res.config)
  config_res = client.projects_instanceConfigs.Get(config_req)
  if verbose_flag:
    command_output = []
    for item in config_res.replicas:
      command_output.append({'location': item.location, 'type': item.type})
  else:
    region_set = set()
    for item in config_res.replicas:
      region_set.add(item.location)
    command_output = [{'location': item} for item in region_set]
  return command_output


def Move(instance, target_instance_config, target_database_move_configs):
  """Moves an instance from one instance-config to another.

  Args:
      instance: Instance to move.
      target_instance_config: The target instance configuration to move the
        instance.
      target_database_move_configs: Configurations for databases in the
        destination instance config.

  The configs can be google-managed or user-managed.
  Ex: gcloud spanner instances move instance-to-move
  --target-config=instance-config-to-move-to

  Above example will move the instance(instance-to-move) to the following
  instance config(instance-config-to-move-to).
  """
  client = apis.GetClientInstance(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  msgs = apis.GetMessagesModule(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  config_ref = resources.REGISTRY.Parse(
      target_instance_config,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instanceConfigs',
  )
  instance_ref = resources.REGISTRY.Parse(
      instance,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instances',
  )
  console_io.PromptContinue(
      message=(
          'You are about to move instance {0} from {1} to {2}. This is a'
          ' long-running operation with potential service'
          ' implications:\n\n\n\t* Increased latencies: Read and write'
          ' operations may experience delays.\n\n\t* Elevated abort rate:'
          ' Transactions may have a higher chance of failing.\n\n\t* Spiked CPU'
          ' utilization: System resources will be strained, impacting'
          ' performance.\n\n\t* Additional costs: Instance moves incur extra'
          ' charges, as described in the documentation.\n\n\t* Backups: It is'
          ' important that you copy your backups before moving your instance.'
          ' Backups need to be deleted from the Instance before the move. You'
          ' cannot create a backup while the move is in progress.\n\nBefore'
          ' proceeding, and for detailed information and best practices, refer'
          ' to the documentation at'
          ' https://cloud.google.com/spanner/docs/move-instance#move-prerequisites.'
          .format(
              instance, GetInstanceConfig(instance), target_instance_config
          )
      ),
      cancel_on_no=True,
      prompt_string='Do you want to proceed',
  )
  req_args = {'targetConfig': config_ref.RelativeName()}
  if target_database_move_configs is not None:
    req_args['targetDatabaseMoveConfigs'] = []
    for target_database_move_config in target_database_move_configs:
      kms_key_names = target_database_move_config['kms-key-names'].split(',')
      encryption_config_args = {}
      encryption_config_args['kmsKeyNames'] = []
      for kms_key_name in kms_key_names:
        encryption_config_args['kmsKeyNames'].append(kms_key_name)
      encryption_config = msgs.InstanceEncryptionConfig(
          **encryption_config_args
      )
      req_args['targetDatabaseMoveConfigs'].append(
          msgs.DatabaseMoveConfig(
              databaseId=target_database_move_config['database-id'],
              encryptionConfig=encryption_config,
          )
      )
  move_req = msgs.SpannerProjectsInstancesMoveRequest(
      moveInstanceRequest=msgs.MoveInstanceRequest(**req_args),
      name=instance_ref.RelativeName(),
  )
  move_operation_id = client.projects_instances.Move(move_req).name
  operation_id = re.search('.*/operations/(.*)', move_operation_id).group(1)
  print(
      '\nInstance move started for {0}\n\n'
      'Track progress with: gcloud spanner operations'
      ' describe {1} --instance={2}'.format(
          instance_ref.RelativeName(), operation_id, instance
      )
  )


def GetInstanceConfig(instance):
  """Get the instance config of the passed instance."""
  client = apis.GetClientInstance(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  msgs = apis.GetMessagesModule(_SPANNER_API_NAME, _SPANNER_API_VERSION)
  instance_ref = resources.REGISTRY.Parse(
      instance,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instances',
  )
  instance_req = msgs.SpannerProjectsInstancesGetRequest(
      name=instance_ref.RelativeName(), fieldMask='config'
  )
  instance_info = client.projects_instances.Get(instance_req)
  instance_config = re.search(
      '.*/instanceConfigs/(.*)', instance_info.config
  ).group(1)
  return instance_config
