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

"""Task for file downloads.

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
from googlecloudsdk.command_lib.storage import progress_callbacks
from googlecloudsdk.command_lib.storage import tracker_file_util
from googlecloudsdk.command_lib.storage import util
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks import task_status
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files


def _get_valid_downloaded_byte_count(destination_url, resource):
  """Checks to see how many bytes of file have been downloaded.

  Args:
    destination_url (storage_url.FileUrl): Has path of file being downloaded.
    resource (resource_reference.ObjectResource): Has metadata of path being
      downloaded.

  Returns:
    Int byte count of size of partially-downloaded file. Returns 0 if file is
    an invalid size, empty, or non-existent.
  """
  if not destination_url.exists():
    return 0
  existing_file_size = os.path.getsize(destination_url.object_name)
  return existing_file_size if existing_file_size < resource.size else 0


class FileDownloadTask(task.Task):
  """Represents a command operation triggering a file download."""

  def __init__(self, source_resource, destination_resource):
    """Initializes task.

    Args:
      source_resource (resource_reference.ObjectResource): Must contain
          the full path of object to download, including bucket. Directories
          will not be accepted. Does not need to contain metadata.
      destination_resource (resource_reference.FileObjectResource): Must contain
          local filesystem path to upload object. Does not need to contain
          metadata.
    """
    super(FileDownloadTask, self).__init__()
    self._source_resource = source_resource
    self._destination_resource = destination_resource
    self.parallel_processing_key = (
        self._destination_resource.storage_url.url_string)

  def execute(self, task_status_queue=None):
    if self._source_resource.md5_hash:
      digesters = {util.HashAlgorithms.MD5: util.get_md5_hash()}
    else:
      digesters = {}

    progress_callback = progress_callbacks.FilesAndBytesProgressCallback(
        status_queue=task_status_queue,
        size=self._source_resource.size,
        source_url=self._source_resource.storage_url,
        destination_url=self._destination_resource.storage_url,
        operation_name=task_status.OperationName.DOWNLOADING,
        process_id=os.getpid(),
        thread_id=threading.get_ident(),
    )

    destination_url = self._destination_resource.storage_url
    if (self._source_resource.size and self._source_resource.size >=
        properties.VALUES.storage.resumable_threshold.GetInt()):
      download_strategy = cloud_api.DownloadStrategy.RESUMABLE

      existing_file_size = _get_valid_downloaded_byte_count(
          destination_url, self._source_resource)
      if existing_file_size:
        with files.BinaryFileReader(destination_url.object_name) as file_reader:
          # Get hash of partially-downloaded file as start for validation.
          for hash_algorithm in digesters:
            digesters[hash_algorithm] = util.get_hash_from_file_stream(
                file_reader, hash_algorithm)

      tracker_file_path, start_byte = (
          tracker_file_util.read_or_create_download_tracker_file(
              self._source_resource,
              destination_url,
              existing_file_size=existing_file_size))
    else:
      download_strategy = cloud_api.DownloadStrategy.ONE_SHOT
      tracker_file_path = None
      start_byte = 0

    mode = (
        files.BinaryFileWriterMode.MODIFY
        if start_byte else files.BinaryFileWriterMode.TRUNCATE)
    with files.BinaryFileWriter(
        self._destination_resource.storage_url.object_name,
        create_path=True,
        mode=mode) as download_stream:
      download_stream.seek(start_byte)
      provider = self._source_resource.storage_url.scheme
      # TODO(b/162264437): Support all of download_object's parameters.
      api_factory.get_api(provider).download_object(
          self._source_resource,
          download_stream,
          digesters=digesters,
          download_strategy=download_strategy,
          progress_callback=progress_callback,
          start_byte=start_byte)

    # TODO(b/172048376): Add crc32c, and make this a loop.
    if util.HashAlgorithms.MD5 in digesters:
      calculated_digest = util.get_base64_hash_digest_string(
          digesters[util.HashAlgorithms.MD5])
      util.validate_object_hashes_match(self._source_resource.storage_url,
                                        self._source_resource.md5_hash,
                                        calculated_digest)

    if tracker_file_path:
      tracker_file_util.delete_tracker_file(tracker_file_path)
