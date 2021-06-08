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
import random

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import gcs_api
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks import task_executor
from googlecloudsdk.command_lib.storage.tasks.cp import copy_component_util
from googlecloudsdk.command_lib.storage.tasks.cp import file_part_upload_task
from googlecloudsdk.command_lib.storage.tasks.cp import finalize_composite_upload_task
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


def _get_random_prefix():
  """Returns an ID distinguishing upload components from different machines."""
  return str(random.randint(1, 10**10))


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

  def execute(self, task_status_queue=None):
    source_filename = self._source_resource.storage_url.object_name
    size = os.path.getsize(source_filename)

    destination_provider = self._destination_resource.storage_url.scheme
    api_capabilties = api_factory.get_capabilities(destination_provider)
    should_perform_single_transfer = (
        size < self._composite_upload_threshold or
        not self._composite_upload_threshold or
        cloud_api.Capability.COMPOSE_OBJECTS not in api_capabilties or
        not task_executor.should_use_parallelism()
    )

    if should_perform_single_transfer:
      file_part_upload_task.FilePartUploadTask(
          self._source_resource,
          self._destination_resource,
          offset=0,
          length=size).execute(task_status_queue)
    else:
      component_size_property = (
          properties.VALUES.storage.parallel_composite_upload_component_size)
      component_offsets_and_lengths = (
          copy_component_util.get_component_offsets_and_lengths(
              size,
              component_size_property.Get(),
              gcs_api.MAX_OBJECTS_PER_COMPOSE_CALL))

      random_prefix = _get_random_prefix()

      file_part_upload_tasks = []
      for i, (offset, length) in enumerate(component_offsets_and_lengths):

        temporary_component_resource = (
            copy_component_util.get_temporary_component_resource(
                self._source_resource, self._destination_resource,
                random_prefix, i))

        upload_task = file_part_upload_task.FilePartUploadTask(
            self._source_resource,
            temporary_component_resource,
            offset,
            length,
            component_number=i,
            total_components=len(component_offsets_and_lengths))

        file_part_upload_tasks.append(upload_task)

      finalize_upload_task = (
          finalize_composite_upload_task.FinalizeCompositeUploadTask(
              expected_component_count=len(file_part_upload_tasks),
              destination_resource=self._destination_resource,
              random_prefix=random_prefix))

      return task.Output(
          additional_task_iterators=[
              file_part_upload_tasks,
              [finalize_upload_task]
          ],
          messages=None)
