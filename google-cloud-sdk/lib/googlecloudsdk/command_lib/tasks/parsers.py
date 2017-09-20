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

import sys

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.tasks import app
from googlecloudsdk.command_lib.tasks import constants
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


_PROJECT = properties.VALUES.core.project.GetOrFail


def ParseLocation(location):
  return resources.REGISTRY.Parse(
      location,
      params={'projectsId': _PROJECT},
      collection=constants.LOCATIONS_COLLECTION)


def ParseQueue(queue):
  """Parses an id or uri for a queue."""
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


def ExtractLocationRefFromQueueRef(queue_ref):
  params = queue_ref.AsDict()
  del params['queuesId']
  location_ref = resources.REGISTRY.Parse(
      None, params=params, collection=constants.LOCATIONS_COLLECTION)
  return location_ref


def ParseCreateOrUpdateQueueArgs(args, queue_type, messages):
  retry_config = _ParseRetryConfigArgs(args, queue_type, messages)
  throttle_config = _ParseThrottleConfigArgs(args, queue_type, messages)
  pull_target = _ParsePullTargetArgs(args, queue_type, messages)
  app_engine_http_target = _ParseAppEngineHttpTargetArgs(args, queue_type,
                                                         messages)
  return (retry_config, throttle_config, pull_target,
          app_engine_http_target)


def _ParseRetryConfigArgs(args, queue_type, messages):
  """Parses the attributes of 'args' for Queue.retryConfig."""
  if queue_type not in constants.VALID_QUEUE_TYPES:
    return None

  retry_config = messages.RetryConfig()
  if queue_type == constants.PULL_QUEUE:
    if not any(filter(args.IsSpecified, ['max_attempts', 'task_age_limit'])):
      return None
    _AddMaxAttemptsFieldsFromArgs(args, retry_config)
    retry_config.taskAgeLimit = args.task_age_limit
  if queue_type == constants.APP_ENGINE_QUEUE:
    if not any(filter(args.IsSpecified, ['max_attempts', 'task_age_limit',
                                         'max_doublings', 'min_backoff',
                                         'max_backoff'])):
      return None
    _AddMaxAttemptsFieldsFromArgs(args, retry_config)
    retry_config.taskAgeLimit = args.task_age_limit
    retry_config.maxDoublings = args.max_doublings
    retry_config.minBackoff = args.min_backoff
    retry_config.maxBackoff = args.max_backoff
  return retry_config


def _AddMaxAttemptsFieldsFromArgs(args, config_object):
  # args.max_attempts is a BoundedInt and so None means unlimited
  if args.IsSpecified('max_attempts') and args.max_attempts is None:
    config_object.unlimitedAttempts = True
  else:
    config_object.maxAttempts = args.max_attempts


def _ParseThrottleConfigArgs(args, queue_type, messages):
  """Parses the attributes of 'args' for Queue.throttleConfig."""
  if queue_type != constants.APP_ENGINE_QUEUE:
    return None
  if not any(filter(args.IsSpecified, ['max_tasks_dispatched_per_second',
                                       'max_outstanding_tasks'])):
    return None

  throttle_config = messages.ThrottleConfig()
  throttle_config.maxTasksDispatchedPerSecond = (
      args.max_tasks_dispatched_per_second)
  throttle_config.maxOutstandingTasks = args.max_outstanding_tasks
  return throttle_config


def _ParsePullTargetArgs(unused_args, queue_type, messages):
  """Parses the attributes of 'args' for Queue.pullTarget."""
  if queue_type != constants.PULL_QUEUE:
    return None

  pull_target = messages.PullTarget()
  return pull_target


def _ParseAppEngineHttpTargetArgs(args, queue_type, messages):
  """Parses the attributes of 'args' for Queue.appEngineHttpTarget."""
  if queue_type != constants.APP_ENGINE_QUEUE:
    return None

  app_engine_http_target = messages.AppEngineHttpTarget()
  app_engine_http_target.appEngineRoutingOverride = args.routing_override
  return app_engine_http_target


def AddQueueResourceArg(parser, verb):
  base.Argument('queue', help='The queue {}.\n\n'.format(verb)).AddToParser(
      parser)


def AddQueueResourceFlag(parser, description='The queue the tasks belong to.',
                         required=True):
  argument = base.Argument('--queue', help=description, required=required)
  argument.AddToParser(parser)


def AddTaskResourceArg(parser, verb):
  base.Argument('task', help='The task {}.\n\n'.format(verb)).AddToParser(
      parser)


def AddIdArg(parser, noun, verb, metavar=None):
  metavar = metavar or '{}_ID'.format(noun.replace(' ', '_').upper())
  argument = base.Argument('id', metavar=metavar,
                           help='ID of the {} {}.\n\n'.format(noun, verb))
  argument.AddToParser(parser)


def _PullQueueFlags():
  return [
      base.Argument(
          '--max-attempts',
          type=arg_parsers.BoundedInt(1, sys.maxint, unlimited=True),
          help="""\
          The maximum number of attempts per task in the queue.
          """),
      base.Argument(
          '--task-age-limit',
          help="""\
          The time limit for retrying a failed task, measured from when the task
          was first run. If specified with `--max-attempts`, the task will be
          retried until both limits are reached. Must be a string that ends in
          's', such as "5s".
          """),
  ]


def _AppEngineQueueFlags():
  return _PullQueueFlags() + [
      base.Argument(
          '--max-tasks-dispatched-per-second',
          type=float,
          help="""\
          The maximum rate at which tasks are dispatched from this queue. This
          also determines "max burst size" for App Engine queues: if
          `--max-tasks-dispatched-per-second` is 1, then max burst size is 10;
          otherwise it is `max-tasks-dispatched-per-second` / 5.
          """),
      base.Argument(
          '--max-outstanding-tasks',
          type=int,
          help="""\
          The maximum number of outstanding tasks that Cloud Tasks allows to
          be dispatched for this queue. After this threshold has been reached,
          Cloud Tasks stops dispatching tasks until the number of outstanding
          requests decreases.
          """),
      base.Argument(
          '--max-doublings',
          type=int,
          help="""\
          The maximum number of times that the interval between failed task
          retries will be doubled before the increase becomes constant. The
          constant is: min-backoff * 2 ** (max-doublings - 1).
          """),
      base.Argument(
          '--min-backoff',
          help="""\
          The minimum amount of time to wait before retrying a task after it
          fails. Must be a string that ends in 's', such as "5s".
          """),
      base.Argument(
          '--max-backoff',
          help="""\
          The maximum amount of time to wait before retrying a task after it
          fails. Must be a string that ends in 's', such as "5s".
          """),
      base.Argument(
          '--routing-override',
          type=arg_parsers.ArgDict(key_type=_AppEngineRoutingKeysValidator,
                                   min_length=1, max_length=3,
                                   operators={':': None}),
          metavar='KEY:VALUE',
          help="""\
          If provided, the specified route is used for all tasks in the queue,
          no matter what is set is at the task-level.

          KEY must be at least one of: [{}]. Any missing keys will use the
          default for the app.
          """.format(', '.join(constants.APP_ENGINE_ROUTING_KEYS))),
  ]


def _AppEngineRoutingKeysValidator(key):
  if key not in constants.APP_ENGINE_ROUTING_KEYS:
    raise arg_parsers.ArgumentTypeError(
        'Only the following keys are valid for override: [{}].'.format(
            ', '.join(constants.APP_ENGINE_ROUTING_KEYS)))
  return key


def AddPullQueueFlags(parser):
  for flag in _PullQueueFlags():
    flag.AddToParser(parser)


def AddAppEngineQueueFlags(parser):
  for flag in _AppEngineQueueFlags():
    flag.AddToParser(parser)


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
