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


def _ungzip_file(gzipped_path, destination_path):
  """Unzips gzip file."""
  with gzip.open(gzipped_path, 'rb') as gzipped_file:
    with files.BinaryFileWriter(
        destination_path, create_path=True) as ungzipped_file:
      shutil.copyfileobj(gzipped_file, ungzipped_file)
  os.remove(gzipped_path)


class FinalizeSlicedDownloadTask(task.Task):
  """Performs final steps of sliced download."""

  def __init__(self, source_resource, temporary_destination_resource,
               final_destination_resource):
    """Initializes task.

    Args:
      source_resource (resource_reference.ObjectResource): Should contain
        object's metadata for checking content encoding.
      temporary_destination_resource (resource_reference.FileObjectResource):
        Must contain a local path to the temporary file written to during
        transfers.
      final_destination_resource (resource_reference.FileObjectResource): Must
        contain local filesystem path to the final download destination.
    """
    super(FinalizeSlicedDownloadTask, self).__init__()
    self._source_resource = source_resource
    self._temporary_destination_resource = temporary_destination_resource
    self._final_destination_resource = final_destination_resource

  def _clean_up_tracker_files(self):
    """Clean up master and component tracker files."""
    tracker_file_util.delete_download_tracker_files(
        self._temporary_destination_resource.storage_url,
        tracker_file_util.TrackerFileType.SLICED_DOWNLOAD)

  def execute(self, task_status_queue=None):
    """Validates and clean ups after sliced download."""
    if (properties.VALUES.storage.check_hashes.Get() !=
        properties.CheckHashes.NEVER.value and
        self._source_resource.crc32c_hash):

      component_payloads = [
          message.payload
          for message in self.received_messages
          if message.topic == task.Topic.CRC32C
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
              self._temporary_destination_resource.storage_url,
              self._source_resource.crc32c_hash, downloaded_file_hash_digest)
        except errors.HashMismatchError:
          if task.Topic.ERROR not in [
              message.topic for message in self.received_messages
          ]:
            os.remove(
                self._temporary_destination_resource.storage_url.object_name)
            self._clean_up_tracker_files()
          raise

    temporary_url = self._temporary_destination_resource.storage_url
    if _should_decompress_gzip(self._source_resource,
                               self._temporary_destination_resource):
      _ungzip_file(
          temporary_url.object_name,
          self._final_destination_resource.storage_url.object_name)
    elif os.path.exists(temporary_url.object_name):
      os.rename(
          temporary_url.object_name,
          self._final_destination_resource.storage_url.object_name)

    self._clean_up_tracker_files()

