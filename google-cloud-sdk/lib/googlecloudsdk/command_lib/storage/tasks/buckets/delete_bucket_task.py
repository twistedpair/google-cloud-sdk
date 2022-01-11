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
"""Task for deleting bucket."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.command_lib.storage import progress_callbacks
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.core import log


class DeleteBucketTask(task.Task):
  """Deletes cloud storage bucket."""

  def __init__(self, url):
    """Initializes task.

    Args:
      url (storage_url.StorageUrl): Should only contain bucket. Objects will be
        ignored.
    """
    super(DeleteBucketTask, self).__init__()
    self._url = url
    self.parallel_processing_key = url.url_string

  def execute(self, task_status_queue=None):
    log.status.Print('Removing {}...'.format(self._url))
    api_client = api_factory.get_api(self._url.scheme)
    request_config = request_config_factory.get_request_config(self._url)
    try:
      api_client.delete_bucket(self._url.bucket_name, request_config)
      if task_status_queue:
        progress_callbacks.increment_count_callback(task_status_queue)
    # pylint:disable=broad-except
    except Exception as e:
      # pylint:enable=broad-except
      if 'not empty' in str(e):
        raise type(e)(
            'Bucket is not empty. To delete all objects and then delete'
            ' bucket, use: gcloud storage rm -r')
      else:
        raise

  def __eq__(self, other):
    if not isinstance(other, DeleteBucketTask):
      return NotImplemented
    return (self._url == other._url and
            self.parallel_processing_key == other.parallel_processing_key)
