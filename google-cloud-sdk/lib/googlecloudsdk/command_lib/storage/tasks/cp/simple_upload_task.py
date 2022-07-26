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
"""Task for uploading small files in one shot."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.command_lib.storage.tasks.cp import upload_task
from googlecloudsdk.command_lib.storage.tasks.cp import upload_util


class SimpleUploadTask(upload_task.UploadTask):
  """Uploads a file with a non-resumable strategy.

  Not suitable for composite uploads, which require resumable upload tracker
  files to correctly clean up temporary components.
  """

  def execute(self, task_status_queue=None):
    """Performs a simple upload. See base class for information on args."""
    api = api_factory.get_api(self._destination_resource.storage_url.scheme)
    request_config = request_config_factory.get_request_config(
        self._destination_resource.storage_url,
        content_type=upload_util.get_content_type(
            self._source_resource.storage_url.object_name,
            self._source_resource.storage_url.is_stream),
        md5_hash=self._source_resource.md5_hash,
        size=self._length)

    digesters = upload_util.get_digesters(
        self._source_resource,
        self._destination_resource)
    source_stream = upload_util.get_stream(
        self._source_resource,
        length=self._length,
        digesters=digesters,
        task_status_queue=task_status_queue,
        destination_resource=self._destination_resource)

    with source_stream:
      uploaded_object_resource = api.upload_object(
          source_stream,
          self._destination_resource,
          request_config,
          source_resource=self._source_resource,
          upload_strategy=cloud_api.UploadStrategy.SIMPLE)

    upload_util.validate_uploaded_object(
        digesters,
        uploaded_object_resource,
        task_status_queue)
