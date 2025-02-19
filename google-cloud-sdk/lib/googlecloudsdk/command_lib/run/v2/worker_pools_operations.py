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
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.run import stages
from googlecloudsdk.command_lib.run.sourcedeploys import deployer
from googlecloudsdk.command_lib.run.v2 import config_changes as config_changes_mod
from googlecloudsdk.core import metrics
from googlecloudsdk.core.console import progress_tracker
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

  def ReleaseWorkerPool(
      self,
      worker_pool_ref,
      config_changes,
      release_track=base.ReleaseTrack.ALPHA,
      tracker=None,
      prefetch=False,
      build_image=None,
      build_pack=None,
      build_source=None,
      build_from_source_container_name=None,
      repo_to_create=None,
      already_activated_services=False,
      force_new_revision=False,
  ):
    """Stubbed method for worker pool deploy surface.

    Update the WorkerPool if it exists, otherwise create it (Upsert).

    Args:
      worker_pool_ref: WorkerPool reference containing project, location,
        workerpool IDs.
      config_changes: list, objects that implement Adjust().
      release_track: ReleaseTrack, the release track of a command calling this.
      tracker: StagedProgressTracker, used to track progress.
      prefetch: the worker pool, pre-fetched for ReleaseWorkerPool. `False`
        indicates the caller did not perform a prefetch; `None` indicates a
        nonexistent worker pool.
      build_image: The build image reference to the build.
      build_pack: The build pack reference to the build.
      build_source: The build source reference to the build.
      build_from_source_container_name: The name of the container to be deployed
        from source.
      repo_to_create: Optional
        googlecloudsdk.command_lib.artifacts.docker_util.DockerRepo defining a
        repository to be created.
      already_activated_services: bool. If true, skip activation prompts for
        services
      force_new_revision: bool to force a new revision to be created.

    Returns:
      A WorkerPool object.
    """
    if tracker is None:
      tracker = progress_tracker.NoOpStagedProgressTracker(
          stages.WorkerPoolStages(
              include_build=build_source is not None,
              include_create_repo=repo_to_create is not None,
          ),
          interruptable=True,
          aborted_message='aborted',
      )

    # Deploying from a source.
    if build_source is not None:
      (
          image_digest,
          _,  # build_base_image
          _,  # build_id
          _,  # uploaded_source
          _,  # build_name
      ) = deployer.CreateImage(
          tracker,
          build_image,
          build_source,
          build_pack,
          repo_to_create,
          release_track,
          already_activated_services,
          worker_pool_ref.locationsId,  # region
          worker_pool_ref,
      )
      if image_digest is None:
        return
      config_changes.append(
          config_changes_mod.AddDigestToImageChange(
              container_name=build_from_source_container_name,
              non_ingress_type=True,
              image_digest=image_digest,
          )
      )

    if prefetch is None:
      worker_pool = None
    elif build_source:
      # if we're building from source, we want to force a new fetch
      # because building takes a while which leaves a long time for
      # potential write conflicts.
      worker_pool = self.GetWorkerPool(worker_pool_ref)
    else:
      worker_pool = prefetch or self.GetWorkerPool(worker_pool_ref)
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
        force_new_revision=force_new_revision,
    )
    with metrics.RecordDuration(metric_name):
      return worker_pools.update_worker_pool(upsert_request)

  def UpdateInstanceSplit(
      self,
      worker_pool_ref,
      config_changes,
  ):
    """Update the instance split of a WorkerPool."""
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
      return worker_pools.update_worker_pool(update_request)

  def GetRevision(self, worker_pool_revision_ref):
    """Get the Revision.

    Args:
      worker_pool_revision_ref: Resource, Revision to get.

    Returns:
      A Revision object.
    """
    worker_pool_revisions = self._client.revisions
    get_request = self._client.types.GetRevisionRequest(
        name=worker_pool_revision_ref.RelativeName()
    )
    try:
      with metrics.RecordDuration(metric_names.GET_WORKER_POOL_REVISION):
        return worker_pool_revisions.get_revision(get_request)
    except exceptions.NotFound:
      return None

  def DeleteRevision(self, worker_pool_revision_ref):
    """Delete the Revision.

    Args:
      worker_pool_revision_ref: Resource, Revision to delete.

    Returns:
      A LRO for delete operation.
    """
    worker_pool_revisions = self._client.revisions
    delete_request = self._client.types.DeleteRevisionRequest(
        name=worker_pool_revision_ref.RelativeName()
    )
    try:
      with metrics.RecordDuration(metric_names.DELETE_WORKER_POOL_REVISION):
        return worker_pool_revisions.delete_revision(delete_request)
    except exceptions.NotFound:
      return None

  def ListRevisions(self, worker_pool_ref):
    """List the Revisions in a region under the given WorkerPool.

    Args:
      worker_pool_ref: Resource, WorkerPool to get the list of Revisions from.

    Returns:
      A list of Revision objects.
    """
    worker_pool_revisions = self._client.revisions
    list_request = self._client.types.ListRevisionsRequest(
        parent=worker_pool_ref.RelativeName()
    )
    # TODO(b/366501494): Support `next_page_token`
    with metrics.RecordDuration(metric_names.LIST_WORKER_POOL_REVISIONS):
      return worker_pool_revisions.list_revisions(list_request)
