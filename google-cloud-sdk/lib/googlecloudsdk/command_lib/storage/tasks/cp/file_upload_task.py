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

"""Task for file uploads.

Typically executed in a task iterator:
googlecloudsdk.command_lib.storage.tasks.task_executor.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import math
import os

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.command_lib.storage import temporary_components
from googlecloudsdk.command_lib.storage.tasks import compose_objects_task
from googlecloudsdk.command_lib.storage.tasks import delete_object_task
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks.cp import file_part_upload_task
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import scaled_integer


def _get_component_count(file_size, api_max_component_count):
  """Returns the number of components to use for an upload."""
  preferred_component_size = scaled_integer.ParseInteger(
      properties.VALUES.storage.parallel_composite_upload_component_size.Get())
  component_count = math.ceil(file_size / preferred_component_size)

  if component_count < 2:
    return 2
  if component_count > api_max_component_count:
    return api_max_component_count
  return component_count


class FileUploadTask(task.Task):
  """Represents a command operation triggering a file upload."""

  def __init__(self, source_resource, destination_resource):
    """Initializes task.

    Args:
      source_resource (resource_reference.FileObjectResource): Must contain
          local filesystem path to upload object. Does not need to contain
          metadata.
      destination_resource (resource_reference.ObjectResource|UnknownResource):
          Must contain the full object path. Directories will not be accepted.
          Existing objects at the this location will be overwritten.
    """
    super(FileUploadTask, self).__init__()
    self._source_resource = source_resource
    self._destination_resource = destination_resource
    self.parallel_processing_key = (
        self._destination_resource.storage_url.url_string)

    self._composite_upload_threshold = scaled_integer.ParseInteger(
        properties.VALUES.storage.parallel_composite_upload_threshold.Get())

  def execute(self, callback=None):
    source_filename = self._source_resource.storage_url.object_name
    size = os.path.getsize(source_filename)

    should_perform_single_transfer = (
        size < self._composite_upload_threshold or
        not self._composite_upload_threshold
    )

    if should_perform_single_transfer:
      file_part_upload_task.FilePartUploadTask(
          self._source_resource,
          self._destination_resource,
          offset=0,
          length=size).execute()
    else:
      destination_url = self._destination_resource.storage_url
      provider = destination_url.scheme
      api_instance = api_factory.get_api(provider)

      component_count = _get_component_count(
          size, api_instance.MAX_OBJECTS_PER_COMPOSE_CALL)
      component_size = math.ceil(size / component_count)

      file_part_upload_tasks = []
      compose_objects_sources = []
      delete_object_tasks = []
      for component_index in range(component_count):

        temporary_component_resource = temporary_components.get_resource(
            self._source_resource,
            self._destination_resource,
            component_index)

        compose_objects_sources.append(temporary_component_resource)

        offset = component_index * component_size
        length = min(component_size, size - offset)
        upload_task = file_part_upload_task.FilePartUploadTask(
            self._source_resource, temporary_component_resource, offset,
            length)

        file_part_upload_tasks.append(upload_task)

        delete_task = delete_object_task.DeleteObjectTask(
            temporary_component_resource)
        delete_object_tasks.append(delete_task)

      compose_objects_tasks = [compose_objects_task.ComposeObjectsTask(
          compose_objects_sources, self._destination_resource)]

      return [
          file_part_upload_tasks,
          compose_objects_tasks,
          delete_object_tasks,
      ]
