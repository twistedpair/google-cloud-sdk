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
"""Bigtable memory layers API helper."""

from googlecloudsdk.api_lib.bigtable import util


MEMORY_LAYER_SUFFIX = '/memoryLayer'


def Describe(cluster_ref, client=None, msgs=None):
  """Describe a memory layer.

  Args:
    cluster_ref: A resource reference to the cluster of the memory layer to
      describe.
    client: The API client.
    msgs: The API messages.

  Returns:
    Memory layer resource object.
  """
  if client is None:
    client = util.GetAdminClient()
  if msgs is None:
    msgs = util.GetAdminMessages()
  memory_layer_name = cluster_ref.RelativeName() + MEMORY_LAYER_SUFFIX

  msg = msgs.BigtableadminProjectsInstancesClustersGetMemoryLayerRequest(
      name=memory_layer_name
  )
  return client.projects_instances_clusters.GetMemoryLayer(msg)


def Update(
    cluster_ref,
    client=None,
    msgs=None,
    *,
    storage_size_gib=None,
    max_request_units_per_second=None,
):
  """Update a memory layer.

  Args:
    cluster_ref: A resource reference to the cluster to update.
    client: The API client.
    msgs: The API messages.
    storage_size_gib: The storage size of the memory layer in gibibytes.
    max_request_units_per_second: The maximum number of request units per second
      that can be used by the memory layer.

  Returns:
    Long running operation.
  """
  if client is None:
    client = util.GetAdminClient()
  if msgs is None:
    msgs = util.GetAdminMessages()
  memory_layer = msgs.MemoryLayer()
  fixed_capacity = msgs.FixedCapacity()
  changed_fields = []

  if storage_size_gib is not None:
    fixed_capacity.storageSizeGib = storage_size_gib
    changed_fields.append('memory_config.fixed_capacity.storage_size_gib')
  if max_request_units_per_second is not None:
    fixed_capacity.maxRequestUnitsPerSecond = max_request_units_per_second
    changed_fields.append(
        'memory_config.fixed_capacity.max_request_units_per_second'
    )

  memory_layer.memoryConfig = msgs.MemoryConfig(fixedCapacity=fixed_capacity)
  memory_layer_name = cluster_ref.RelativeName() + MEMORY_LAYER_SUFFIX

  msg = msgs.BigtableadminProjectsInstancesClustersUpdateMemoryLayerRequest(
      memoryLayer=memory_layer,
      name=memory_layer_name,
      updateMask=','.join(changed_fields),
  )

  return client.projects_instances_clusters.UpdateMemoryLayer(msg)


def Disable(cluster_ref, client=None, msgs=None):
  """Disable a memory layer.

  Args:
    cluster_ref: A resource reference to the cluster to disable memory layer on.
    client: The API client.
    msgs: The API messages.

  Returns:
    Long running operation.
  """
  if client is None:
    client = util.GetAdminClient()
  if msgs is None:
    msgs = util.GetAdminMessages()
  memory_layer = msgs.MemoryLayer()
  memory_layer_name = cluster_ref.RelativeName() + MEMORY_LAYER_SUFFIX

  msg = msgs.BigtableadminProjectsInstancesClustersUpdateMemoryLayerRequest(
      memoryLayer=memory_layer,
      name=memory_layer_name,
      updateMask='memory_config',
  )

  return client.projects_instances_clusters.UpdateMemoryLayer(msg)
