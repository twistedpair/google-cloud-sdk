# -*- coding: utf-8 -*- #
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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from apitools.base.py import list_pager
from googlecloudsdk.api_lib import tasks
from googlecloudsdk.core import exceptions


class CreatingPullAndAppEngineQueueError(exceptions.InternalError):
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
             rate_limits=None, pull_target=None,
             app_engine_http_target=None):
    """Prepares and sends a Create request for creating a queue."""
    if pull_target and app_engine_http_target:
      raise CreatingPullAndAppEngineQueueError(
          'Attempting to send PullTarget and AppEngineHttpTarget '
          'simultaneously')
    queue = self.api.messages.Queue(
        name=queue_ref.RelativeName(), retryConfig=retry_config,
        rateLimits=rate_limits, pullTarget=pull_target,
        appEngineHttpTarget=app_engine_http_target)
    request = self.api.messages.CloudtasksProjectsLocationsQueuesCreateRequest(
        parent=parent_ref.RelativeName(), queue=queue)
    return self.api.queues_service.Create(request)

  def Patch(self, queue_ref, retry_config=None, rate_limits=None,
            app_engine_routing_override=None):
    """Prepares and sends a Patch request for modifying a queue."""

    if not any([retry_config, rate_limits, app_engine_routing_override]):
      raise NoFieldsSpecifiedError('Must specify at least one field to update.')

    queue = self.api.messages.Queue(name=queue_ref.RelativeName())

    updated_fields = []
    if retry_config is not None:
      queue.retryConfig = retry_config
      updated_fields.append('retryConfig')
    if rate_limits is not None:
      queue.rateLimits = rate_limits
      updated_fields.append('rateLimits')
    if app_engine_routing_override is not None:
      if _IsEmptyConfig(app_engine_routing_override):
        queue.appEngineHttpTarget = self.api.messages.AppEngineHttpTarget()
      else:
        queue.appEngineHttpTarget = self.api.messages.AppEngineHttpTarget(
            appEngineRoutingOverride=app_engine_routing_override)
      updated_fields.append('appEngineHttpTarget.appEngineRoutingOverride')
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

  def GetIamPolicy(self, queue_ref):
    request = (
        self.api.messages.CloudtasksProjectsLocationsQueuesGetIamPolicyRequest(
            resource=queue_ref.RelativeName()))
    return self.api.queues_service.GetIamPolicy(request)

  def SetIamPolicy(self, queue_ref, policy):
    request = (
        self.api.messages.CloudtasksProjectsLocationsQueuesSetIamPolicyRequest(
            resource=queue_ref.RelativeName(),
            setIamPolicyRequest=self.api.messages.SetIamPolicyRequest(
                policy=policy)))
    return self.api.queues_service.SetIamPolicy(request)


def _IsEmptyConfig(config):
  if config is None:
    return True

  config_dict = encoding.MessageToDict(config)
  return not any(config_dict.values())
