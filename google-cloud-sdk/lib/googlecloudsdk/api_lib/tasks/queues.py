# Copyright 2017 Google Inc. All Rights Reserved.
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
"""API Library for gcloud tasks queues."""
# TODO(b/36865670): Add GetLocation, ListLocation, SetIamPolicy,
#    GetIamPolicy, and TestIamPermissions
from apitools.base.py import encoding
from apitools.base.py import list_pager
from googlecloudsdk.api_lib import tasks
from googlecloudsdk.core import exceptions


class ModifyingPullAndAppEngineQueueError(exceptions.InternalError):
  """Error for when attempt to create a queue as both pull and App Engine."""


class NoFieldsSpecifiedError(exceptions.Error):
  """Error for when calling a patch method with no fields specified."""


class Queues(object):
  """Client for queues service in the Cloud Tasks API."""

  def __init__(self, tasks_api=None):
    self.api = tasks_api or tasks.ApiAdapter()

  def Get(self, queue_ref):
    request = self.api.messages.CloudtasksProjectsLocationsQueuesGetRequest(
        name=queue_ref.RelativeName())
    return self.api.queues_service.Get(request)

  def List(self, parent_ref, limit=None, page_size=100):
    request = self.api.messages.CloudtasksProjectsLocationsQueuesListRequest(
        parent=parent_ref.RelativeName())
    return list_pager.YieldFromList(
        self.api.queues_service, request, batch_size=page_size, limit=limit,
        field='queues', batch_size_attribute='pageSize')

  def Create(self, parent_ref, queue_ref, retry_config=None,
             throttle_config=None, pull_target=None,
             app_engine_http_target=None):
    """Prepares and sends a Patch request for creating a queue."""
    if pull_target and app_engine_http_target:
      raise ModifyingPullAndAppEngineQueueError(
          'Attempting to send PullTarget and AppEngineHttpTarget '
          'simultaneously')
    queue = self.api.messages.Queue(
        name=queue_ref.RelativeName(), retryConfig=retry_config,
        throttleConfig=throttle_config, pullTarget=pull_target,
        appEngineHttpTarget=app_engine_http_target)
    request = self.api.messages.CloudtasksProjectsLocationsQueuesCreateRequest(
        parent=parent_ref.RelativeName(), queue=queue)
    return self.api.queues_service.Create(request)

  def Patch(self, queue_ref, retry_config=None, throttle_config=None,
            pull_target=None, app_engine_http_target=None):
    """Prepares and sends a Patch request for modifying a queue."""
    if pull_target and app_engine_http_target:
      raise ModifyingPullAndAppEngineQueueError(
          'Attempting to send PullTarget and AppEngineHttpTarget '
          'simultaneously')

    if _AllEmptyConfigs([retry_config, throttle_config, pull_target,
                         app_engine_http_target]):
      raise NoFieldsSpecifiedError('Must specify at least one field to update.')

    queue = self.api.messages.Queue(name=queue_ref.RelativeName())

    updated_fields = []
    if retry_config is not None:
      queue.retryConfig = retry_config
      updated_fields.append('retryConfig')
    if throttle_config is not None:
      queue.throttleConfig = throttle_config
      updated_fields.append('throttleConfig')
    if pull_target is not None:
      queue.pullTarget = pull_target
      updated_fields.append('pullTarget')
    if app_engine_http_target is not None:
      queue.appEngineHttpTarget = app_engine_http_target
      updated_fields.append('appEngineHttpTarget')
    update_mask = ','.join(updated_fields)

    request = self.api.messages.CloudtasksProjectsLocationsQueuesPatchRequest(
        name=queue_ref.RelativeName(), queue=queue, updateMask=update_mask)
    return self.api.queues_service.Patch(request)

  def Delete(self, queue_ref):
    request = self.api.messages.CloudtasksProjectsLocationsQueuesDeleteRequest(
        name=queue_ref.RelativeName())
    return self.api.queues_service.Delete(request)

  def Purge(self, queue_ref):
    request = self.api.messages.CloudtasksProjectsLocationsQueuesPurgeRequest(
        name=queue_ref.RelativeName())
    return self.api.queues_service.Purge(request)

  def Pause(self, queue_ref):
    request = self.api.messages.CloudtasksProjectsLocationsQueuesPauseRequest(
        name=queue_ref.RelativeName())
    return self.api.queues_service.Pause(request)

  def Resume(self, queue_ref):
    request = self.api.messages.CloudtasksProjectsLocationsQueuesResumeRequest(
        name=queue_ref.RelativeName())
    return self.api.queues_service.Resume(request)


def _AllEmptyConfigs(configs):
  return all(map(_IsEmptyConfig, configs))


def _IsEmptyConfig(config):
  if config is None:
    return True

  config_dict = encoding.MessageToDict(config)
  return not any(config_dict.values())


