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
from googlecloudsdk.command_lib.storage import hash_util
from googlecloudsdk.command_lib.storage import progress_callbacks
from googlecloudsdk.command_lib.storage import tracker_file_util
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks import task_status
from googlecloudsdk.command_lib.storage.tasks.cp import copy_component_util
from googlecloudsdk.command_lib.storage.tasks.cp import file_part_task
from googlecloudsdk.command_lib.util import crc32c
from googlecloudsdk.core.util import files


_READ_SIZE = 8192  # 8 KiB.
NULL_BYTE = b'\x00'


def _get_first_null_byte_index(destination_url, offset, length):
  """Checks to see how many bytes in range have already been downloaded.

  Args:
    destination_url (storage_url.FileUrl): Has path of file being downloaded.
    offset (int): For components, index to start reading bytes at.
    length (int): For components, where to stop reading bytes.

  Returns:
    Int byte count of size of partially-downloaded file. Returns 0 if file is
    an invalid size, empty, or non-existent.
  """
  if not destination_url.exists():
    return 0

  # Component is slice of larger file. Find how much of slice is downloaded.
  first_null_byte = offset
  end_of_range = offset + length
  with files.BinaryFileReader(destination_url.object_name) as file_reader:
    file_reader.seek(offset)
    while first_null_byte < end_of_range:
      data = file_reader.read(_READ_SIZE)
      if not data:
        break
      null_byte_index = data.find(NULL_BYTE)
      if null_byte_index != -1:
        first_null_byte += null_byte_index
        break
      first_null_byte += len(data)
  return first_null_byte


class FilePartDownloadTask(file_part_task.FilePartTask):
  """Downloads a byte range."""

  def __init__(self,
               source_resource,
               destination_resource,
               offset,
               length,
               component_number=None,
               total_components=None,
               strategy=cloud_api.DownloadStrategy.ONE_SHOT,
               digesters=None):
    """Initializes task.

    Args:
      source_resource (resource_reference.ObjectResource): Must contain the full
        path of object to download, including bucket. Directories will not be
        accepted. Does not need to contain metadata.
      destination_resource (resource_reference.FileObjectResource): Must contain
        local filesystem path to upload object. Does not need to contain
        metadata.
      offset (int): The index of the first byte in the upload range.
      length (int): The number of bytes in the upload range.
      component_number (int|None): If a multipart operation, indicates the
        component number.
      total_components (int|None): If a multipart operation, indicates the total
        number of components.
      strategy (cloud_api.DownloadStrategy): Determines what download
        implementation to use.
      digesters (dict|None): Determines what hash validation to do on download.
    """
    super(FilePartDownloadTask,
          self).__init__(source_resource, destination_resource, offset, length,
                         component_number, total_components)
    self._strategy = strategy
    self._digesters = digesters or {}

  def _perform_download(self, progress_callback, download_strategy, start_byte,
                        end_byte, write_mode):
    """Prepares file stream, calls API, and validates hash."""
    with files.BinaryFileWriter(
        self._destination_resource.storage_url.object_name,
        create_path=True,
        mode=write_mode) as download_stream:
      download_stream.seek(start_byte)
      provider = self._source_resource.storage_url.scheme
      # TODO(b/162264437): Support all of download_object's parameters.
      if self._source_resource.size != 0:
        api_factory.get_api(provider).download_object(
            self._source_resource,
            download_stream,
            digesters=self._digesters,
            download_strategy=download_strategy,
            progress_callback=progress_callback,
            start_byte=start_byte,
            end_byte=end_byte)
      else:
        # Trying to download a zero-sized file. Call progress_callback to
        # ensure that the file count gets updated.
        progress_callback(0)

    # CRC32C validated in FinalizeSlicedDownloadTask.
    if hash_util.HashAlgorithm.MD5 in self._digesters:
      calculated_digest = hash_util.get_base64_hash_digest_string(
          self._digesters[hash_util.HashAlgorithm.MD5])
      hash_util.validate_object_hashes_match(self._source_resource.storage_url,
                                             self._source_resource.md5_hash,
                                             calculated_digest)

  def _perform_one_shot_download(self, progress_callback):
    """Sets up a basic download based on task attributes."""
    start_byte = self._offset
    end_byte = self._offset + self._length - 1

    self._perform_download(progress_callback,
                           cloud_api.DownloadStrategy.ONE_SHOT, start_byte,
                           end_byte, files.BinaryFileWriterMode.TRUNCATE)

  def _perform_resumable_download(self, progress_callback):
    """Resume or start download that can be resumabled."""
    copy_component_util.create_file_if_needed(self._source_resource,
                                              self._destination_resource)

    destination_url = self._destination_resource.storage_url
    first_null_byte = _get_first_null_byte_index(destination_url,
                                                 self._offset, self._length)
    tracker_file_path, found_tracker_file = (
        tracker_file_util.read_or_create_download_tracker_file(
            self._source_resource, destination_url))
    start_byte = first_null_byte if found_tracker_file else 0
    end_byte = self._source_resource.size - 1

    if start_byte:
      write_mode = files.BinaryFileWriterMode.MODIFY
      with files.BinaryFileReader(destination_url.object_name) as file_reader:
        # Get hash of partially-downloaded file as start for validation.
        for hash_algorithm in self._digesters:
          self._digesters[hash_algorithm] = hash_util.get_hash_from_file_stream(
              file_reader, hash_algorithm, start=0, stop=start_byte)
    else:
      # TRUNCATE can create new file unlike MODIFY.
      write_mode = files.BinaryFileWriterMode.TRUNCATE

    self._perform_download(progress_callback,
                           cloud_api.DownloadStrategy.RESUMABLE, start_byte,
                           end_byte, write_mode)
    tracker_file_util.delete_tracker_file(tracker_file_path)

  def _perform_component_download(self, progress_callback):
    """Component download does not validate hash or delete tracker."""
    destination_url = self._destination_resource.storage_url
    first_null_byte = _get_first_null_byte_index(
        destination_url,
        offset=self._offset,
        length=self._length)

    _, found_tracker_file = (
        tracker_file_util.read_or_create_download_tracker_file(
            self._source_resource,
            destination_url,
            slice_start_byte=self._offset,
            component_number=self._component_number))
    start_byte = first_null_byte if found_tracker_file else self._offset
    end_byte = self._offset + self._length - 1

    if start_byte >= self._source_resource.size:
      # Component has already been downloaded.
      return

    self._perform_download(progress_callback,
                           cloud_api.DownloadStrategy.RESUMABLE, start_byte,
                           end_byte, files.BinaryFileWriterMode.MODIFY)

    if hash_util.HashAlgorithm.CRC32C in self._digesters:
      return task.Output(
          additional_task_iterators=None,
          messages=[
              task.Message(
                  topic=task.Topic.CRC32C,
                  payload={
                      'component_number':
                          self._component_number,
                      'crc32c_checksum':
                          crc32c.get_checksum(
                              self._digesters[hash_util.HashAlgorithm.CRC32C]),
                      'length':
                          self._length,
                  })
          ])

  def execute(self, task_status_queue=None):
    """Performs download."""
    progress_callback = progress_callbacks.FilesAndBytesProgressCallback(
        status_queue=task_status_queue,
        offset=self._offset,
        length=self._length,
        source_url=self._source_resource.storage_url,
        destination_url=self._destination_resource.storage_url,
        component_number=self._component_number,
        total_components=self._total_components,
        operation_name=task_status.OperationName.DOWNLOADING,
        process_id=os.getpid(),
        thread_id=threading.get_ident(),
    )

    if self._source_resource.size and self._component_number is not None:
      try:
        return self._perform_component_download(progress_callback)
      # pylint:disable=broad-except
      except Exception as e:
        # pylint:enable=broad-except
        return task.Output(
            additional_task_iterators=None,
            messages=[task.Message(topic=task.Topic.ERROR, payload=e)])

    if self._strategy is cloud_api.DownloadStrategy.RESUMABLE:
      self._perform_resumable_download(progress_callback)
    else:
      self._perform_one_shot_download(progress_callback)
