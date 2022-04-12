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
"""Task for updating a bucket."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import errors
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.command_lib.artifacts import requests
from googlecloudsdk.command_lib.storage import progress_callbacks
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.core import log


class UpdateBucketTask(task.Task):
  """Updates a cloud storage bucket's metadata."""

  def __init__(self, bucket_resource, user_request_args=None):
    """Initializes task.

    Args:
      bucket_resource (resource_reference.UnknownResource):
          The bucket to update.
      user_request_args (UserRequestArgs|None): Describes metadata updates to
          perform.
    """
    super(UpdateBucketTask, self).__init__()
    self._bucket_resource = bucket_resource
    self._user_request_args = user_request_args

  def execute(self, task_status_queue=None):
    log.status.Print('Updating {}...'.format(self._bucket_resource))
    provider = self._bucket_resource.storage_url.scheme
    request_config = request_config_factory.get_request_config(
        self._bucket_resource.storage_url,
        user_request_args=self._user_request_args)

    try:
      api_factory.get_api(provider).patch_bucket(
          self._bucket_resource, request_config=request_config)
    except errors.GcsApiError as e:
      # Service agent does not have the encrypter/decrypter role.
      if (e.payload.status_code == 403 and
          request_config.resource_args.default_encryption_key):

        service_agent = api_factory.get_api(provider).get_service_agent()
        requests.AddCryptoKeyPermission(
            request_config.resource_args.default_encryption_key,
            'serviceAccount:' + service_agent)

        api_factory.get_api(provider).patch_bucket(
            self._bucket_resource, request_config=request_config)
      else:
        raise

    if task_status_queue:
      progress_callbacks.increment_count_callback(task_status_queue)
