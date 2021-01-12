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
"""Task for deleting an object."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.command_lib.storage.tasks import task


class DeleteObjectTask(task.Task):
  """Deletes an object."""

  def __init__(self, object_resource):
    """Initializes task.

    Args:
      object_resource (resource_reference.ObjectResource): The object to delete.
    """
    super().__init__()
    self._object_resource = object_resource

  def execute(self, callback=None):
    provider = self._object_resource.storage_url.scheme
    api_factory.get_api(provider).delete_object(self._object_resource)

