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

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.api_lib.functions.v2 import exceptions
from googlecloudsdk.api_lib.functions.v2 import util as api_util
from googlecloudsdk.api_lib.run import global_methods
from googlecloudsdk.command_lib.functions import flags
from googlecloudsdk.command_lib.run import connection_context
from googlecloudsdk.command_lib.run import serverless_operations
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.args import map_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io

import six

SOURCE_REGEX = re.compile('gs://([^/]+)/(.*)')
SOURCE_ERROR_MESSAGE = (
    'For now, Cloud Functions v2 only supports deploying from a Cloud '
    'Storage bucket. You must provide a `--source` that begins with '
    '`gs://`.')

INVALID_NON_HTTP_SIGNATURE_TYPE_ERROR_MESSAGE = (
    'When `--trigger_http` is provided, `--signature-type` must be omitted '
    'or set to `http`.')
INVALID_HTTP_SIGNATURE_TYPE_ERROR_MESSAGE = (
    'When an event trigger is provided, `--signature-type` cannot be set to '
    '`http`.')
SIGNATURE_TYPE_ENV_VAR_COLLISION_ERROR_MESSAGE = (
    '`GOOGLE_FUNCTION_SIGNATURE_TYPE` is a reserved build environment variable.'
)

LEGACY_V1_FLAGS = [
    ('security_level', '--security-level'),
    ('trigger_event', '--trigger-event'),
    ('trigger_resource', '--trigger-resource'),
]
LEGACY_V1_FLAG_ERROR = '`%s` is only supported in Cloud Functions V1.'

EVENT_TYPE_PUBSUB_MESSAGE_PUBLISHED = 'google.cloud.pubsub.topic.v1.messagePublished'

CLOUD_RUN_SERVICE_COLLECTION_K8S = 'run.namespaces.services'
CLOUD_RUN_SERVICE_COLLECTION_ONE_PLATFORM = 'run.projects.locations.services'


def _GetSource(source_arg, is_new_function):
  """Parses the source bucket and object from the --source flag.

  Currently only Cloud Storage location source is supported.

  Args:
    source_arg: str, the passed in source flag argument. Either with gs://,
      https://, or local file system
    is_new_function: bool, true if function does not exist yet

  Returns:
    source_bucket: str, source bucket name
    source_object: str, source object path
  """
  if not source_arg:
    if is_new_function:
      raise exceptions.FunctionsError(SOURCE_ERROR_MESSAGE)
    else:
      return None, None

  source_match = SOURCE_REGEX.match(source_arg)
  if not source_match:
    raise exceptions.FunctionsError(SOURCE_ERROR_MESSAGE)

  return (source_match.group(1), source_match.group(2))


def _GetServiceConfig(args, messages):
  """Constructs a ServiceConfig message from the command-line arguments.

  Args:
    args: [str], The arguments from the command line
    messages: messages module, the gcf v2 message stubs

  Returns:
    vpc_connector: str, the vpc connector name
    vpc_egress_settings: VpcConnectorEgressSettingsValueValuesEnum, enum value
  """
  env_var_flags = map_util.GetMapFlagsFromArgs('env-vars', args)
  env_vars = map_util.ApplyMapFlags({}, **env_var_flags)

  vpc_connector, vpc_egress_settings = (
      _GetVpcAndVpcEgressSettings(args, messages))

  return messages.ServiceConfig(
      availableMemoryMb=utils.BytesToMb(args.memory) if args.memory else None,
      maxInstanceCount=args.max_instances,
      minInstanceCount=args.min_instances,
      serviceAccountEmail=args.run_service_account or args.service_account,
      timeoutSeconds=args.timeout,
      ingressSettings=_GetIngressSettings(args, messages),
      vpcConnector=vpc_connector,
      vpcConnectorEgressSettings=vpc_egress_settings,
      environmentVariables=messages.ServiceConfig.EnvironmentVariablesValue(
          additionalProperties=[
              messages.ServiceConfig.EnvironmentVariablesValue
              .AdditionalProperty(key=key, value=value)
              for key, value in sorted(env_vars.items())
          ])), ['service_config.available_memory_mb'] if args.memory else []


def _GetEventTrigger(args, messages):
  """Constructs an EventTrigger message from the command-line arguments.

  Args:
    args: [str], The arguments from the command line
    messages: messages module, the gcf v2 message stubs

  Returns:
    event_trigger: cloudfunctions_v2alpha_messages.EventTrigger, used to request
      events sent from another service
  """
  if not args.trigger_topic and not args.trigger_event_filters:
    return None

  event_type = None
  pubsub_topic = None

  if args.trigger_topic:
    event_type = EVENT_TYPE_PUBSUB_MESSAGE_PUBLISHED
    pubsub_topic = 'projects/{}/topics/{}'.format(
        properties.VALUES.core.project.GetOrFail(), args.trigger_topic)

  event_trigger = messages.EventTrigger(
      eventType=event_type,
      pubsubTopic=pubsub_topic,
      serviceAccountEmail=args.trigger_service_account or args.service_account,
      triggerRegion=args.trigger_location)

  if args.trigger_event_filters:
    for trigger_event_filter in args.trigger_event_filters:
      attribute, value = trigger_event_filter.split('=', 1)
      if attribute == 'type':
        event_trigger.eventType = value
      else:
        event_trigger.eventFilters.append(
            messages.EventFilter(attribute=attribute, value=value))

  return event_trigger


def _GetSignatureType(args, event_trigger):
  """Determines the function signature type from the command-line arguments.

  Args:
    args: [str], The arguments from the command line
    event_trigger:

  Returns:
    signature_type: str, the desired functions signature type
  """
  if args.IsSpecified('trigger_http') or not event_trigger:
    if args.IsSpecified('signature_type') and args.signature_type != 'http':
      raise exceptions.FunctionsError(
          INVALID_NON_HTTP_SIGNATURE_TYPE_ERROR_MESSAGE)
    return 'http'
  elif args.IsSpecified('signature_type'):
    if args.signature_type == 'http':
      raise exceptions.FunctionsError(INVALID_HTTP_SIGNATURE_TYPE_ERROR_MESSAGE)
    return args.signature_type
  else:
    return 'cloudevent'


def _GetBuildConfig(args, messages, event_trigger, is_new_function):
  """Constructs a BuildConfig message from the command-line arguments.

  Args:
    args: [str], The arguments from the command line
    messages: messages module, the gcf v2 message stubs
    event_trigger: cloudfunctions_v2alpha_messages.EventTrigger, used to request
      events sent from another service
    is_new_function: bool, true if function does not exist yet

  Returns:
    build_config: cloudfunctions_v2alpha_messages.BuildConfig, describes the
      build step for the function
  """
  source_bucket, source_object = _GetSource(args.source, is_new_function)

  build_env_var_flags = map_util.GetMapFlagsFromArgs('build-env-vars', args)
  build_env_vars = map_util.ApplyMapFlags({}, **build_env_var_flags)

  if 'GOOGLE_FUNCTION_SIGNATURE_TYPE' in build_env_vars:
    raise exceptions.FunctionsError(
        SIGNATURE_TYPE_ENV_VAR_COLLISION_ERROR_MESSAGE)
  else:
    build_env_vars['GOOGLE_FUNCTION_SIGNATURE_TYPE'] = _GetSignatureType(
        args, event_trigger)

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


def _GetIngressSettings(args, messages):
  """Constructs ingress setting enum from command-line arguments."""
  if args.IsSpecified('ingress_settings'):
    ingress_settings_enum = arg_utils.ChoiceEnumMapper(
        arg_name='ingress_settings',
        message_enum=messages.ServiceConfig.IngressSettingsValueValuesEnum,
        custom_mappings=flags.INGRESS_SETTINGS_MAPPING).GetEnumForChoice(
            args.ingress_settings)
    return ingress_settings_enum
  else:
    return None


def _GetVpcAndVpcEgressSettings(args, messages):
  """Constructs vpc connector and egress settings from command-line arguments."""
  vpc_connector = args.vpc_connector

  if not args.IsSpecified('egress_settings'):
    return vpc_connector, None

  if vpc_connector is None:
    raise exceptions.RequiredArgumentException(
        'vpc-connector', 'Flag `--vpc-connector` is '
        'required for setting `egress-settings`.')
  vpc_egress_settings = arg_utils.ChoiceEnumMapper(
      arg_name='egress_settings',
      message_enum=messages.ServiceConfig
      .VpcConnectorEgressSettingsValueValuesEnum,
      custom_mappings=flags.EGRESS_SETTINGS_MAPPING).GetEnumForChoice(
          args.egress_settings)

  return vpc_connector, vpc_egress_settings


def _ValidateLegacyV1Flags(args):
  for flag_variable, flag_name in LEGACY_V1_FLAGS:
    if args.IsSpecified(flag_variable):
      raise exceptions.FunctionsError(LEGACY_V1_FLAG_ERROR % flag_name)


def _GetLabels(args, messages):
  labels_to_update = args.update_labels or {}
  return messages.Function.LabelsValue(additionalProperties=[
      messages.Function.LabelsValue.AdditionalProperty(key=key, value=value)
      for key, value in sorted(labels_to_update.items())
  ])


def _SetInvokerPermissions(args, function):
  """Add the IAM binding for the invoker role on the Cloud Run service, if applicable.

  Args:
    args: [str], The arguments from the command line
    function: cloudfunctions_v2alpha_messages.Function, recently created or
      updated GCF function

  Returns:
    None
  """
  service_ref_one_platform = resources.REGISTRY.ParseRelativeName(
      function.serviceConfig.service,
      CLOUD_RUN_SERVICE_COLLECTION_ONE_PLATFORM)

  if args.trigger_http:
    allow_unauthenticated = flags.ShouldEnsureAllUsersInvoke(args)
    if not allow_unauthenticated and not flags.ShouldDenyAllUsersInvoke(args):
      allow_unauthenticated = console_io.PromptContinue(
          prompt_string=(
              'Allow unauthenticated invocations of new function [{}]?'.format(
                  args.NAME)),
          default=False)

    if allow_unauthenticated:
      run_connection_context = connection_context.RegionalConnectionContext(
          service_ref_one_platform.locationsId,
          global_methods.SERVERLESS_API_NAME,
          global_methods.SERVERLESS_API_VERSION)
      with serverless_operations.Connect(run_connection_context) as operations:
        service_ref_k8s = resources.REGISTRY.ParseRelativeName(
            'namespaces/{}/services/{}'.format(
                properties.VALUES.core.project.GetOrFail(),
                service_ref_one_platform.Name()),
            CLOUD_RUN_SERVICE_COLLECTION_K8S)
        operations.AddOrRemoveIamPolicyBinding(
            service_ref_k8s,
            member=serverless_operations.ALLOW_UNAUTH_POLICY_BINDING_MEMBER,
            role=serverless_operations.ALLOW_UNAUTH_POLICY_BINDING_ROLE)


def _GetFunction(client, messages, function_ref):
  """Get function and return None if doesn't exist.

  Args:
    client: apitools client, the gcf v2 api client
    messages: messages module, the gcf v2 message stubs
    function_ref: gcf v2 functions resource reference

  Returns:
    function: cloudfunctions_v2alpha_messages.Function, fetched gcf v2 function
  """
  try:
    # We got response for a GET request, so a function exists.
    return client.projects_locations_functions.Get(
        messages.CloudfunctionsProjectsLocationsFunctionsGetRequest(
            name=function_ref.RelativeName()))
  except apitools_exceptions.HttpError as error:
    if error.status_code == six.moves.http_client.NOT_FOUND:
      return None
    raise


def Run(args, release_track):
  """Runs a function deployment with the given args."""
  client = api_util.GetClientInstance(release_track=release_track)
  messages = api_util.GetMessagesModule(release_track=release_track)

  function_ref = args.CONCEPTS.name.Parse()

  _ValidateLegacyV1Flags(args)

  fetched_function = _GetFunction(client, messages, function_ref)
  is_new_function = fetched_function is None

  event_trigger = _GetEventTrigger(args, messages)
  build_config = _GetBuildConfig(args, messages, event_trigger,
                                 is_new_function)

  service_config, service_updated_fields = _GetServiceConfig(args, messages)

  # cs/symbol:google.cloud.functions.v2main.Function$
  function = messages.Function(
      name=function_ref.RelativeName(),
      buildConfig=build_config,
      eventTrigger=event_trigger,
      serviceConfig=service_config,
      labels=_GetLabels(args, messages))

  if is_new_function:
    function_parent = 'projects/%s/locations/%s' % (
        properties.VALUES.core.project.GetOrFail(),
        properties.VALUES.functions.region.GetOrFail())

    create_request = messages.CloudfunctionsProjectsLocationsFunctionsCreateRequest(
        parent=function_parent,
        functionId=function_ref.Name(),
        function=function)
    operation = client.projects_locations_functions.Create(create_request)
  else:
    update_mask = ','.join(service_updated_fields)

    update_request = messages.CloudfunctionsProjectsLocationsFunctionsPatchRequest(
        name=function_ref.RelativeName(),
        updateMask=update_mask,
        function=function)

    operation = client.projects_locations_functions.Patch(update_request)

  api_util.WaitForOperation(client, messages, operation,
                            'Deploying function (may take a while)')

  function = client.projects_locations_functions.Get(
      messages.CloudfunctionsProjectsLocationsFunctionsGetRequest(
          name=function_ref.RelativeName()))

  _SetInvokerPermissions(args, function)

  log.status.Print(
      'You can view your function in the Cloud Console here: ' +
      'https://console.cloud.google.com/functions/details/{}/{}?project={}\n'
      .format(properties.VALUES.functions.region.GetOrFail(),
              function_ref.Name(), properties.VALUES.core.project.GetOrFail()))

  return function
