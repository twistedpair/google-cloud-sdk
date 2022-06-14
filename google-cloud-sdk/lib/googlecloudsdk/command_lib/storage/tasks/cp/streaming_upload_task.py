# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Task for streaming uploads."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks.cp import upload_util
from googlecloudsdk.core import log


class StreamingUploadTask(task.Task):
  """Represents a command operation triggering a streaming upload."""

  def __init__(self,
               source_resource,
               destination_resource,
               print_created_message=False,
               user_request_args=None):
    """Initializes task.

    Args:
      source_resource (FileObjectResource): Points to the stream or named pipe
          to read from.
      destination_resource (UnknownResource|ObjectResource): The full path of
          object to upload to.
      print_created_message (bool): Print the versioned URL of each successfully
          copied object.
      user_request_args (UserRequestArgs|None): Values for RequestConfig.
    """
    super(__class__, self).__init__()
    self._source_resource = source_resource
    self._destination_resource = destination_resource
    self._print_created_message = print_created_message
    self._user_request_args = user_request_args

  def execute(self, task_status_queue=None):
    """Runs upload from stream."""
    digesters = upload_util.get_digesters(
        self._source_resource,
        self._destination_resource)
    stream = upload_util.get_stream(
        self._source_resource,
        digesters=digesters,
        task_status_queue=task_status_queue,
        destination_resource=self._destination_resource)

    request_config = request_config_factory.get_request_config(
        self._destination_resource.storage_url,
        content_type=upload_util.get_content_type(
            self._source_resource.storage_url.object_name, is_pipe=True),
        md5_hash=self._source_resource.md5_hash,
        user_request_args=self._user_request_args)

    with stream:
      provider = self._destination_resource.storage_url.scheme
      uploaded_object_resource = api_factory.get_api(provider).upload_object(
          source_stream=stream,
          destination_resource=self._destination_resource,
          request_config=request_config,
          source_resource=self._source_resource,
          upload_strategy=cloud_api.UploadStrategy.STREAMING)

    upload_util.validate_uploaded_object(
        digesters,
        uploaded_object_resource,
        task_status_queue)

    if self._print_created_message:
      log.status.Print('Created: {}'.format(
          uploaded_object_resource.storage_url))
