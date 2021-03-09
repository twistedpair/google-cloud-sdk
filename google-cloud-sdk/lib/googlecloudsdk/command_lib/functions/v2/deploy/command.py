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
from googlecloudsdk.command_lib.util.args import map_util
from googlecloudsdk.core import properties

SOURCE_REGEX = re.compile('gs://([^/]+)/(.*)')
SOURCE_ERROR_MESSAGE = """
    For now, Cloud Functions V2 only supports deploying from a Cloud
    Storage bucket. You must provide a `--source` that begins with
    `gs://`."""

LEGACY_V1_FLAGS = [
    ('security_level', '--security-level'),
    ('trigger_event', '--trigger-event'),
    ('trigger_resource', '--trigger-resource'),
]
LEGACY_V1_FLAG_ERROR = '`%s` is only supported in Cloud Functions V1.'


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
  env_var_flags = map_util.GetMapFlagsFromArgs('env-vars', args)
  env_vars = map_util.ApplyMapFlags({}, **env_var_flags)

  return messages.ServiceConfig(
      availableMemoryMb=utils.BytesToMb(args.memory) if args.memory else None,
      maxInstanceCount=args.max_instances,
      serviceAccountEmail=args.run_service_account or args.service_account,
      timeoutSeconds=args.timeout,
      environmentVariables=messages.ServiceConfig.EnvironmentVariablesValue(
          additionalProperties=[
              messages.ServiceConfig.EnvironmentVariablesValue
              .AdditionalProperty(key=key, value=value)
              for key, value in sorted(env_vars.items())
          ]))


def _GetEventTrigger(args, messages):
  """Construct an EventTrigger message from the command-line arguments."""
  event_trigger = None

  if args.trigger_event_filters:
    event_trigger = messages.EventTrigger(
        serviceAccountEmail=args.trigger_service_account or
        args.service_account,
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


def _GetBuildConfig(args, messages):
  """Construct a BuildConfig message from the command-line arguments."""
  source_bucket, source_object = _GetSource(args.source)

  build_env_var_flags = map_util.GetMapFlagsFromArgs('build-env-vars', args)
  build_env_vars = map_util.ApplyMapFlags({}, **build_env_var_flags)

  return messages.BuildConfig(
      entryPoint=args.entry_point,
      runtime=args.runtime,
      source=messages.Source(
          storageSource=messages.StorageSource(
              bucket=source_bucket, object=source_object)),
      workerPool=args.build_worker_pool,
      environmentVariables=messages.BuildConfig.EnvironmentVariablesValue(
          additionalProperties=[
              messages.BuildConfig.EnvironmentVariablesValue.AdditionalProperty(
                  key=key, value=value)
              for key, value in sorted(build_env_vars.items())
          ]))


def _ValidateLegacyV1Flags(args):
  for flag_variable, flag_name in LEGACY_V1_FLAGS:
    if args.IsSpecified(flag_variable):
      raise exceptions.FunctionsError(LEGACY_V1_FLAG_ERROR % flag_name)


def Run(args, release_track):
  """Run a function deployment with the given args."""
  client = api_util.GetClientInstance(release_track=release_track)
  messages = api_util.GetMessagesModule(release_track=release_track)

  function_ref = args.CONCEPTS.name.Parse()

  _ValidateLegacyV1Flags(args)

  function = messages.Function(
      name=function_ref.RelativeName(),
      buildConfig=_GetBuildConfig(args, messages),
      eventTrigger=_GetEventTrigger(args, messages),
      serviceConfig=_GetServiceConfig(args, messages))

  create_request = messages.CloudfunctionsProjectsLocationsFunctionsCreateRequest(
      parent='projects/%s/locations/%s' % (_GetProject(), args.region),
      functionId=function_ref.Name(),
      function=function)

  operation = client.projects_locations_functions.Create(create_request)

  api_util.WaitForOperation(client, messages, operation,
                            'Deploying function (may take a while)')
