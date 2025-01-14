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
"""Allows you to write surfaces in terms of logical Cloud Run V2 WorkerPools API operations."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from google.api_core import exceptions
from googlecloudsdk.api_lib.run import metric_names
from googlecloudsdk.command_lib.run.v2 import config_changes as config_changes_mod
from googlecloudsdk.core import metrics
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import worker_pool as worker_pool_objects


class WorkerPoolsOperations(object):
  """Client used to communicate with the actual Cloud Run V2 WorkerPools API."""

  def __init__(self, client):
    self._client = client

  def GetWorkerPool(self, worker_pool_ref):
    """Get the WorkerPool.

    Args:
      worker_pool_ref: Resource, WorkerPool to get.

    Returns:
      A WorkerPool object.
    """
    worker_pools = self._client.worker
    get_request = self._client.types.GetWorkerPoolRequest(
        name=worker_pool_ref.RelativeName()
    )
    try:
      with metrics.RecordDuration(metric_names.GET_WORKER_POOL):
        return worker_pools.get_worker_pool(get_request)
    except exceptions.NotFound:
      return None

  def DeleteWorkerPool(self, worker_pool_ref):
    """Delete the WorkerPool.

    Args:
      worker_pool_ref: Resource, WorkerPool to delete.

    Returns:
      A LRO for delete operation.
    """
    worker_pools = self._client.worker
    delete_request = self._client.types.DeleteWorkerPoolRequest(
        name=worker_pool_ref.RelativeName()
    )
    try:
      with metrics.RecordDuration(metric_names.DELETE_WORKER_POOL):
        return worker_pools.delete_worker_pool(delete_request)
    except exceptions.NotFound:
      return None

  def ListWorkerPools(self, region_ref):
    """List the WorkerPools in a region.

    Args:
      region_ref: Resource, Region to get the list of WorkerPools from.

    Returns:
      A list of WorkerPool objects.
    """
    worker_pools = self._client.worker
    list_request = self._client.types.ListWorkerPoolsRequest(
        parent=region_ref.RelativeName()
    )
    # TODO(b/366501494): Support `next_page_token`
    with metrics.RecordDuration(metric_names.LIST_WORKER_POOLS):
      return worker_pools.list_worker_pools(list_request)

  def ReleaseWorkerPool(self, worker_pool_ref, worker_pool, config_changes):
    """Stubbed method for worker pool deploy surface.

    Update the WorkerPool if it exists, otherwise create it (Upsert).

    Args:
      worker_pool_ref: WorkerPool reference containing project, location,
        workerpool IDs.
      worker_pool: Resource, the WorkerPool to release. None for create flow.
      config_changes: list, objects that implement Adjust().

    Returns:
      A WorkerPool object.
    """
    # TODO(b/376904673): Add progress tracker.
    metric_name = metric_names.UPDATE_WORKER_POOL
    if worker_pool is None:
      # WorkerPool does not exist, create it.
      worker_pool = worker_pool_objects.WorkerPool(
          name=worker_pool_ref.RelativeName(),
      )
      metric_name = metric_names.CREATE_WORKER_POOL
    # Apply config changes to the WorkerPool.
    worker_pool = config_changes_mod.WithChanges(worker_pool, config_changes)
    worker_pools = self._client.worker
    upsert_request = self._client.types.UpdateWorkerPoolRequest(
        worker_pool=worker_pool,
        allow_missing=True,
    )
    # TODO(b/366576967): Support wait operation in sync mode.
    with metrics.RecordDuration(metric_name):
      return worker_pools.update_worker_pool(upsert_request)

  def UpdateInstanceSplit(
      self,
      worker_pool_ref,
      config_changes,
  ):
    """Update the instance split of a WorkerPool."""
    # TODO: b/376904673 - Add progress tracker.
    worker_pool = self.GetWorkerPool(worker_pool_ref)
    if worker_pool is None:
      raise exceptions.NotFound(
          'WorkerPool [{}] could not be found.'.format(
              worker_pool_ref.workerPoolsId
          )
      )
    worker_pool = config_changes_mod.WithChanges(worker_pool, config_changes)
    worker_pools = self._client.worker
    update_request = self._client.types.UpdateWorkerPoolRequest(
        worker_pool=worker_pool,
    )
    with metrics.RecordDuration(metric_names.UPDATE_WORKER_POOL):
      # TODO(b/366576967): Support wait operation in sync mode.
      return worker_pools.update_worker_pool(update_request)
