# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Task for bulk restoring soft-deleted objects."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.command_lib.storage import progress_callbacks
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.core import log


class BulkRestoreObjectsTask(task.Task):
  """Restores soft-deleted cloud storage objects."""

  def __init__(
      self,
      url,
      allow_overwrite=False,
      deleted_after_time=None,
      deleted_before_time=None,
      user_request_args=None,
  ):
    """Initializes task.

    Args:
      url (CloudUrl): URL matching objects to restore. If bucket URL, restores
        all objects in bucket. If object URL, extracts bucket and uses object
        portion of URL for `matchGlobs` API argument.
      allow_overwrite (bool): Overwrite existing live objects.
      deleted_after_time (datetime): Filter results to objects soft-deleted
        after this time. Backend will reject if used with `live_at_time`.
      deleted_before_time (datetime): Filter results to objects soft-deleted
        before this time. Backend will reject if used with `live_at_time`.
      user_request_args (UserRequestArgs|None): Contains restore settings.
    """
    super(BulkRestoreObjectsTask, self).__init__()
    self._url = url
    self._allow_overwrite = allow_overwrite
    self._deleted_after_time = deleted_after_time
    self._deleted_before_time = deleted_before_time
    self._user_request_args = user_request_args

  def execute(self, task_status_queue=None):
    log.status.Print(
        'Bulk restoring {}...'.format(self._url.versionless_url_string)
    )
    provider = self._url.scheme
    request_config = request_config_factory.get_request_config(
        self._url,
        user_request_args=self._user_request_args,
    )

    api_factory.get_api(provider).bulk_restore_objects(
        self._url,
        request_config=request_config,
        allow_overwrite=self._allow_overwrite,
        deleted_after_time=self._deleted_after_time,
        deleted_before_time=self._deleted_before_time,
    )

    if task_status_queue:
      progress_callbacks.increment_count_callback(task_status_queue)

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (
        self._url == other._url
        and self._allow_overwrite == other._allow_overwrite
        and self._deleted_after_time == other._deleted_after_time
        and self._deleted_before_time == other._deleted_before_time
        and self._user_request_args == other._user_request_args
    )
