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

"""Task for deleting a managed folder."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.command_lib.storage import progress_callbacks
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.core import log


class DeleteManagedFolderTask(task.Task):
  """Represents a command operation copying an object around the cloud."""

  def __init__(
      self,
      managed_folder_resource,
      verbose=True,
  ):
    """Initializes DeleteManagedFolderTask.

    Args:
      managed_folder_resource (resource_reference.Resource): Indicates the
        resource to delete.
      verbose (bool): If True, prints status messages.
    """
    super(DeleteManagedFolderTask, self).__init__()
    self._managed_folder_resource = managed_folder_resource
    self._verbose = verbose

    self.parallel_processing_key = (
        self._managed_folder_resource.storage_url.url_string
    )

  @property
  def managed_folder_resource(self):
    """The resource deleted by this task.

    Exposing this allows execution to respect containment order.
    """
    return self._managed_folder_resource

  def execute(self, task_status_queue=None):
    if self._verbose:
      log.status.Print('Removing {}...'.format(self._managed_folder_resource))

    url = self._managed_folder_resource.storage_url
    api_client = api_factory.get_api(url.scheme)
    api_client.delete_managed_folder(url.bucket_name, url.object_name)

    if task_status_queue:
      progress_callbacks.increment_count_callback(task_status_queue)

  def __eq__(self, other):
    if not isinstance(other, DeleteManagedFolderTask):
      return NotImplemented
    return (
        self._managed_folder_resource == other._managed_folder_resource
        and self._verbose == other._verbose
    )
