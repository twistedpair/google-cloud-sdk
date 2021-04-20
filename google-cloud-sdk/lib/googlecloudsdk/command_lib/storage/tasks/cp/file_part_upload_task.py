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
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import file_part
from googlecloudsdk.command_lib.storage import hash_util
from googlecloudsdk.command_lib.storage import progress_callbacks
from googlecloudsdk.command_lib.storage.tasks import task_status
from googlecloudsdk.command_lib.storage.tasks.cp import file_part_task
from googlecloudsdk.command_lib.storage.tasks.rm import delete_object_task
from googlecloudsdk.core.util import files


class FilePartUploadTask(file_part_task.FilePartTask):
  """Uploads a range of bytes from a file.

  Normally, don't docstring private attributes, but initialization parameters
  need to be more specific than parent class's.

  Attributes:
    _source_resource (resource_reference.FileObjectResource): Must contain local
      filesystem path to upload object. Does not need to contain metadata.
    _destination_resource (resource_reference.ObjectResource|UnknownResource):
      Must contain the full object path. Directories will not be accepted.
      Existing objects at the this location will be overwritten.
    _offset (int): The index of the first byte in the upload range.
    _length (int): The number of bytes in the upload range.
    _component_number (int?): If a multipart operation, indicates the
      component number.
    _total_components (int?): If a multipart operation, indicates the total
      number of components.
  """

  def execute(self, task_status_queue=None):
    """Performs upload."""
    progress_callback = progress_callbacks.FilesAndBytesProgressCallback(
        status_queue=task_status_queue,
        offset=self._offset,
        length=self._length,
        source_url=self._source_resource.storage_url,
        destination_url=self._destination_resource.storage_url,
        component_number=self._component_number,
        total_components=self._total_components,
        operation_name=task_status.OperationName.UPLOADING,
        process_id=os.getpid(),
        thread_id=threading.get_ident(),
    )

    source_stream = files.BinaryFileReader(
        self._source_resource.storage_url.object_name)
    provider = self._destination_resource.storage_url.scheme

    digesters = {hash_util.HashAlgorithm.MD5: hash_util.get_md5()}
    with file_part.FilePart(source_stream, self._offset,
                            self._length, digesters=digesters) as upload_stream:
      destination_resource = api_factory.get_api(provider).upload_object(
          upload_stream,
          self._destination_resource,
          request_config=cloud_api.RequestConfig(
              md5_hash=self._source_resource.md5_hash, size=self._length),
          progress_callback=progress_callback)

    # TODO(b/175904829): Skip this if the hash is provided through a flag.
    calculated_digest = hash_util.get_base64_hash_digest_string(
        digesters[hash_util.HashAlgorithm.MD5])
    try:
      hash_util.validate_object_hashes_match(self._source_resource.storage_url,
                                             calculated_digest,
                                             destination_resource.md5_hash)
    except errors.HashMismatchError:
      delete_object_task.DeleteObjectTask(
          destination_resource.storage_url).execute(
              task_status_queue=task_status_queue)
      raise
