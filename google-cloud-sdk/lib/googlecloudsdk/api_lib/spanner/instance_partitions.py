# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Spanner instance partition API helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime

from apitools.base.py import list_pager
from cloudsdk.google.protobuf import timestamp_pb2
from googlecloudsdk.api_lib.spanner import response_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


# The list of pre-defined IAM roles in Spanner.
KNOWN_ROLES = [
    'roles/spanner.admin',
    'roles/spanner.databaseAdmin',
    'roles/spanner.databaseReader',
    'roles/spanner.databaseUser',
    'roles/spanner.viewer',
]

# Timeout to use in ListInstancePartitions for unreachable instance partitions.
UNREACHABLE_INSTANCE_PARTITION_TIMEOUT = datetime.timedelta(seconds=20)

_API_NAME = 'spanner'
_API_VERSION = 'v1'


def Create(
    instance_ref,
    instance_partition,
    config,
    description,
    nodes,
    processing_units=None,
    autoscaling_min_nodes=None,
    autoscaling_max_nodes=None,
    autoscaling_min_processing_units=None,
    autoscaling_max_processing_units=None,
    autoscaling_high_priority_cpu_target=None,
    autoscaling_total_cpu_target=None,
    autoscaling_storage_target=None,
):
  """Create a new instance partition."""
  client = apis.GetClientInstance(_API_NAME, _API_VERSION)
  # Module containing the definitions of messages for the specified API.
  msgs = apis.GetMessagesModule(_API_NAME, _API_VERSION)
  config_ref = resources.REGISTRY.Parse(
      config,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instanceConfigs',
  )
  instance_partition_obj = msgs.InstancePartition(
      config=config_ref.RelativeName(), displayName=description
  )
  if nodes:
    instance_partition_obj.nodeCount = nodes
  elif processing_units:
    instance_partition_obj.processingUnits = processing_units
  elif (
      autoscaling_min_nodes
      or autoscaling_max_nodes
      or autoscaling_min_processing_units
      or autoscaling_max_processing_units
      or autoscaling_high_priority_cpu_target
      or autoscaling_total_cpu_target
      or autoscaling_storage_target
  ):
    instance_partition_obj.autoscalingConfig = msgs.AutoscalingConfig(
        autoscalingLimits=msgs.AutoscalingLimits(
            minNodes=autoscaling_min_nodes,
            maxNodes=autoscaling_max_nodes,
            minProcessingUnits=autoscaling_min_processing_units,
            maxProcessingUnits=autoscaling_max_processing_units,
        ),
        autoscalingTargets=msgs.AutoscalingTargets(
            highPriorityCpuUtilizationPercent=autoscaling_high_priority_cpu_target,
            totalCpuUtilizationPercent=autoscaling_total_cpu_target,
            storageUtilizationPercent=autoscaling_storage_target,
        ),
    )
  req = msgs.SpannerProjectsInstancesInstancePartitionsCreateRequest(
      parent=instance_ref.RelativeName(),
      createInstancePartitionRequest=msgs.CreateInstancePartitionRequest(
          instancePartitionId=instance_partition,
          instancePartition=instance_partition_obj,
      ),
  )
  return client.projects_instances_instancePartitions.Create(req)


def Get(instance_partition_ref):
  """Get an instance partition by name."""
  client = apis.GetClientInstance(_API_NAME, _API_VERSION)
  msgs = apis.GetMessagesModule(_API_NAME, _API_VERSION)
  req = msgs.SpannerProjectsInstancesInstancePartitionsGetRequest(
      name=instance_partition_ref.RelativeName()
  )
  return client.projects_instances_instancePartitions.Get(req)


def Patch(
    instance_partition_ref,
    description=None,
    nodes=None,
    processing_units=None,
    autoscaling_min_nodes=None,
    autoscaling_max_nodes=None,
    autoscaling_min_processing_units=None,
    autoscaling_max_processing_units=None,
    autoscaling_high_priority_cpu_target=None,
    autoscaling_total_cpu_target=None,
    autoscaling_storage_target=None,
):
  """Update an instance partition."""
  fields = []
  if description is not None:
    fields.append('displayName')
  if nodes is not None:
    fields.append('nodeCount')
  if processing_units is not None:
    fields.append('processingUnits')

  if (
      (autoscaling_min_nodes and autoscaling_max_nodes)
      or (autoscaling_min_processing_units and autoscaling_max_processing_units)
  ) and (
      (autoscaling_high_priority_cpu_target or autoscaling_total_cpu_target)
      and autoscaling_storage_target
  ):
    fields.append('autoscalingConfig')
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
    if autoscaling_total_cpu_target:
      fields.append(
          'autoscalingConfig.autoscalingTargets.totalCpuUtilizationPercent'
      )
    if autoscaling_storage_target:
      fields.append(
          'autoscalingConfig.autoscalingTargets.storageUtilizationPercent'
      )

  client = apis.GetClientInstance(_API_NAME, _API_VERSION)
  msgs = apis.GetMessagesModule(_API_NAME, _API_VERSION)

  instance_partition_obj = msgs.InstancePartition(displayName=description)
  if processing_units:
    instance_partition_obj.processingUnits = processing_units
  elif nodes:
    instance_partition_obj.nodeCount = nodes
  elif (
      autoscaling_min_nodes
      or autoscaling_max_nodes
      or autoscaling_min_processing_units
      or autoscaling_max_processing_units
      or autoscaling_high_priority_cpu_target
      or autoscaling_total_cpu_target
      or autoscaling_storage_target
  ):
    instance_partition_obj.autoscalingConfig = msgs.AutoscalingConfig(
        autoscalingLimits=msgs.AutoscalingLimits(
            minNodes=autoscaling_min_nodes,
            maxNodes=autoscaling_max_nodes,
            minProcessingUnits=autoscaling_min_processing_units,
            maxProcessingUnits=autoscaling_max_processing_units,
        ),
        autoscalingTargets=msgs.AutoscalingTargets(
            highPriorityCpuUtilizationPercent=autoscaling_high_priority_cpu_target,
            totalCpuUtilizationPercent=autoscaling_total_cpu_target,
            storageUtilizationPercent=autoscaling_storage_target,
        ),
    )

  req = msgs.SpannerProjectsInstancesInstancePartitionsPatchRequest(
      name=instance_partition_ref.RelativeName(),
      updateInstancePartitionRequest=msgs.UpdateInstancePartitionRequest(
          fieldMask=','.join(fields), instancePartition=instance_partition_obj
      ),
  )
  return client.projects_instances_instancePartitions.Patch(req)


def List(instance_ref):
  """List instance partitions in the project."""
  client = apis.GetClientInstance(_API_NAME, _API_VERSION)
  msgs = apis.GetMessagesModule(_API_NAME, _API_VERSION)
  tp_proto = timestamp_pb2.Timestamp()
  tp_proto.FromDatetime(
      datetime.datetime.now(tz=datetime.timezone.utc)
      + UNREACHABLE_INSTANCE_PARTITION_TIMEOUT
  )
  req = msgs.SpannerProjectsInstancesInstancePartitionsListRequest(
      parent=instance_ref.RelativeName(),
      instancePartitionDeadline=tp_proto.ToJsonString(),
  )
  return list_pager.YieldFromList(
      client.projects_instances_instancePartitions,
      req,
      field='instancePartitions',
      batch_size_attribute='pageSize',
      get_field_func=response_util.GetFieldAndLogUnreachableInstancePartitions,
  )


def Delete(instance_partition_ref):
  """Delete an instance partition."""
  client = apis.GetClientInstance(_API_NAME, _API_VERSION)
  msgs = apis.GetMessagesModule(_API_NAME, _API_VERSION)
  req = msgs.SpannerProjectsInstancesInstancePartitionsDeleteRequest(
      name=instance_partition_ref.RelativeName()
  )
  return client.projects_instances_instancePartitions.Delete(req)
