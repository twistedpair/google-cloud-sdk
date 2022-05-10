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
"""Task for composing storage objects."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.command_lib.storage.tasks import task


class ComposeObjectsTask(task.Task):
  """Composes storage objects."""

  def __init__(self,
               source_resources,
               destination_resource,
               original_source_resource=None,
               user_request_args=None):
    """Initializes task.

    Args:
      source_resources (list[ObjectResource|UnknownResource]): The objects to
        compose. This field accepts UnknownResources since it should allow
        ComposeObjectsTasks to be initialized before the target objects have
        been created.
      destination_resource (resource_reference.UnknownResource): Metadata for
        the resulting composite object.
      original_source_resource (Resource|None): Useful for finding metadata to
        apply to final object. For instance, if doing a composite upload, this
        would represent the pre-split local file.
      user_request_args (UserRequestArgs|None): Values for RequestConfig.
    """
    super(ComposeObjectsTask, self).__init__()
    self._source_resources = source_resources
    self._destination_resource = destination_resource
    self._original_source_resource = original_source_resource
    self._user_request_args = user_request_args

  def execute(self, task_status_queue=None):
    del task_status_queue  # Unused.
    request_config = request_config_factory.get_request_config(
        self._destination_resource.storage_url,
        user_request_args=self._user_request_args)

    provider = self._destination_resource.storage_url.scheme
    created_resource = api_factory.get_api(provider).compose_objects(
        self._source_resources,
        self._destination_resource,
        request_config,
        original_source_resource=self._original_source_resource)
    return task.Output(
        messages=[
            task.Message(
                topic=task.Topic.CREATED_RESOURCE, payload=created_resource),
        ],
        additional_task_iterators=[])

  def __eq__(self, other):
    if not isinstance(other, ComposeObjectsTask):
      return NotImplemented
    return (self._source_resources == other._source_resources and
            self._destination_resource == other._destination_resource and
            self._user_request_args == other._user_request_args)
