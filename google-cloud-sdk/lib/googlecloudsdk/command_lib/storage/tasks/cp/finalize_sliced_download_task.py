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

    if (properties.VALUES.storage.check_hashes.Get() != 'never' and
        self._source_resource.md5_hash):
      # Validate final product of sliced download.
      # TODO(b/181340192): See if sharing and concating task hashes is faster.
      with files.BinaryFileReader(self._destination_resource.storage_url
                                  .object_name) as downloaded_file:
        # TODO(b/172048376): Test other hash algorithms.
        downloaded_file_hash_object = hash_util.get_hash_from_file_stream(
            downloaded_file, hash_util.HashAlgorithm.MD5)

      downloaded_file_hash_digest = hash_util.get_base64_hash_digest_string(
          downloaded_file_hash_object)

      try:
        hash_util.validate_object_hashes_match(
            self._destination_resource.storage_url,
            self._source_resource.md5_hash, downloaded_file_hash_digest)
      except errors.HashMismatchError:
        os.remove(self._destination_resource.storage_url.object_name)
        raise

    if _should_decompress_gzip(self._source_resource,
                               self._destination_resource):
      _ungzip_file(self._destination_resource.storage_url.object_name)
