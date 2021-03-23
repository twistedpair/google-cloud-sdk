# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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

"""Task for file downloads.

Typically executed in a task iterator:
googlecloudsdk.command_lib.storage.tasks.task_executor.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import tracker_file_util
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks.cp import copy_component_util
from googlecloudsdk.command_lib.storage.tasks.cp import file_part_download_task
from googlecloudsdk.command_lib.storage.tasks.cp import finalize_sliced_download_task
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import scaled_integer


def _should_perform_sliced_download(resource):
  threshold = scaled_integer.ParseInteger(
      properties.VALUES.storage.sliced_object_download_threshold.Get())
  component_size = scaled_integer.ParseInteger(
      properties.VALUES.storage.sliced_object_download_component_size.Get())
  return (resource.size and threshold != 0 and resource.size > threshold and
          component_size and
          resource.storage_url.scheme is storage_url.ProviderPrefix.GCS)


class FileDownloadTask(task.Task):
  """Represents a command operation triggering a file download."""

  def __init__(self, source_resource, destination_resource):
    """Initializes task.

    Args:
      source_resource (ObjectResource): Must contain
        the full path of object to download, including bucket. Directories
        will not be accepted. Does not need to contain metadata.
      destination_resource (FileObjectResource|UnknownResource): Must contain
        local filesystem path to upload object. Does not need to contain
        metadata.
    """
    super(FileDownloadTask, self).__init__()
    self._source_resource = source_resource
    self._destination_resource = destination_resource
    self.parallel_processing_key = (
        self._destination_resource.storage_url.url_string)

  def _get_sliced_download_tasks(self):
    """Creates all tasks necessary for a sliced download."""
    component_offsets_and_lengths = copy_component_util.get_component_offsets_and_lengths(
        self._source_resource.size,
        properties.VALUES.storage.sliced_object_download_component_size.Get(),
        properties.VALUES.storage.sliced_object_download_max_components.GetInt(
        ))

    download_component_task_list = []
    for i, (offset, length) in enumerate(component_offsets_and_lengths):
      download_component_task_list.append(
          file_part_download_task.FilePartDownloadTask(
              self._source_resource,
              self._destination_resource,
              offset=offset,
              length=length,
              component_number=i,
              total_components=len(component_offsets_and_lengths)))

    finalize_sliced_download_task_list = [
        finalize_sliced_download_task.FinalizeSlicedDownloadTask(
            self._source_resource, self._destination_resource)
    ]

    return (download_component_task_list, finalize_sliced_download_task_list)

  def execute(self, task_status_queue=None):
    """Creates appropriate download tasks."""
    if _should_perform_sliced_download(self._source_resource):
      copy_component_util.create_file_if_needed(self._source_resource,
                                                self._destination_resource)
      download_component_task_list, finalize_sliced_download_task_list = self._get_sliced_download_tasks(
      )

      tracker_file_util.read_or_create_download_tracker_file(
          self._source_resource,
          self._destination_resource.storage_url,
          total_components=len(download_component_task_list),
      )
      log.debug('Launching sliced download with {} components.'.format(
          len(download_component_task_list)))
      return [download_component_task_list, finalize_sliced_download_task_list]
    else:
      file_part_download_task.FilePartDownloadTask(
          self._source_resource,
          self._destination_resource,
          offset=0,
          length=self._source_resource.size).execute(
              task_status_queue=task_status_queue)
