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

"""Task for file uploads.

Typically executed in a task iterator:
googlecloudsdk.command_lib.storage.tasks.task_executor.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import threading

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.command_lib.storage import file_part
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks import task_status
from googlecloudsdk.core.util import files


class FilePartUploadTask(task.Task):
  """Uploads a range of bytes from a file."""

  def __init__(self, source_resource, destination_resource, offset, length):
    """Initializes task.

    Args:
      source_resource (resource_reference.FileObjectResource): Must contain
          local filesystem path to upload object. Does not need to contain
          metadata.
      destination_resource (resource_reference.ObjectResource|UnknownResource):
          Must contain the full object path. Directories will not be accepted.
          Existing objects at the this location will be overwritten.
      offset (int): The index of the first byte in the upload range.
      length (int): The number of bytes in the upload range.
    """
    super().__init__()
    self._source_resource = source_resource
    self._destination_resource = destination_resource
    self._offset = offset
    self._length = length
    self.parallel_processing_key = (
        self._destination_resource.storage_url.url_string)

  def execute(self, task_status_queue=None):
    progress_callback = task_status.FilesAndBytesProgressCallback(
        status_queue=task_status_queue,
        size=self._length,
        source_url=self._source_resource.storage_url,
        destination_url=self._destination_resource.storage_url,
        operation_name=task_status.OperationName.UPLOADING,
        process_id=os.getpid(),
        thread_id=threading.get_ident(),
    )

    source_stream = files.BinaryFileReader(
        self._source_resource.storage_url.object_name)
    provider = self._destination_resource.storage_url.scheme

    with file_part.FilePart(source_stream, self._offset,
                            self._length) as upload_stream:
      api_factory.get_api(provider).upload_object(
          upload_stream,
          self._destination_resource,
          request_config=cloud_api.RequestConfig(
              md5_hash=self._source_resource.md5_hash, size=self._length),
          progress_callback=progress_callback)

  def __eq__(self, other):
    if not isinstance(other, FilePartUploadTask):
      return NotImplemented
    return (self._destination_resource == other._destination_resource and
            self._source_resource == other._source_resource and
            self._offset == other._offset and self._length == other._length)
