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

"""Task for file uploads.

Typically executed in a task iterator:
googlecloudsdk.command_lib.storage.tasks.task_executor.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import random

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.command_lib.storage import gzip_util
from googlecloudsdk.command_lib.storage import manifest_util
from googlecloudsdk.command_lib.storage import tracker_file_util
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks import task_util
from googlecloudsdk.command_lib.storage.tasks.cp import copy_component_util
from googlecloudsdk.command_lib.storage.tasks.cp import copy_util
from googlecloudsdk.command_lib.storage.tasks.cp import file_part_upload_task
from googlecloudsdk.command_lib.storage.tasks.cp import finalize_composite_upload_task
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


def _get_random_prefix():
  """Returns an ID distinguishing upload components from different machines."""
  return str(random.randint(1, 10**10))


class FileUploadTask(copy_util.CopyTaskWithExitHandler):
  """Represents a command operation triggering a file upload."""

  def __init__(
      self,
      source_resource,
      destination_resource,
      delete_source=False,
      is_composite_upload_eligible=False,
      print_created_message=False,
      print_source_version=False,
      user_request_args=None,
      verbose=False,
  ):
    """Initializes task.

    Args:
      source_resource (resource_reference.FileObjectResource): Must contain
        local filesystem path to upload object. Does not need to contain
        metadata.
      destination_resource (resource_reference.ObjectResource|UnknownResource):
        Must contain the full object path. Directories will not be accepted.
        Existing objects at the this location will be overwritten.
      delete_source (bool): If copy completes successfully, delete the source
        object afterwards.
      is_composite_upload_eligible (bool): If True, parallel composite upload
        may be performed.
      print_created_message (bool): Print a message containing the versioned URL
        of the copy result.
      print_source_version (bool): Print source object version in status message
        enabled by the `verbose` kwarg.
      user_request_args (UserRequestArgs|None): Values for RequestConfig.
      verbose (bool): Print a "copying" status message on initialization.
    """
    super(FileUploadTask, self).__init__(
        source_resource,
        destination_resource,
        print_source_version=print_source_version,
        user_request_args=user_request_args,
        verbose=verbose,
    )
    self._delete_source = delete_source
    self._is_composite_upload_eligible = is_composite_upload_eligible
    self._print_created_message = print_created_message

    self.parallel_processing_key = (
        self._destination_resource.storage_url.url_string)

  def execute(self, task_status_queue=None):
    destination_provider = self._destination_resource.storage_url.scheme
    api_client = api_factory.get_api(destination_provider)
    if copy_util.check_for_cloud_clobber(
        self._user_request_args, api_client, self._destination_resource):
      log.status.Print(
          copy_util.get_no_clobber_message(
              self._destination_resource.storage_url))
      if self._send_manifest_messages:
        manifest_util.send_skip_message(
            task_status_queue, self._source_resource,
            self._destination_resource,
            copy_util.get_no_clobber_message(
                self._destination_resource.storage_url))
      return

    source_url = self._source_resource.storage_url
    original_source_path = source_url.object_name
    should_gzip_locally = gzip_util.should_gzip_locally(
        getattr(self._user_request_args, 'gzip_settings', None),
        original_source_path)

    if source_url.is_stream:
      size = None
      source_path = original_source_path
    else:
      if should_gzip_locally:
        source_path = gzip_util.get_temporary_gzipped_file(original_source_path)
      else:
        source_path = original_source_path
      size = os.path.getsize(source_path)

    component_count = copy_component_util.get_component_count(
        size,
        properties.VALUES.storage.parallel_composite_upload_component_size.Get(
        ),
        api_client.MAX_OBJECTS_PER_COMPOSE_CALL)
    should_perform_single_transfer = (
        not self._is_composite_upload_eligible or
        not task_util.should_use_parallelism() or component_count <= 1)

    if should_perform_single_transfer:
      task_output = file_part_upload_task.FilePartUploadTask(
          self._source_resource,
          self._destination_resource,
          source_path,
          offset=0,
          length=size,
          user_request_args=self._user_request_args).execute(task_status_queue)
      result_resource = task_util.get_first_matching_message_payload(
          task_output.messages, task.Topic.CREATED_RESOURCE)
      if result_resource:
        if self._print_created_message:
          log.status.Print('Created: {}'.format(result_resource.storage_url))
        if self._send_manifest_messages:
          manifest_util.send_success_message(
              task_status_queue,
              self._source_resource,
              self._destination_resource,
              md5_hash=result_resource.md5_hash)

      if should_gzip_locally:
        # Delete temporary gzipped version of source file.
        os.remove(source_path)
      if self._delete_source:
        # Delete original source file.
        os.remove(self._source_resource.storage_url.object_name)
    else:
      component_offsets_and_lengths = (
          copy_component_util.get_component_offsets_and_lengths(
              size, component_count))

      tracker_file_path = tracker_file_util.get_tracker_file_path(
          self._destination_resource.storage_url,
          tracker_file_util.TrackerFileType.PARALLEL_UPLOAD,
          source_url=source_url)
      tracker_data = tracker_file_util.read_composite_upload_tracker_file(
          tracker_file_path)

      if tracker_data:
        random_prefix = tracker_data.random_prefix
      else:
        random_prefix = _get_random_prefix()

      tracker_file_util.write_composite_upload_tracker_file(
          tracker_file_path, random_prefix)

      file_part_upload_tasks = []
      for i, (offset, length) in enumerate(component_offsets_and_lengths):

        temporary_component_resource = (
            copy_component_util.get_temporary_component_resource(
                self._source_resource, self._destination_resource,
                random_prefix, i))

        upload_task = file_part_upload_task.FilePartUploadTask(
            self._source_resource,
            temporary_component_resource,
            source_path,
            offset,
            length,
            component_number=i,
            total_components=len(component_offsets_and_lengths),
            user_request_args=self._user_request_args)

        file_part_upload_tasks.append(upload_task)

      finalize_upload_task = (
          finalize_composite_upload_task.FinalizeCompositeUploadTask(
              expected_component_count=len(file_part_upload_tasks),
              source_resource=self._source_resource,
              destination_resource=self._destination_resource,
              source_path=source_path,
              random_prefix=random_prefix,
              delete_source=self._delete_source,
              print_created_message=self._print_created_message,
              user_request_args=self._user_request_args))

      return task.Output(
          additional_task_iterators=[
              file_part_upload_tasks,
              [finalize_upload_task]
          ],
          messages=None)
