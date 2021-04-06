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
"""Task for performing final steps of sliced download.

Typically executed in a task iterator:
googlecloudsdk.command_lib.storage.tasks.task_executor.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import gzip
import os
import shutil

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import hash_util
from googlecloudsdk.command_lib.storage import tracker_file_util
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks.cp import file_part_download_task
from googlecloudsdk.command_lib.util import crc32c
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files


def _should_decompress_gzip(source_resource, destination_resource):
  """Checks if file has gzip metadata and is actually gzipped."""
  content_encoding = getattr(source_resource.metadata, 'contentEncoding', '')
  if content_encoding is None or 'gzip' not in content_encoding.split(','):
    return False
  try:
    with gzip.open(destination_resource.storage_url.object_name) as file_stream:
      file_stream.read(1)
    return True
  except OSError:
    return False


def _ungzip_file(file_path):
  """Unzips gzip file."""
  temporary_file_path = file_path + '.tmp'
  with gzip.open(file_path, 'rb') as gzipped_file:
    with files.BinaryFileWriter(
        temporary_file_path, create_path=True) as ungzipped_file:
      shutil.copyfileobj(gzipped_file, ungzipped_file)
  shutil.move(temporary_file_path, file_path)


class FinalizeSlicedDownloadTask(task.Task):
  """Performs final steps of sliced download."""

  def __init__(self, source_resource, destination_resource):
    """Initializes task.

    Args:
      source_resource (resource_reference.ObjectResource): Should contain
        object's metadata for checking content encoding.
      destination_resource (resource_reference.FileObjectResource): Must contain
        local filesystem path to downloaded object.
    """
    super(FinalizeSlicedDownloadTask, self).__init__()
    self._source_resource = source_resource
    self._destination_resource = destination_resource

  def execute(self, task_status_queue=None):
    """Validates and clean ups after sliced download."""
    # Clean up master and component tracker files.
    tracker_file_util.delete_download_tracker_files(
        self._destination_resource.storage_url,
        tracker_file_util.TrackerFileType.SLICED_DOWNLOAD)

    if (properties.VALUES.storage.check_hashes.Get() !=
        properties.CheckHashes.NEVER.value and
        self._source_resource.crc32c_hash):

      component_payloads = [
          message.payload
          for message in self.received_messages
          if message.topic == file_part_download_task.COMPONENT_CRC32C_TOPIC
      ]
      if component_payloads:
        # Returns list of payload values sorted by component number.
        sorted_component_payloads = sorted(
            component_payloads, key=lambda d: d['component_number'])

        downloaded_file_checksum = sorted_component_payloads[0][
            'crc32c_checksum']
        for i in range(1, len(sorted_component_payloads)):
          payload = sorted_component_payloads[i]
          downloaded_file_checksum = crc32c.concat_checksums(
              downloaded_file_checksum,
              payload['crc32c_checksum'],
              b_byte_count=payload['length'])

        downloaded_file_hash_object = crc32c.get_crc32c_from_checksum(
            downloaded_file_checksum)
        downloaded_file_hash_digest = crc32c.get_hash(
            downloaded_file_hash_object)

        try:
          hash_util.validate_object_hashes_match(
              self._destination_resource.storage_url,
              self._source_resource.crc32c_hash, downloaded_file_hash_digest)
        except errors.HashMismatchError:
          os.remove(self._destination_resource.storage_url.object_name)
          raise

    if _should_decompress_gzip(self._source_resource,
                               self._destination_resource):
      _ungzip_file(self._destination_resource.storage_url.object_name)
