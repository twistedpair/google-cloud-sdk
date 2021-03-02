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
"""This file provides the implementation of the `functions deploy` command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.api_lib.functions.v2 import exceptions
from googlecloudsdk.api_lib.functions.v2 import util as api_util
from googlecloudsdk.core import properties

SOURCE_REGEX = re.compile('gs://([^/]+)/(.*)')
SOURCE_ERROR_MESSAGE = """
    For now, Cloud Functions v2 only supports deploying from a Cloud
    Storage bucket. You must provide a `--source` that begins with
    `gs://`."""


def _GetProject():
  """Determine the user's project."""
  return properties.VALUES.core.project.Get(required=True)


def _GetSource(source_arg):
  """Parse the source bucket and object from the --source flag."""
  if not source_arg:
    raise exceptions.FunctionsError(SOURCE_ERROR_MESSAGE)

  source_match = SOURCE_REGEX.match(source_arg)
  if not source_match:
    raise exceptions.FunctionsError(SOURCE_ERROR_MESSAGE)

  return (source_match.group(1), source_match.group(2))


def _GetServiceConfig(args, messages):
  """Construct a ServiceConfig message from the command-line arguments."""
  service_config = messages.ServiceConfig()
  if args.memory:
    service_config.availableMemoryMb = utils.BytesToMb(args.memory)
  if args.IsSpecified('max_instances') or args.IsSpecified(
      'clear_max_instances'):
    max_instances = 0 if args.clear_max_instances else args.max_instances
    service_config.maxInstanceCount = max_instances
  service_config.serviceAccountEmail = args.run_service_account
  if args.timeout:
    service_config.timeoutSeconds = args.timeout
  return service_config


def _GetEventTrigger(args, messages):
  """Construct an EventTrigger message from the command-line arguments."""
  event_trigger = None

  if args.trigger_event_filters:
    event_trigger = messages.EventTrigger(
        serviceAccountEmail=args.trigger_service_account,
        triggerRegion=args.trigger_location,
        pubsubTopic=args.trigger_topic)

    for trigger_event_filter in args.trigger_event_filters:
      attribute, value = trigger_event_filter.split('=', 1)
      if attribute == 'type':
        event_trigger.eventType = value
      else:
        event_trigger.eventFilters.append(
            messages.EventFilter(attribute=attribute, value=value))

  return event_trigger


def _GetWorkerPool(args):
  """Return the appropriate worker pool, if any."""
  worker_pool = None
  if args.build_worker_pool or args.clear_build_worker_pool:
    worker_pool = (''
                   if args.clear_build_worker_pool else args.build_worker_pool)
  return worker_pool


def Run(args, release_track):
  """Run a function deployment with the given args."""
  client = api_util.GetClientInstance(release_track=release_track)
  messages = api_util.GetMessagesModule(release_track=release_track)

  function_ref = args.CONCEPTS.name.Parse()

  source_bucket, source_object = _GetSource(args.source)

  function = messages.Function(
      name=function_ref.RelativeName(),
      buildConfig=messages.BuildConfig(
          entryPoint=args.entry_point,
          runtime=args.runtime,
          source=messages.Source(
              storageSource=messages.StorageSource(
                  bucket=source_bucket, object=source_object)),
          workerPool=_GetWorkerPool(args)),
      eventTrigger=_GetEventTrigger(args, messages),
      serviceConfig=_GetServiceConfig(args, messages))

  create_request = messages.CloudfunctionsProjectsLocationsFunctionsCreateRequest(
      parent='projects/%s/locations/%s' % (_GetProject(), args.region),
      functionId=function_ref.Name(),
      function=function)

  operation = client.projects_locations_functions.Create(create_request)

  api_util.WaitForOperation(client, messages, operation,
                            'Deploying function (may take a while)')
