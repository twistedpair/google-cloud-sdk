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
"""General utilities for copies."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import errors
from googlecloudsdk.command_lib.storage import manifest_util


class CopyTaskExitHandlerMixin:
  """Mixin that overrides exit handler to copy tasks."""

  def exit_handler(self, error=None, task_status_queue=None):
    """Send copy result info to manifest if requested."""
    if not (getattr(self, '_source_resource', None) and
            getattr(self, '_destination_resource', None)):
      raise KeyError(
          self.__class__.__name__ +
          ' requires attributes "_source_resource" and "_destination_resource".'
      )

    if getattr(
        getattr(self, '_user_request_args', None), 'manifest_path', None):
      if not task_status_queue:
        raise ValueError(
            'Tried to send message to manifest, but'
            ' CopyTaskExitHandlerMixin did not receive task_status_queue.')
      if error:
        manifest_util.send_error_message(task_status_queue,
                                         self._source_resource,
                                         self._destination_resource, error)
      else:
        manifest_util.send_success_message(task_status_queue,
                                           self._source_resource,
                                           self._destination_resource)


def get_no_clobber_message(destination_url):
  """Returns standardized no clobber warning."""
  return 'Skipping existing destination item (no-clobber): {}'.format(
      destination_url)


def check_for_cloud_clobber(user_request_args, api_client,
                            destination_resource):
  """Returns if cloud destination object exists if no-clobber enabled."""
  if not (user_request_args and user_request_args.no_clobber):
    return False
  try:
    api_client.get_object_metadata(
        destination_resource.storage_url.bucket_name,
        destination_resource.storage_url.object_name,
        fields_scope=cloud_api.FieldsScope.SHORT)
  except errors.NotFoundError:
    return False
  return True


def get_generation_match_value(request_config):
  """Prioritizes user-input generation over no-clobber zero value."""
  if request_config.precondition_generation_match is not None:
    return request_config.precondition_generation_match
  if request_config.no_clobber:
    return 0
  return None
