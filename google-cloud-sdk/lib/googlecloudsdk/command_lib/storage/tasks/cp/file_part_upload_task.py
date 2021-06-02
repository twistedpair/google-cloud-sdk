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

import collections
import contextlib
import os
import threading

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import file_part
from googlecloudsdk.command_lib.storage import hash_util
from googlecloudsdk.command_lib.storage import progress_callbacks
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks import task_status
from googlecloudsdk.command_lib.storage.tasks.cp import file_part_task
from googlecloudsdk.command_lib.storage.tasks.rm import delete_object_task
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import scaled_integer


UploadedComponent = collections.namedtuple(
    'UploadedComponent',
    ['component_number', 'object_resource']
)


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

  def _should_do_resumable_upload(self, api):
    resumable_threshold = scaled_integer.ParseInteger(
        properties.VALUES.storage.resumable_threshold.Get())
    return (
        self._length >= resumable_threshold and
        cloud_api.Capability.RESUMABLE_UPLOAD in api.capabilities
    )

  def _get_progress_callback(self, task_status_queue):
    if task_status_queue:
      return progress_callbacks.FilesAndBytesProgressCallback(
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

  @contextlib.contextmanager
  def _progress_reporting_stream(self, digesters, task_status_queue):
    progress_callback = self._get_progress_callback(task_status_queue)
    source_stream = files.BinaryFileReader(
        self._source_resource.storage_url.object_name)
    wrapped_stream = file_part.FilePart(
        source_stream, self._offset, self._length, digesters=digesters,
        progress_callback=progress_callback)

    try:
      yield wrapped_stream
    finally:
      wrapped_stream.close()

  def _get_digesters(self):
    provider = self._destination_resource.storage_url.scheme
    check_hashes = properties.CheckHashes(
        properties.VALUES.storage.check_hashes.Get())

    if (self._source_resource.md5_hash or
        # Boto3 implements its own unskippable validation.
        provider == storage_url.ProviderPrefix.S3 or
        check_hashes == properties.CheckHashes.NEVER):
      return {}
    return {hash_util.HashAlgorithm.MD5: hash_util.get_md5()}

  def _validate_uploaded_object(self, digesters, destination_resource,
                                task_status_queue):
    if not digesters:
      return
    calculated_digest = hash_util.get_base64_hash_digest_string(
        digesters[hash_util.HashAlgorithm.MD5])
    try:
      hash_util.validate_object_hashes_match(
          self._source_resource.storage_url, calculated_digest,
          destination_resource.md5_hash)
    except errors.HashMismatchError:
      delete_object_task.DeleteObjectTask(
          destination_resource.storage_url).execute(
              task_status_queue=task_status_queue)
      raise

  def execute(self, task_status_queue=None):
    """Performs upload."""
    digesters = self._get_digesters()
    provider = self._destination_resource.storage_url.scheme
    api = api_factory.get_api(provider)
    request_config = cloud_api.RequestConfig(
        md5_hash=self._source_resource.md5_hash, size=self._length)

    with self._progress_reporting_stream(digesters,
                                         task_status_queue) as upload_stream:
      if self._should_do_resumable_upload(api):
        destination_resource = api.upload_object(
            upload_stream,
            self._destination_resource,
            request_config=request_config,
            upload_strategy=cloud_api.UploadStrategy.RESUMABLE)
      else:
        destination_resource = api.upload_object(
            upload_stream,
            self._destination_resource,
            request_config=request_config,
            upload_strategy=cloud_api.UploadStrategy.SIMPLE)

      self._validate_uploaded_object(
          digesters, destination_resource, task_status_queue)

    if self._component_number is not None:
      return task.Output(
          additional_task_iterators=None,
          messages=[
              task.Message(
                  topic=task.Topic.UPLOADED_COMPONENT,
                  payload=UploadedComponent(
                      component_number=self._component_number,
                      object_resource=destination_resource)),
          ])
