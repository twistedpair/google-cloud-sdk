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

"""Task for copying an object around the cloud.

Typically executed in a task iterator:
googlecloudsdk.command_lib.storage.tasks.task_executor.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import threading

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.command_lib.storage import manifest_util
from googlecloudsdk.command_lib.storage import progress_callbacks
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks import task_status
from googlecloudsdk.command_lib.storage.tasks.cp import copy_util
from googlecloudsdk.command_lib.storage.tasks.rm import delete_object_task
from googlecloudsdk.core import log


class IntraCloudCopyTask(copy_util.CopyTaskWithExitHandler):
  """Represents a command operation copying an object around the cloud."""

  def __init__(self,
               source_resource,
               destination_resource,
               delete_source=False,
               print_created_message=False,
               user_request_args=None):
    """Initializes task.

    Args:
      source_resource (resource_reference.Resource): Must
        contain the full object path. Directories will not be accepted.
      destination_resource (resource_reference.Resource): Must
        contain the full object path. Directories will not be accepted.
        Existing objects at the this location will be overwritten.
      delete_source (bool): If copy completes successfully, delete the source
        object afterwards.
      print_created_message (bool): Print a message containing the versioned
        URL of the copy result.
      user_request_args (UserRequestArgs|None): Values for RequestConfig.
    """
    super(IntraCloudCopyTask, self).__init__(
        source_resource,
        destination_resource,
        user_request_args=user_request_args)

    if ((source_resource.storage_url.scheme
         != destination_resource.storage_url.scheme)
        or not isinstance(source_resource.storage_url,
                          storage_url.CloudUrl)):
      raise ValueError('IntraCloudCopyTask takes two URLs from the same cloud'
                       ' provider.')

    self._delete_source = delete_source
    self._print_created_message = print_created_message

    self.parallel_processing_key = (
        self._destination_resource.storage_url.url_string)

  def execute(self, task_status_queue=None):
    api_client = api_factory.get_api(self._source_resource.storage_url.scheme)
    if copy_util.check_for_cloud_clobber(self._user_request_args, api_client,
                                         self._destination_resource):
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

    progress_callback = progress_callbacks.FilesAndBytesProgressCallback(
        status_queue=task_status_queue,
        offset=0,
        length=self._source_resource.size,
        source_url=self._source_resource.storage_url,
        destination_url=self._destination_resource.storage_url,
        operation_name=task_status.OperationName.INTRA_CLOUD_COPYING,
        process_id=os.getpid(),
        thread_id=threading.get_ident(),
    )

    request_config = request_config_factory.get_request_config(
        self._destination_resource.storage_url,
        decryption_key_hash=self._source_resource.decryption_key_hash,
        user_request_args=self._user_request_args)
    # TODO(b/161900052): Support all of copy_object's parameters
    result_resource = api_client.copy_object(
        self._source_resource,
        self._destination_resource,
        request_config,
        progress_callback=progress_callback)

    if self._print_created_message:
      log.status.Print('Created: {}'.format(result_resource.storage_url))
    if self._send_manifest_messages:
      manifest_util.send_success_message(
          task_status_queue,
          self._source_resource,
          self._destination_resource,
          md5_hash=result_resource.md5_hash)
    if self._delete_source:
      return task.Output(
          additional_task_iterators=[[
              delete_object_task.DeleteObjectTask(
                  self._source_resource.storage_url)
          ]],
          messages=None)
