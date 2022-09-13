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

import copy
import os
import textwrap

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import fast_crc32c_util as fast_crc32c
from googlecloudsdk.command_lib.storage import manifest_util
from googlecloudsdk.command_lib.storage import posix_util
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import tracker_file_util
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks import task_util
from googlecloudsdk.command_lib.storage.tasks.cp import copy_component_util
from googlecloudsdk.command_lib.storage.tasks.cp import copy_util
from googlecloudsdk.command_lib.storage.tasks.cp import download_util
from googlecloudsdk.command_lib.storage.tasks.cp import file_part_download_task
from googlecloudsdk.command_lib.storage.tasks.cp import finalize_sliced_download_task
from googlecloudsdk.command_lib.storage.tasks.rm import delete_object_task
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import platforms
from googlecloudsdk.core.util import scaled_integer


def _get_hash_check_warning_base():
  # Create the text in a function so that we can test it easily.
  google_crc32c_install_step = fast_crc32c.get_google_crc32c_install_command()
  gcloud_crc32c_install_step = 'gcloud components install gcloud-crc32c'
  return textwrap.dedent(
      """\
      This download {{}} since fast hash calculation tools
      are not installed. You can change this by running:
      \t$ {crc32c_step}
      You can also modify the "storage/check_hashes" config setting.""".format(
          crc32c_step=google_crc32c_install_step
          if google_crc32c_install_step else gcloud_crc32c_install_step))


_HASH_CHECK_WARNING_BASE = _get_hash_check_warning_base()
_NO_HASH_CHECK_WARNING = _HASH_CHECK_WARNING_BASE.format(
    'will not be validated')
_SLOW_HASH_CHECK_WARNING = _HASH_CHECK_WARNING_BASE.format('may be slow')
_NO_HASH_CHECK_ERROR = _HASH_CHECK_WARNING_BASE.format('was skipped')


def _log_or_raise_crc32c_issues(resource):
  """Informs user about non-standard hashing behavior.

  Args:
    resource (resource_reference.ObjectResource): For checking if object has
      known hash to validate against.

  Raises:
    errors.Error: gcloud storage set to fail if performance-optimized digesters
      could not be created.
  """
  if (not resource.crc32c_hash or fast_crc32c.is_fast_crc32c_available()):
    # If resource.crc32c not available, no hash will be verified.
    # If a binary crc32c libary is available, hashing behavior will be standard.
    return

  check_hashes = properties.VALUES.storage.check_hashes.Get()
  if check_hashes == properties.CheckHashes.ALWAYS.value:
    log.warning(_SLOW_HASH_CHECK_WARNING)
  elif check_hashes == properties.CheckHashes.IF_FAST_ELSE_SKIP.value:
    log.warning(_NO_HASH_CHECK_WARNING)
  elif check_hashes == properties.CheckHashes.IF_FAST_ELSE_FAIL.value:
    raise errors.Error(_NO_HASH_CHECK_ERROR)


def _should_perform_sliced_download(source_resource, destination_resource):
  """Returns True if conditions are right for a sliced download."""
  if destination_resource.storage_url.is_stream:
    # Can't write to different indices of streams.
    return False
  if (not source_resource.crc32c_hash and
      properties.VALUES.storage.check_hashes.Get() !=
      properties.CheckHashes.NEVER.value):
    # Do not perform sliced download if hash validation is not possible.
    return False

  threshold = scaled_integer.ParseInteger(
      properties.VALUES.storage.sliced_object_download_threshold.Get())
  component_size = scaled_integer.ParseInteger(
      properties.VALUES.storage.sliced_object_download_component_size.Get())
  # TODO(b/183017513): Only perform sliced downloads with parallelism.
  api_capabilities = api_factory.get_capabilities(
      source_resource.storage_url.scheme)
  return (source_resource.size and threshold != 0 and
          source_resource.size > threshold and component_size and
          cloud_api.Capability.SLICED_DOWNLOAD in api_capabilities and
          task_util.should_use_parallelism())


class FileDownloadTask(copy_util.CopyTaskWithExitHandler):
  """Represents a command operation triggering a file download."""

  def __init__(self,
               source_resource,
               destination_resource,
               delete_source=False,
               do_not_decompress=False,
               print_created_message=False,
               user_request_args=None):
    """Initializes task.

    Args:
      source_resource (ObjectResource): Must contain
        the full path of object to download, including bucket. Directories
        will not be accepted. Does not need to contain metadata.
      destination_resource (FileObjectResource|UnknownResource): Must contain
        local filesystem path to destination object. Does not need to contain
        metadata.
      delete_source (bool): If copy completes successfully, delete the source
        object afterwards.
      do_not_decompress (bool): Prevents automatically decompressing
        downloaded gzips.
      print_created_message (bool): Print a message containing the versioned
        URL of the copy result.
      user_request_args (UserRequestArgs|None): Values for RequestConfig.
    """
    super(FileDownloadTask, self).__init__(
        source_resource,
        destination_resource,
        user_request_args=user_request_args)
    self._delete_source = delete_source
    self._do_not_decompress = do_not_decompress
    self._print_created_message = print_created_message

    self._temporary_destination_resource = (
        self._get_temporary_destination_resource())

    if (self._source_resource.size and
        self._source_resource.size >= scaled_integer.ParseInteger(
            properties.VALUES.storage.resumable_threshold.Get())):
      self._strategy = cloud_api.DownloadStrategy.RESUMABLE
    else:
      self._strategy = cloud_api.DownloadStrategy.ONE_SHOT

    self.parallel_processing_key = (
        self._destination_resource.storage_url.url_string)

  def _get_temporary_destination_resource(self):
    temporary_resource = copy.deepcopy(self._destination_resource)
    temporary_resource.storage_url.object_name += (
        storage_url.TEMPORARY_FILE_SUFFIX)
    if ((properties.VALUES.storage.convert_incompatible_windows_path_characters
         .GetBool()) and platforms.OperatingSystem.Current()
        == platforms.OperatingSystem.WINDOWS):
      temporary_resource.storage_url.object_name = (
          platforms.MakePathWindowsCompatible(
              temporary_resource.storage_url.object_name))
    return temporary_resource

  def _get_sliced_download_tasks(self):
    """Creates all tasks necessary for a sliced download."""
    _log_or_raise_crc32c_issues(self._source_resource)

    component_offsets_and_lengths = (
        copy_component_util.get_component_offsets_and_lengths(
            self._source_resource.size,
            copy_component_util.get_component_count(
                self._source_resource.size,
                properties.VALUES.storage.sliced_object_download_component_size
                .Get(),
                properties.VALUES.storage.sliced_object_download_max_components
                .GetInt())))

    download_component_task_list = []
    for i, (offset, length) in enumerate(component_offsets_and_lengths):
      download_component_task_list.append(
          file_part_download_task.FilePartDownloadTask(
              self._source_resource,
              self._temporary_destination_resource,
              offset=offset,
              length=length,
              component_number=i,
              total_components=len(component_offsets_and_lengths),
              strategy=self._strategy,
              user_request_args=self._user_request_args))

    finalize_sliced_download_task_list = [
        finalize_sliced_download_task.FinalizeSlicedDownloadTask(
            self._source_resource,
            self._temporary_destination_resource,
            self._destination_resource,
            delete_source=self._delete_source,
            do_not_decompress=self._do_not_decompress,
            user_request_args=self._user_request_args)
    ]

    return (download_component_task_list, finalize_sliced_download_task_list)

  def _restart_download(self):
    log.status.Print('Temporary download file corrupt.'
                     ' Restarting download {}'.format(self._source_resource))
    temporary_download_url = self._temporary_destination_resource.storage_url
    os.remove(temporary_download_url.object_name)
    tracker_file_util.delete_download_tracker_files(temporary_download_url)

  def execute(self, task_status_queue=None):
    """Creates appropriate download tasks."""
    destination_url = self._destination_resource.storage_url
    # We need to call os.remove here for two reasons:
    # 1. It saves on disk space during a transfer.
    # 2. Os.rename fails if a file exists at the destination. Avoiding this by
    # removing files after a download makes us susceptible to a race condition
    # between two running instances of gcloud storage. See the following PR for
    # more information: https://github.com/GoogleCloudPlatform/gsutil/pull/1202.
    if destination_url.exists():
      if self._user_request_args and self._user_request_args.no_clobber:
        log.status.Print(copy_util.get_no_clobber_message(destination_url))
        if self._send_manifest_messages:
          manifest_util.send_skip_message(
              task_status_queue, self._source_resource,
              self._destination_resource,
              copy_util.get_no_clobber_message(destination_url))
        return
      os.remove(destination_url.object_name)

    temporary_download_file_exists = (
        self._temporary_destination_resource.storage_url.exists())
    if temporary_download_file_exists and os.path.getsize(
        self._temporary_destination_resource.storage_url.object_name
    ) > self._source_resource.size:
      self._restart_download()

    if _should_perform_sliced_download(self._source_resource,
                                       self._destination_resource):
      download_component_task_list, finalize_sliced_download_task_list = (
          self._get_sliced_download_tasks())

      _, found_tracker_file = (
          tracker_file_util.read_or_create_download_tracker_file(
              self._source_resource,
              self._temporary_destination_resource.storage_url,
              total_components=len(download_component_task_list),
          ))
      if found_tracker_file:
        log.debug('Resuming sliced download with {} components.'.format(
            len(download_component_task_list)))
      else:
        if temporary_download_file_exists:
          # Component count may have changed, invalidating earlier download.
          self._restart_download()
        log.debug('Launching sliced download with {} components.'.format(
            len(download_component_task_list)))

      copy_component_util.create_file_if_needed(
          self._source_resource, self._temporary_destination_resource)

      return task.Output(
          additional_task_iterators=[
              download_component_task_list,
              finalize_sliced_download_task_list,
          ],
          messages=None)

    part_download_task_output = file_part_download_task.FilePartDownloadTask(
        self._source_resource,
        self._temporary_destination_resource,
        offset=0,
        length=self._source_resource.size,
        do_not_decompress=self._do_not_decompress,
        strategy=self._strategy,
        user_request_args=self._user_request_args,
    ).execute(task_status_queue=task_status_queue)

    temporary_file_url = self._temporary_destination_resource.storage_url
    download_util.decompress_or_rename_file(
        self._source_resource,
        temporary_file_url.object_name,
        destination_url.object_name,
        do_not_decompress_flag=self._do_not_decompress)
    # For sliced download, cleanup is done in the finalized sliced download task
    # We perform cleanup here for all other types in case some corrupt files
    # were left behind.
    tracker_file_util.delete_download_tracker_files(temporary_file_url)

    posix_util.set_posix_attributes_on_file_if_valid(
        self._user_request_args, part_download_task_output.messages,
        self._source_resource, self._destination_resource)

    if self._print_created_message:
      log.status.Print('Created: {}'.format(destination_url))
    if self._send_manifest_messages:
      manifest_util.send_success_message(
          task_status_queue,
          self._source_resource,
          self._destination_resource,
          md5_hash=task_util.get_first_matching_message_payload(
              part_download_task_output.messages, task.Topic.MD5))

    if self._delete_source:
      return task.Output(
          additional_task_iterators=[[
              delete_object_task.DeleteObjectTask(
                  self._source_resource.storage_url),
          ]],
          messages=None)
