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

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import hash_util
from googlecloudsdk.command_lib.storage import tracker_file_util
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks.cp import copy_component_util
from googlecloudsdk.command_lib.storage.tasks.cp import file_part_download_task
from googlecloudsdk.command_lib.storage.tasks.cp import finalize_sliced_download_task
from googlecloudsdk.command_lib.util import crc32c
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import scaled_integer


_NO_HASH_CHECK_ERROR = """
google-crc32c not installed, so hashing will be slow. Install google-crc32c or
change the "storage/check_hashes" config setting.
"""
_HASH_CHECK_WARNING_BASE = """
This download {} since the google-crc32c
binary is not installed, and Python hash computation will likely
throttle performance. You can change this by installing the binary or
modifying the "storage/check_hashes" config setting.
"""
_NO_HASH_CHECK_WARNING = _HASH_CHECK_WARNING_BASE.format(
    'will not be validated')
_SLOW_HASH_CHECK_WARNING = _HASH_CHECK_WARNING_BASE.format('may be slow')


def _get_digester(algorithm, resource, should_log_warning=True):
  """Returns digesters dictionary for download hash validation.

  Args:
    algorithm (hash_util.HashAlgorithm): Type of hash digester to create.
    resource (resource_reference.ObjectResource): For checking if object has
      known hash to validate against.
    should_log_warning (bool): Log a warning about potential digesters issues.

  Returns:
    Digesters dict.

  Raises:
    errors.Error: gcloud storage set to fail if performance-optimized digesters
      could not be created.
  """
  check_hashes = properties.VALUES.storage.check_hashes.Get()
  if check_hashes == properties.CheckHashes.NEVER.value:
    return {}

  digesters = {}
  if algorithm == hash_util.HashAlgorithm.MD5 and resource.md5_hash:
    digesters[hash_util.HashAlgorithm.MD5] = hash_util.get_md5()

  elif algorithm == hash_util.HashAlgorithm.CRC32C and resource.crc32c_hash:
    if (crc32c.IS_GOOGLE_CRC32C_AVAILABLE or
        check_hashes == properties.CheckHashes.ALWAYS.value):
      if should_log_warning and not crc32c.IS_GOOGLE_CRC32C_AVAILABLE:
        log.warning(_SLOW_HASH_CHECK_WARNING)

      digesters[hash_util.HashAlgorithm.CRC32C] = crc32c.get_crc32c()

    elif check_hashes == properties.CheckHashes.IF_FAST_ELSE_FAIL.value:
      raise errors.Error(_NO_HASH_CHECK_ERROR)

    elif (should_log_warning and
          check_hashes == properties.CheckHashes.IF_FAST_ELSE_SKIP.value):
      log.warning(_NO_HASH_CHECK_WARNING)

  return digesters


def _should_perform_sliced_download(resource):
  """Returns True if conditions are right for a sliced download."""
  if (not resource.crc32c_hash and properties.VALUES.storage.check_hashes.Get()
      != properties.CheckHashes.NEVER.value):
    # Do not perform sliced download if hash validation is not possible.
    return False

  threshold = scaled_integer.ParseInteger(
      properties.VALUES.storage.sliced_object_download_threshold.Get())
  component_size = scaled_integer.ParseInteger(
      properties.VALUES.storage.sliced_object_download_component_size.Get())
  # TODO(b/183017513): Only perform sliced downloads with parallelism.
  api_capabilities = api_factory.get_capabilities(resource.storage_url.scheme)
  return (resource.size and threshold != 0 and resource.size > threshold and
          component_size and
          cloud_api.Capability.SLICED_DOWNLOAD in api_capabilities)


class FileDownloadTask(task.Task):
  """Represents a command operation triggering a file download."""

  def __init__(self, source_resource, destination_resource):
    """Initializes task.

    Args:
      source_resource (ObjectResource): Must contain
        the full path of object to download, including bucket. Directories
        will not be accepted. Does not need to contain metadata.
      destination_resource (FileObjectResource|UnknownResource): Must contain
        local filesystem path to upload object. Does not need to contain
        metadata.
    """
    super(FileDownloadTask, self).__init__()
    self._source_resource = source_resource
    self._destination_resource = destination_resource
    self.parallel_processing_key = (
        self._destination_resource.storage_url.url_string)

  def _get_sliced_download_tasks(self):
    """Creates all tasks necessary for a sliced download."""
    component_offsets_and_lengths = copy_component_util.get_component_offsets_and_lengths(
        self._source_resource.size,
        properties.VALUES.storage.sliced_object_download_component_size.Get(),
        properties.VALUES.storage.sliced_object_download_max_components.GetInt(
        ))

    download_component_task_list = []
    for i, (offset, length) in enumerate(component_offsets_and_lengths):
      digesters = _get_digester(
          hash_util.HashAlgorithm.CRC32C,
          self._source_resource,
          should_log_warning=i == 0)
      download_component_task_list.append(
          file_part_download_task.FilePartDownloadTask(
              self._source_resource,
              self._destination_resource,
              offset=offset,
              length=length,
              component_number=i,
              total_components=len(component_offsets_and_lengths),
              digesters=digesters))

    finalize_sliced_download_task_list = [
        finalize_sliced_download_task.FinalizeSlicedDownloadTask(
            self._source_resource, self._destination_resource)
    ]

    return (download_component_task_list, finalize_sliced_download_task_list)

  def execute(self, task_status_queue=None):
    """Creates appropriate download tasks."""
    if _should_perform_sliced_download(self._source_resource):
      copy_component_util.create_file_if_needed(self._source_resource,
                                                self._destination_resource)
      download_component_task_list, finalize_sliced_download_task_list = self._get_sliced_download_tasks(
      )

      tracker_file_util.read_or_create_download_tracker_file(
          self._source_resource,
          self._destination_resource.storage_url,
          total_components=len(download_component_task_list),
      )
      log.debug('Launching sliced download with {} components.'.format(
          len(download_component_task_list)))
      return task.Output(
          additional_task_iterators=[
              download_component_task_list,
              finalize_sliced_download_task_list,
          ],
          messages=None)
    else:
      if (self._source_resource.size and
          self._source_resource.size >= scaled_integer.ParseInteger(
              properties.VALUES.storage.resumable_threshold.Get())):
        strategy = cloud_api.DownloadStrategy.RESUMABLE
      else:
        strategy = cloud_api.DownloadStrategy.ONE_SHOT

      digesters = _get_digester(hash_util.HashAlgorithm.MD5,
                                self._source_resource)

      file_part_download_task.FilePartDownloadTask(
          self._source_resource,
          self._destination_resource,
          offset=0,
          length=self._source_resource.size,
          strategy=strategy,
          digesters=digesters).execute(task_status_queue=task_status_queue)
