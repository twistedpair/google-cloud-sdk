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

"""Task for copying an object around the cloud.

Typically executed in a task iterator:
googlecloudsdk.command_lib.storage.tasks.task_executor.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.tasks import task


class IntraCloudCopyTask(task.Task):
  """Represents a command operation copying an object around the cloud.

  Attributes:
    source_reference (str): (resource_reference.ObjectReference): Must
        contain the full object path. Directories will not be accepted.Existing
        objects at the this location will be overwritten.
    destination_reference (resource_reference.ObjectReference): Must
        contain the full object path. Directories will not be accepted.Existing
        objects at the this location will be overwritten.
  """

  def __init__(self, source_reference, destination_reference):
    super(IntraCloudCopyTask, self).__init__()
    if ((source_reference.storage_url.scheme
         != destination_reference.storage_url.scheme)
        or not isinstance(source_reference.storage_url,
                          storage_url.CloudUrl)):
      raise ValueError('IntraCloudCopyTask takes two URLs from the same cloud'
                       ' provider.')

    self.source_reference = source_reference
    self.destination_reference = destination_reference

  def execute(self, callback=None):
    # TODO(b/161900052): Support all of CopyObject's parameters
    provider = cloud_api.ProviderPrefix(
        self.source_reference.storage_url.scheme)
    api_factory.get_api(provider).CopyObject(
        self.source_reference.metadata_object,
        self.destination_reference.metadata_object)
