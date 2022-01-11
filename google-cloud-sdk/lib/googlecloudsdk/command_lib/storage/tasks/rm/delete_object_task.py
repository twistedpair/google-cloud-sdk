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
"""Task for deleting an object."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.command_lib.storage import progress_callbacks
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.core import log


class DeleteObjectTask(task.Task):
  """Deletes an object."""

  def __init__(self, object_url, user_request_args=None, verbose=True):
    """Initializes task.

    Args:
      object_url (storage_url.CloudUrl): URL of the object to delete.
      user_request_args (UserRequestArgs|None): Values for RequestConfig.
      verbose (bool): If true, prints status messages. Otherwise, does not
          print anything.
    """
    super(DeleteObjectTask, self).__init__()
    self._object_url = object_url
    self._user_request_args = user_request_args
    self._verbose = verbose

    self.parallel_processing_key = object_url.url_string

  def execute(self, task_status_queue=None):
    provider = self._object_url.scheme
    request_config = request_config_factory.get_request_config(
        self._object_url, user_request_args=self._user_request_args)

    if self._verbose:
      log.status.Print('Removing {}...'.format(self._object_url))
    api_factory.get_api(provider).delete_object(self._object_url,
                                                request_config)
    if task_status_queue:
      progress_callbacks.increment_count_callback(task_status_queue)

  def __eq__(self, other):
    if not isinstance(other, DeleteObjectTask):
      return NotImplemented
    return (self._object_url == other._object_url and
            self._user_request_args == other._user_request_args and
            self._verbose == other._verbose)
