# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Task for restoring a soft-deleted bucket."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.command_lib.storage import progress_callbacks
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.core import log


class RestoreBucketTask(task.Task):
  """Restores a soft-deleted cloud storage bucket."""

  def __init__(self, bucket_url):
    """Initializes task.

    Args:
      bucket_url (CloudUrl): Bucket Url to restore.
    """
    super(RestoreBucketTask, self).__init__()
    self._bucket_url = bucket_url

  def execute(self, task_status_queue=None):
    log.status.Print('Restoring {}...'.format(self._bucket_url.url_string))
    provider = self._bucket_url.scheme

    api_factory.get_api(provider).restore_bucket(self._bucket_url)

    if task_status_queue:
      progress_callbacks.increment_count_callback(task_status_queue)

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return self._bucket_url == other._bucket_url
