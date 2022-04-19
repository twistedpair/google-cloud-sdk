# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Deletes temporary components and tracker files from a composite upload."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import glob
import os

from googlecloudsdk.command_lib.storage import tracker_file_util
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks.cp import copy_component_util
from googlecloudsdk.command_lib.storage.tasks.rm import delete_object_task


class DeleteTemporaryComponentsTask(task.Task):
  """Deletes temporary components and tracker files after a composite upload."""

  def __init__(self, source_resource, destination_resource, random_prefix):
    """Initializes a task instance.

    Args:
      source_resource (resource_reference.FileObjectResource): The local,
          uploaded file.
      destination_resource (resource_reference.UnknownResource): The final
          composite object's metadata.
      random_prefix (str): ID added to temporary component names.
    """
    super(DeleteTemporaryComponentsTask, self).__init__()
    self._source_resource = source_resource
    self._destination_resource = destination_resource
    self._random_prefix = random_prefix

  def execute(self, task_status_queue=None):
    """Deletes temporary components and associated tracker files.

    Args:
      task_status_queue: See base class.

    Returns:
      A task.Output with tasks for deleting temporary components.
    """
    del task_status_queue

    component_tracker_path_prefix = tracker_file_util.get_tracker_file_path(
        copy_component_util.get_temporary_component_resource(
            self._source_resource, self._destination_resource,
            self._random_prefix, component_id='').storage_url,
        tracker_file_util.TrackerFileType.UPLOAD,
        # TODO(b/190093425): Setting component_number will not be necessary
        # after using the final destination to generate component tracker paths.
        component_number='')
    # Matches all paths, regardless of component number:
    component_tracker_paths = glob.iglob(component_tracker_path_prefix + '*')

    delete_tasks = []
    for component_tracker_path in component_tracker_paths:
      tracker_data = tracker_file_util.read_resumable_upload_tracker_file(
          component_tracker_path)
      if tracker_data.complete:
        _, _, component_number = component_tracker_path.rpartition('_')
        component_resource = (
            copy_component_util.get_temporary_component_resource(
                self._source_resource, self._destination_resource,
                self._random_prefix, component_id=component_number))

        delete_tasks.append(delete_object_task.DeleteObjectTask(
            component_resource.storage_url, verbose=False))
      os.remove(component_tracker_path)

    # TODO(b/228956264): May be able to remove after task graph improvements.
    additional_task_iterators = [delete_tasks] if delete_tasks else None
    return task.Output(
        additional_task_iterators=additional_task_iterators, messages=None)

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (
        self._source_resource == other._source_resource
        and self._destination_resource == other._destination_resource
        and self._random_prefix == other._random_prefix
    )
