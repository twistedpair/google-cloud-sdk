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
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.core import log


class DeleteBucketTask(task.Task):
  """Deletes cloud storage bucket."""

  def __init__(self, url, ignore_error=False):
    """Initializes task.

    Args:
      url (storage_url.StorageUrl): Should only contain bucket. Objects will be
        ignored.
      ignore_error (bool): Do not raise errors if there is an issue deleting the
        bucket.
    """
    super().__init__()
    self._url = url
    self._ignore_error = ignore_error

  def execute(self, task_status_queue=None):
    log.status.Print('Removing {}...'.format(self._url))
    api_client = api_factory.get_api(self._url.scheme)

    try:
      api_client.delete_bucket(self._url.bucket_name)
    # pylint:disable=broad-except
    except Exception:
      # pylint:enable=broad-except
      if not self._ignore_error:
        raise
