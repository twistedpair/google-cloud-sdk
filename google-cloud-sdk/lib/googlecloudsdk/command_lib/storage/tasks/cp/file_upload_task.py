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

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.core.util import files


class FileUploadTask(task.Task):
  """Represents a command operation triggering a file upload."""

  def __init__(self, source_resource, destination_resource):
    """Initializes task.

    Args:
      source_resource (resource_reference.FileObjectResource): Must contain
          local filesystem path to upload object. Does not need to contain
          metadata.
      destination_resource (resource_reference.Resource): Must contain
          the full object path. Directories will not be accepted. Existing
          objects at the this location will be overwritten.
    """
    super(FileUploadTask, self).__init__()
    self._source_resource = source_resource
    self._destination_resource = destination_resource

  def execute(self, callback=None):
    destination_url = self._destination_resource.storage_url
    provider = cloud_api.ProviderPrefix(destination_url.scheme)

    object_metadata = getattr(
        self._destination_resource, 'metadata_object', None)
    if not object_metadata:
      messages = core_apis.GetMessagesModule('storage', 'v1')
      object_metadata = messages.Object(bucket=destination_url.bucket_name,
                                        name=destination_url.object_name,
                                        generation=destination_url.generation)

    with files.BinaryFileReader(
        self._source_resource.storage_url.object_name) as upload_stream:
      # TODO(b/162069479): Support all of UploadObject's parameters.
      api_factory.get_api(provider).UploadObject(upload_stream, object_metadata)
