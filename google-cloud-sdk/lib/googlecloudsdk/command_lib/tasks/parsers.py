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
"""Utilities for parsing arguments to `gcloud tasks` commands."""

from googlecloudsdk.api_lib.tasks import tasks as tasks_api
from googlecloudsdk.command_lib.tasks import app
from googlecloudsdk.command_lib.tasks import constants
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import files


_PROJECT = properties.VALUES.core.project.GetOrFail


def ParseLocation(location):
  return resources.REGISTRY.Parse(
      location,
      params={'projectsId': _PROJECT},
      collection=constants.LOCATIONS_COLLECTION)


def ParseQueue(queue):
  """Parses an id or uri for a queue.

  Args:
    queue: An id, self-link, or relative path of a queue resource.

  Returns:
    A queue resource reference, or None if passed-in queue is Falsy.
  """
  if not queue:
    return None

  queue_ref = None
  try:
    queue_ref = resources.REGISTRY.Parse(queue,
                                         collection=constants.QUEUES_COLLECTION)
  except resources.RequiredFieldOmittedException:
    location_ref = ParseLocation(app.ResolveAppLocation())
    queue_ref = resources.REGISTRY.Parse(
        queue, params={'projectsId': location_ref.projectsId,
                       'locationsId': location_ref.locationsId},
        collection=constants.QUEUES_COLLECTION)
  return queue_ref


def ParseTask(task, queue_ref=None):
  """Parses an id or uri for a task."""
  params = queue_ref.AsDict() if queue_ref else None
  task_ref = resources.REGISTRY.Parse(task,
                                      collection=constants.TASKS_COLLECTION,
                                      params=params)
  return task_ref


def ExtractLocationRefFromQueueRef(queue_ref):
  params = queue_ref.AsDict()
  del params['queuesId']
  location_ref = resources.REGISTRY.Parse(
      None, params=params, collection=constants.LOCATIONS_COLLECTION)
  return location_ref


def ParseCreateOrUpdateQueueArgs(args, queue_type, messages):
  return messages.Queue(
      retryConfig=_ParseRetryConfigArgs(args, queue_type, messages),
      throttleConfig=_ParseThrottleConfigArgs(args, queue_type, messages),
      pullTarget=_ParsePullTargetArgs(args, queue_type, messages),
      appEngineHttpTarget=_ParseAppEngineHttpTargetArgs(args, queue_type,
                                                        messages))


def ParseCreateTaskArgs(args, task_type, messages):
  return messages.Task(
      scheduleTime=args.schedule_time,
      pullMessage=_ParsePullMessageArgs(args, task_type, messages),
      appEngineHttpRequest=_ParseAppEngineHttpRequestArgs(args, task_type,
                                                          messages))


def _AnyArgsSpecified(specified_args_object, args_list):
  return any(filter(specified_args_object.IsSpecified, args_list))


def _ParseRetryConfigArgs(args, queue_type, messages):
  """Parses the attributes of 'args' for Queue.retryConfig."""
  if (queue_type == constants.PULL_QUEUE and
      _AnyArgsSpecified(args, ['max_attempts', 'task_age_limit'])):
    retry_config = messages.RetryConfig(taskAgeLimit=args.task_age_limit)
    _AddMaxAttemptsFieldsFromArgs(args, retry_config)
    return retry_config

  if (queue_type == constants.APP_ENGINE_QUEUE and
      _AnyArgsSpecified(args, ['task_age_limit', 'max_doublings',
                               'min_backoff', 'max_backoff'])):
    retry_config = messages.RetryConfig(taskAgeLimit=args.task_age_limit,
                                        maxDoublings=args.max_doublings,
                                        minBackoff=args.min_backoff,
                                        maxBackoff=args.max_backoff)
    _AddMaxAttemptsFieldsFromArgs(args, retry_config)
    return retry_config


def _AddMaxAttemptsFieldsFromArgs(args, config_object):
  # args.max_attempts is a BoundedInt and so None means unlimited
  if args.IsSpecified('max_attempts') and args.max_attempts is None:
    config_object.unlimitedAttempts = True
  else:
    config_object.maxAttempts = args.max_attempts


def _ParseThrottleConfigArgs(args, queue_type, messages):
  """Parses the attributes of 'args' for Queue.throttleConfig."""
  if (queue_type == constants.APP_ENGINE_QUEUE and
      _AnyArgsSpecified(args, ['max_tasks_dispatched_per_second',
                               'max_outstanding_tasks'])):
    return messages.ThrottleConfig(
        maxTasksDispatchedPerSecond=args.max_tasks_dispatched_per_second,
        maxOutstandingTasks=args.max_outstanding_tasks)


def _ParsePullTargetArgs(unused_args, queue_type, messages):
  """Parses the attributes of 'args' for Queue.pullTarget."""
  if queue_type == constants.PULL_QUEUE:
    return messages.PullTarget()


def _ParseAppEngineHttpTargetArgs(args, queue_type, messages):
  """Parses the attributes of 'args' for Queue.appEngineHttpTarget."""
  if queue_type == constants.APP_ENGINE_QUEUE:
    routing_override = (messages.AppEngineRouting(**args.routing_override)
                        if args.routing_override else None)
    return messages.AppEngineHttpTarget(
        appEngineRoutingOverride=routing_override)


def _ParsePullMessageArgs(args, task_type, messages):
  if task_type == constants.PULL_QUEUE:
    return messages.PullMessage(payload=_ParsePayloadArgs(args), tag=args.tag)


def _ParseAppEngineHttpRequestArgs(args, task_type, messages):
  """Parses the attributes of 'args' for Task.appEngineHttpRequest."""
  if task_type == constants.APP_ENGINE_QUEUE:
    routing = (
        messages.AppEngineRouting(**args.routing) if args.routing else None)
    http_method = (messages.AppEngineHttpRequest.HttpMethodValueValuesEnum(
        args.method.upper()) if args.IsSpecified('method') else None)
    return messages.AppEngineHttpRequest(
        appEngineRouting=routing, headers=_ParseHeaderArg(args, messages),
        httpMethod=http_method, payload=_ParsePayloadArgs(args),
        relativeUrl=args.url)


def _ParsePayloadArgs(args):
  if args.IsSpecified('payload_file'):
    return files.GetFileOrStdinContents(args.payload_file, binary=False)
  elif args.IsSpecified('payload_content'):
    return args.payload_content


def _ParseHeaderArg(args, messages):
  if args.header:
    header_tuples = map(_SplitHeaderArgValue, args.header)
    headers_dicts = [{h[0]: h[1]} for h in header_tuples]
    return tasks_api.ConstructHeadersValueMessageFromListOfDicts(
        headers_dicts, messages)


def _SplitHeaderArgValue(header_arg_value):
  key, value = header_arg_value.split(':', 1)
  return key, value.lstrip()


def FormatLeaseDuration(lease_duration):
  return '{}s'.format(lease_duration)


def QueuesUriFunc(queue):
  return resources.REGISTRY.Parse(
      queue.name,
      params={'projectsId': _PROJECT},
      collection=constants.QUEUES_COLLECTION).SelfLink()


def TasksUriFunc(task):
  return resources.REGISTRY.Parse(
      task.name,
      params={'projectsId': _PROJECT},
      collection=constants.QUEUES_COLLECTION).SelfLink()
