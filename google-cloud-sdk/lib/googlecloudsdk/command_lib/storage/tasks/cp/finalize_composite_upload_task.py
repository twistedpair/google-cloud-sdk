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
"""Contains logic for finalizing composite uploads."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage.tasks import compose_objects_task
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks.rm import delete_object_task


class FinalizeCompositeUploadTask(task.Task):
  """Composes and deletes object resources received as messages."""

  def __init__(self, expected_component_count, destination_resource):
    """Initializes task.

    Args:
      expected_component_count (int): Number of temporary components expected.
      destination_resource (resource_reference.UnknownResource): Metadata for
          the final composite object.
    """
    super().__init__()
    self._expected_component_count = expected_component_count
    self._destination_resource = destination_resource

  def execute(self, task_status_queue=None):
    uploaded_components = [
        message.payload
        for message in self.received_messages
        if message.topic == task.Topic.UPLOADED_COMPONENT
    ]

    if len(uploaded_components) != self._expected_component_count:
      raise errors.Error(
          'Temporary components were not uploaded correctly.'
          ' Please retry this upload.')

    uploaded_objects = [
        component.object_resource for component in sorted(
            uploaded_components,
            key=lambda component: component.component_number)
    ]

    compose_task = compose_objects_task.ComposeObjectsTask(
        uploaded_objects, self._destination_resource)
    compose_task.execute(task_status_queue=task_status_queue)

    delete_tasks = [
        delete_object_task.DeleteObjectTask(uploaded_object.storage_url)
        for uploaded_object in uploaded_objects
    ]
    return task.Output(additional_task_iterators=[delete_tasks], messages=None)

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (
        self._expected_component_count == other._expected_component_count
        and self._destination_resource == other._destination_resource
    )

