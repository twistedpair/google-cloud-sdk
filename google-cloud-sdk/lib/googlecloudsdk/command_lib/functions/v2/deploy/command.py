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

import os
import random
import re
import string

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import http_wrapper
from apitools.base.py import transfer
from googlecloudsdk.api_lib.functions import api_enablement
from googlecloudsdk.api_lib.functions import cmek_util
from googlecloudsdk.api_lib.functions import secrets as secrets_util
from googlecloudsdk.api_lib.functions.v1 import util as api_util_v1
from googlecloudsdk.api_lib.functions.v2 import client as api_client_v2
from googlecloudsdk.api_lib.functions.v2 import exceptions
from googlecloudsdk.api_lib.functions.v2 import util as api_util
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.calliope.arg_parsers import ArgumentTypeError
from googlecloudsdk.command_lib.eventarc import types as trigger_types
from googlecloudsdk.command_lib.functions import flags
from googlecloudsdk.command_lib.functions import labels_util
from googlecloudsdk.command_lib.functions import run_util
from googlecloudsdk.command_lib.functions import secrets_config
from googlecloudsdk.command_lib.projects import util as projects_util
from googlecloudsdk.command_lib.run import serverless_operations
from googlecloudsdk.command_lib.util import gcloudignore
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.args import map_util
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import transports
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import archive
from googlecloudsdk.core.util import files as file_utils
import six

_SIGNED_URL_UPLOAD_ERROR_MESSSAGE = (
    'There was a problem uploading the source code to a signed Cloud Storage '
    'URL. Please try again.'
)

_GCS_SOURCE_REGEX = re.compile('gs://([^/]+)/(.*)')
_GCS_SOURCE_ERROR_MESSAGE = (
    'Invalid Cloud Storage URL. Must match the following format: '
    'gs://bucket/object'
)

# https://cloud.google.com/functions/docs/reference/rest/v1/projects.locations.functions#sourcerepository
_CSR_SOURCE_REGEX = re.compile(
    # Minimally required fields
    r'https://source\.developers\.google\.com'
    r'/projects/(?P<project_id>[^/]+)/repos/(?P<repo_name>[^/]+)'
    # Optional oneof revision/alias
    r'(((/revisions/(?P<commit>[^/]+))|'
    r'(/moveable-aliases/(?P<branch>[^/]+))|'
    r'(/fixed-aliases/(?P<tag>[^/]+)))'
    # Optional path
    r'(/paths/(?P<path>[^/]+))?)?'
    # Optional ending forward slash and enforce regex matches end of string
    r'/?$'
)
_CSR_SOURCE_ERROR_MESSAGE = (
    'Invalid Cloud Source Repository URL provided. Must match the '
    'following format: https://source.developers.google.com/projects/'
    '<projectId>/repos/<repoName>. Specify the desired branch by appending '
    '/moveable-aliases/<branchName>, the desired tag with '
    '/fixed-aliases/<tagName>, or the desired commit with /revisions/<commit>. '
)

_INVALID_RETRY_FLAG_ERROR_MESSAGE = (
    '`--retry` is only supported with an event trigger not http triggers.'
)

_LATEST_REVISION_TRAFFIC_WARNING_MESSAGE = (
    'The latest revision of this function is not serving 100% of traffic. '
    'Please see the associated Cloud Run service to '
    'confirm your expected traffic settings.'
)

_V1_ONLY_FLAGS = [
    # Legacy flags
    ('docker_registry', '--docker-registry'),
    ('security_level', '--security-level'),
    # Not yet supported flags
    ('buildpack_stack', '--buildpack-stack'),
]
_V1_ONLY_FLAG_ERROR = (
    '`%s` is only supported in Cloud Functions (First generation).'
)

_DEFAULT_IGNORE_FILE = gcloudignore.DEFAULT_IGNORE_FILE + '\nnode_modules\n'

_ZIP_MIME_TYPE = 'application/zip'

_DEPLOYMENT_TOOL_LABEL = 'deployment-tool'
_DEPLOYMENT_TOOL_VALUE = 'cli-gcloud'

# Extra progress tracker stages that can appear during rollbacks.
# cs/symbol:google.cloud.functions.v2main.Stage.Name
_ARTIFACT_REGISTRY_STAGE = progress_tracker.Stage(
    '[ArtifactRegistry]', key='ARTIFACT_REGISTRY'
)
_SERVICE_ROLLBACK_STAGE = progress_tracker.Stage(
    '[Healthcheck]', key='SERVICE_ROLLBACK'
)
_TRIGGER_ROLLBACK_STAGE = progress_tracker.Stage(
    '[Triggercheck]', key='TRIGGER_ROLLBACK'
)

_EXTRA_STAGES = [
    _ARTIFACT_REGISTRY_STAGE,
    _SERVICE_ROLLBACK_STAGE,
    _TRIGGER_ROLLBACK_STAGE,
]

# GCF 2nd generation control plane valid memory units
_GCF_GEN2_UNITS = [
    'k',
    'Ki',
    'M',
    'Mi',
    'G',
    'Gi',
    'T',
    'Ti',
    'P',
    'Pi',
]

# GCF 2nd gen valid cpu units
_GCF_GEN2_CPU_UNITS = ['m'] + _GCF_GEN2_UNITS

_MEMORY_VALUE_PATTERN = r"""
    ^                                    # Beginning of input marker.
    (?P<amount>\d+)                      # Amount.
    ((?P<suffix>[-/ac-zAC-Z]+)([bB])?)?  # Optional scale and optional 'b'.
    $                                    # End of input marker.
"""

_CPU_VALUE_PATTERN = r"""
    ^                                    # Beginning of input marker.
    (?P<amount>\d*.?\d*)                 # Amount.
    (?P<suffix>[-/ac-zAC-Z]+)?           # Optional scale.
    $                                    # End of input marker.
"""


def _GcloudIgnoreCreationPredicate(directory):
  return gcloudignore.AnyFileOrDirExists(
      directory, gcloudignore.GIT_FILES + ['node_modules']
  )


def _GetSourceGCS(messages, source):
  """Constructs a `Source` message from a Cloud Storage object.

  Args:
    messages: messages module, the GCFv2 message stubs
    source: str, the Cloud Storage URL

  Returns:
    function_source: cloud.functions.v2main.Source
  """
  match = _GCS_SOURCE_REGEX.match(source)
  if not match:
    raise exceptions.FunctionsError(_GCS_SOURCE_ERROR_MESSAGE)

  return messages.Source(
      storageSource=messages.StorageSource(
          bucket=match.group(1), object=match.group(2)
      )
  )


def _GetSourceCSR(messages, source):
  """Constructs a `Source` message from a Cloud Source Repository reference.

  Args:
    messages: messages module, the GCFv2 message stubs
    source: str, the Cloud Source Repository reference

  Returns:
    function_source: cloud.functions.v2main.Source
  """
  match = _CSR_SOURCE_REGEX.match(source)

  if match is None:
    raise exceptions.FunctionsError(_CSR_SOURCE_ERROR_MESSAGE)

  repo_source = messages.RepoSource(
      projectId=match.group('project_id'),
      repoName=match.group('repo_name'),
      dir=match.group('path'),  # Optional
  )

  # Optional oneof revision field
  commit = match.group('commit')
  branch = match.group('branch')
  tag = match.group('tag')

  if commit:
    repo_source.commitSha = commit
  elif tag:
    repo_source.tagName = tag
  else:
    # Default to 'master' branch if no revision/alias provided.
    repo_source.branchName = branch or 'master'

  return messages.Source(repoSource=repo_source)


def _UploadToStageBucket(region, function_name, zip_file_path, stage_bucket):
  """Uploads a ZIP file to a user-provided stage bucket.

  Args:
    region: str, the region to deploy the function to
    function_name: str, the name of the function
    zip_file_path: str, the path to the ZIP file
    stage_bucket: str, the name of the stage bucket

  Returns:
    dest_object: storage_util.ObjectReference, a reference to the uploaded
                 Cloud Storage object
  """
  dest_object = storage_util.ObjectReference.FromBucketRef(
      storage_util.BucketReference.FromArgument(stage_bucket),
      '{}-{}-{}.zip'.format(
          region,
          function_name,
          ''.join(random.choice(string.ascii_lowercase) for _ in range(12)),
      ),
  )
  storage_api.StorageClient().CopyFileToGCS(zip_file_path, dest_object)
  return dest_object


def _UploadToGeneratedUrl(zip_file_path, url):
  """Uploads a ZIP file to a signed Cloud Storage URL.

  Args:
    zip_file_path: str, the path to the ZIP file
    url: str, the signed Cloud Storage URL
  """
  upload = transfer.Upload.FromFile(zip_file_path, mime_type=_ZIP_MIME_TYPE)
  try:
    request = http_wrapper.Request(
        url, http_method='PUT', headers={'content-type': upload.mime_type}
    )
    request.body = upload.stream.read()
    upload.stream.close()
    response = http_wrapper.MakeRequest(
        transports.GetApitoolsTransport(), request
    )
  finally:
    upload.stream.close()
  if response.status_code // 100 != 2:
    raise exceptions.FunctionsError(_SIGNED_URL_UPLOAD_ERROR_MESSSAGE)


def _GetSourceLocal(
    client,
    messages,
    region,
    function_name,
    source,
    stage_bucket_arg,
    ignore_file_arg,
    kms_key=None,
):
  """Constructs a `Source` message from a local file system path.

  Args:
    client: The GCFv2 API client
    messages: messages module, the GCFv2 message stubs
    region: str, the region to deploy the function to
    function_name: str, the name of the function
    source: str, the path
    stage_bucket_arg: str, the passed in --stage-bucket flag argument
    ignore_file_arg: str, the passed in --ignore-file flag argument
    kms_key: resource name of the customer managed KMS key | None

  Returns:
    function_source: cloud.functions.v2main.Source
  """
  with file_utils.TemporaryDirectory() as tmp_dir:
    zip_file_path = os.path.join(tmp_dir, 'fun.zip')
    chooser = gcloudignore.GetFileChooserForDir(
        source,
        default_ignore_file=_DEFAULT_IGNORE_FILE,
        gcloud_ignore_creation_predicate=_GcloudIgnoreCreationPredicate,
        ignore_file=ignore_file_arg,
    )
    archive.MakeZipFromDir(zip_file_path, source, predicate=chooser.IsIncluded)

    if stage_bucket_arg:
      dest_object = _UploadToStageBucket(
          region, function_name, zip_file_path, stage_bucket_arg
      )
      return messages.Source(
          storageSource=messages.StorageSource(
              bucket=dest_object.bucket, object=dest_object.name
          )
      )
    else:
      generate_upload_url_request = messages.GenerateUploadUrlRequest(
          kmsKeyName=kms_key
      )
      try:
        dest = client.projects_locations_functions.GenerateUploadUrl(
            messages.CloudfunctionsProjectsLocationsFunctionsGenerateUploadUrlRequest(
                generateUploadUrlRequest=generate_upload_url_request,
                parent='projects/{}/locations/{}'.format(
                    api_util.GetProject(), region
                ),
            )
        )
      except apitools_exceptions.HttpError as e:
        cmek_util.ProcessException(e, kms_key)
        raise e

      _UploadToGeneratedUrl(zip_file_path, dest.uploadUrl)

      return messages.Source(storageSource=dest.storageSource)


def _GetSource(
    client,
    messages,
    region,
    function_name,
    source_arg,
    stage_bucket_arg,
    ignore_file_arg,
    existing_function,
    kms_key=None,
):
  """Parses the source bucket and object from the --source flag.

  Args:
    client: The GCFv2 API client
    messages: messages module, the GCFv2 message stubs
    region: str, the region to deploy the function to
    function_name: str, the name of the function
    source_arg: str, the passed in --source flag argument
    stage_bucket_arg: str, the passed in --stage-bucket flag argument
    ignore_file_arg: str, the passed in --ignore-file flag argument
    existing_function: cloudfunctions_v2alpha_messages.Function | None
    kms_key: resource name of the customer managed KMS key | None

  Returns:
    function_source: cloud.functions.v2main.Source | None
    update_field_set: frozenset, set of update mask fields
  """
  if (
      source_arg is None
      and existing_function is not None
      and existing_function.buildConfig.source.repoSource
  ):
    # The function was previously deployed from a Cloud Source Repository, and
    # the `--source` flag was not specified this time. Don't set any source,
    # so the control plane will reuse the original one.
    return None, frozenset()

  source = source_arg or '.'

  if source.startswith('gs://'):
    return _GetSourceGCS(messages, source), frozenset(['build_config.source'])
  elif source.startswith('https://'):
    return _GetSourceCSR(messages, source), frozenset(['build_config.source'])
  else:
    return _GetSourceLocal(
        client,
        messages,
        region,
        function_name,
        source,
        stage_bucket_arg,
        ignore_file_arg,
        kms_key,
    ), frozenset(['build_config.source'])


def _GetServiceConfig(args, messages, existing_function):
  """Constructs a ServiceConfig message from the command-line arguments.

  Args:
    args: argparse.Namespace, arguments that this command was invoked with
    messages: messages module, the GCFv2 message stubs
    existing_function: cloudfunctions_v2alpha_messages.Function | None

  Returns:
    vpc_connector: str, the vpc connector name
    vpc_egress_settings: VpcConnectorEgressSettingsValueValuesEnum, the vpc
      enum value
    updated_fields_set: frozenset, set of update mask fields
  """

  old_env_vars = {}
  if (
      existing_function
      and existing_function.serviceConfig
      and existing_function.serviceConfig.environmentVariables
      and existing_function.serviceConfig.environmentVariables.additionalProperties
  ):
    for (
        additional_property
    ) in (
        existing_function.serviceConfig.environmentVariables.additionalProperties
    ):
      old_env_vars[additional_property.key] = additional_property.value

  env_var_flags = map_util.GetMapFlagsFromArgs('env-vars', args)
  env_vars = map_util.ApplyMapFlags(old_env_vars, **env_var_flags)

  old_secrets = {}
  new_secrets = {}
  if existing_function and existing_function.serviceConfig:
    old_secrets = secrets_util.GetSecretsAsDict(
        existing_function.serviceConfig.secretEnvironmentVariables,
        existing_function.serviceConfig.secretVolumes,
    )

  if secrets_config.IsArgsSpecified(args):
    try:
      new_secrets = secrets_config.ApplyFlags(
          old_secrets,
          args,
          api_util.GetProject(),
          projects_util.GetProjectNumber(api_util.GetProject()),
      )
    except ArgumentTypeError as error:
      core_exceptions.reraise(exceptions.FunctionsError(error))
  else:
    new_secrets = old_secrets

  old_secret_env_vars, old_secret_volumes = secrets_config.SplitSecretsDict(
      old_secrets
  )
  secret_env_vars, secret_volumes = secrets_config.SplitSecretsDict(new_secrets)

  vpc_connector, vpc_egress_settings, vpc_updated_fields = (
      _GetVpcAndVpcEgressSettings(args, messages, existing_function)
  )

  ingress_settings, ingress_updated_fields = _GetIngressSettings(args, messages)

  concurrency = getattr(args, 'concurrency', None)
  cpu = getattr(args, 'cpu', None)

  updated_fields = set()

  if args.serve_all_traffic_latest_revision:
    # only set field if flag is specified, never explicitly set to false.
    updated_fields.add('service_config.all_traffic_on_latest_revision')
  if args.memory is not None:
    updated_fields.add('service_config.available_memory')
  if concurrency is not None:
    updated_fields.add('service_config.max_instance_request_concurrency')
  if cpu is not None:
    updated_fields.add('service_config.available_cpu')
  if args.max_instances is not None or args.clear_max_instances:
    updated_fields.add('service_config.max_instance_count')
  if args.min_instances is not None or args.clear_min_instances:
    updated_fields.add('service_config.min_instance_count')
  if args.run_service_account is not None or args.service_account is not None:
    updated_fields.add('service_config.service_account_email')
  if args.timeout is not None:
    updated_fields.add('service_config.timeout_seconds')
  if env_vars != old_env_vars:
    updated_fields.add('service_config.environment_variables')
  if secret_env_vars != old_secret_env_vars:
    updated_fields.add('service_config.secret_environment_variables')
  if secret_volumes != old_secret_volumes:
    updated_fields.add('service_config.secret_volumes')

  service_updated_fields = frozenset.union(
      vpc_updated_fields, ingress_updated_fields, updated_fields
  )

  return (
      messages.ServiceConfig(
          availableMemory=_ParseMemoryStrToK8sMemory(args.memory),
          maxInstanceCount=None
          if args.clear_max_instances
          else args.max_instances,
          minInstanceCount=None
          if args.clear_min_instances
          else args.min_instances,
          serviceAccountEmail=args.run_service_account or args.service_account,
          timeoutSeconds=args.timeout,
          ingressSettings=ingress_settings,
          vpcConnector=vpc_connector,
          vpcConnectorEgressSettings=vpc_egress_settings,
          allTrafficOnLatestRevision=(
              args.serve_all_traffic_latest_revision or None
          ),
          environmentVariables=messages.ServiceConfig.EnvironmentVariablesValue(
              additionalProperties=[
                  messages.ServiceConfig.EnvironmentVariablesValue.AdditionalProperty(
                      key=key, value=value
                  )
                  for key, value in sorted(env_vars.items())
              ]
          ),
          secretEnvironmentVariables=secrets_util.SecretEnvVarsToMessages(
              secret_env_vars, messages
          ),
          secretVolumes=secrets_util.SecretVolumesToMessages(
              secret_volumes, messages, normalize_for_v2=True
          ),
          maxInstanceRequestConcurrency=concurrency,
          availableCpu=_ValidateK8sCpuStr(cpu),
      ),
      service_updated_fields,
  )


def _ParseMemoryStrToK8sMemory(memory):
  """Parses user provided memory to kubernetes expected format.

  Ensure --gen2 continues to parse Gen1 --memory passed in arguments. Defaults
  as M if no unit was specified.

  k8s format:
  https://github.com/kubernetes/kubernetes/blob/master/staging/src/k8s.io/apimachinery/pkg/api/resource/generated.proto

  Args:
    memory: str, input from `args.memory`

  Returns:
    k8s_memory: str|None, in kubernetes memory format. GCF 2nd Gen control plane
      is case-sensitive and only accepts: value + m, k, M, G, T, Ki, Mi, Gi, Ti.

  Raises:
    InvalidArgumentException: User provided invalid input for flag.
  """
  if memory is None or not memory:
    return None

  match = re.match(_MEMORY_VALUE_PATTERN, memory, re.VERBOSE)
  if not match:
    raise exceptions.InvalidArgumentException(
        '--memory', 'Invalid memory value for: {} specified.'.format(memory)
    )

  suffix = match.group('suffix')
  amount = match.group('amount')

  # Default to megabytes (decimal-base) if suffix not provided.
  if suffix is None:
    suffix = 'M'

  # No case enforced since previously didn't enforce case sensitivity.
  uppercased_gen2_units = dict(
      [(unit.upper(), unit) for unit in _GCF_GEN2_UNITS]
  )
  corrected_suffix = uppercased_gen2_units.get(suffix.upper())

  if not corrected_suffix:
    raise exceptions.InvalidArgumentException(
        '--memory', 'Invalid suffix for: {} specified.'.format(memory)
    )

  parsed_memory = amount + corrected_suffix
  return parsed_memory


def _ValidateK8sCpuStr(cpu):
  """Validates user provided cpu to kubernetes expected format.

  k8s format:
  https://github.com/kubernetes/kubernetes/blob/master/staging/src/k8s.io/apimachinery/pkg/api/resource/generated.proto

  Args:
    cpu: str, input from `args.cpu`

  Returns:
    k8s_cpu: str|None, in kubernetes cpu format.

  Raises:
    InvalidArgumentException: User provided invalid input for flag.
  """
  if cpu is None:
    return None

  match = re.match(_CPU_VALUE_PATTERN, cpu, re.VERBOSE)
  if not match:
    raise exceptions.InvalidArgumentException(
        '--cpu', 'Invalid cpu value for: {} specified.'.format(cpu)
    )

  suffix = match.group('suffix') or ''
  amount = match.group('amount')

  if not amount or amount == '.':
    raise exceptions.InvalidArgumentException(
        '--cpu', 'Invalid amount for: {} specified.'.format(cpu)
    )

  if suffix and suffix not in _GCF_GEN2_CPU_UNITS:
    raise exceptions.InvalidArgumentException(
        '--cpu', 'Invalid suffix for: {} specified.'.format(cpu)
    )

  parsed_memory = amount + suffix
  return parsed_memory


def _GetEventTrigger(args, messages, existing_function):
  """Constructs an EventTrigger message from the command-line arguments.

  Args:
    args: argparse.Namespace, arguments that this command was invoked with
    messages: messages module, the GCFv2 message stubs
    existing_function: cloudfunctions_v2alpha_messages.Function | None

  Returns:
    event_trigger: cloudfunctions_v2alpha_messages.EventTrigger, used to request
      events sent from another service
    updated_fields_set: frozenset, set of update mask fields
  """
  if args.trigger_http:
    event_trigger, updated_fields_set = None, frozenset(
        ['event_trigger'] if existing_function else []
    )

  elif args.trigger_event or args.trigger_resource:
    event_trigger, updated_fields_set = _GetEventTriggerForEventType(
        args, messages
    ), frozenset(['event_trigger'])
  elif args.trigger_topic or args.trigger_bucket or args.trigger_event_filters:
    event_trigger, updated_fields_set = _GetEventTriggerForOther(
        args, messages
    ), frozenset(['event_trigger'])

  else:
    if existing_function:
      event_trigger, updated_fields_set = (
          existing_function.eventTrigger,
          frozenset(),
      )
    else:
      raise calliope_exceptions.OneOfArgumentsRequiredException(
          [
              '--trigger-topic',
              '--trigger-bucket',
              '--trigger-http',
              '--trigger-event',
              '--trigger-event-filters',
          ],
          'You must specify a trigger when deploying a new function.',
      )

  if args.IsSpecified('retry'):
    retry_policy, retry_updated_field = _GetRetry(args, messages, event_trigger)
    event_trigger.retryPolicy = retry_policy
    updated_fields_set = updated_fields_set.union(retry_updated_field)

  if event_trigger and trigger_types.IsPubsubType(event_trigger.eventType):
    pubsub_sa = 'service-{}@gcp-sa-pubsub.iam.gserviceaccount.com'.format(
        projects_util.GetProjectNumber(api_util.GetProject())
    )
    if not api_util.HasRoleBinding(pubsub_sa, 'roles/pubsub.serviceAgent'):
      api_util.PromptToBindRoleIfMissing(
          pubsub_sa,
          'roles/iam.serviceAccountTokenCreator',
          reason=(
              'Pub/Sub needs this role to create identity tokens. '
              'For more details, please see '
              'https://cloud.google.com/pubsub/docs/push#authentication'
          ),
      )

  if event_trigger and trigger_types.IsAuditLogType(event_trigger.eventType):
    service_filter = [
        f for f in event_trigger.eventFilters if f.attribute == 'serviceName'
    ]
    if service_filter:
      service = service_filter[0].value
      if not api_util.HasDataAccessAuditLogsFullyEnabled(service):
        api_util.PromptToEnableDataAccessAuditLogs(service)

  return event_trigger, updated_fields_set


def _GetEventTriggerForEventType(args, messages):
  """Constructs an EventTrigger message from the command-line arguments.

  Args:
    args: argparse.Namespace, arguments that this command was invoked with
    messages: messages module, the GCFv2 message stubs

  Returns:
    event_trigger: cloudfunctions_v2alpha_messages.EventTrigger, used to request
      events sent from another service
  """
  trigger_event = args.trigger_event
  trigger_resource = args.trigger_resource
  service_account_email = args.trigger_service_account or args.service_account

  if trigger_event in api_util.PUBSUB_MESSAGE_PUBLISH_TYPES:
    pubsub_topic = api_util_v1.ValidatePubsubTopicNameOrRaise(trigger_resource)
    return messages.EventTrigger(
        eventType=api_util.EA_PUBSUB_MESSAGE_PUBLISHED,
        pubsubTopic=_BuildFullPubsubTopic(pubsub_topic),
        serviceAccountEmail=service_account_email,
        triggerRegion=args.trigger_location,
    )

  elif (
      trigger_event in api_util.EVENTARC_STORAGE_TYPES
      or trigger_event in api_util.EVENTFLOW_TO_EVENTARC_STORAGE_MAP
  ):
    # name without prefix gs://
    bucket_name = storage_util.BucketReference.FromUrl(trigger_resource).bucket
    storage_event_type = api_util.EVENTFLOW_TO_EVENTARC_STORAGE_MAP.get(
        trigger_event, trigger_event
    )
    return messages.EventTrigger(
        eventType=storage_event_type,
        eventFilters=[
            messages.EventFilter(attribute='bucket', value=bucket_name)
        ],
        serviceAccountEmail=service_account_email,
        triggerRegion=args.trigger_location,
    )

  else:
    raise exceptions.InvalidArgumentException(
        '--trigger-event',
        'Event type {} is not supported by this flag, try using'
        ' --trigger-event-filters.'.format(trigger_event),
    )


def _GetEventTriggerForOther(args, messages):
  """Constructs an EventTrigger when using --trigger-bucket/topic/filters.

  Args:
    args: argparse.Namespace, arguments that this command was invoked with
    messages: messages module, the GCFv2 message stubs

  Returns:
    event_trigger: cloudfunctions_v2alpha_messages.EventTrigger, used to request
      events sent from another service
  """
  event_filters = []
  event_type = None
  pubsub_topic = None
  service_account_email = args.trigger_service_account or args.service_account
  trigger_location = args.trigger_location

  if args.trigger_topic:
    event_type = api_util.EA_PUBSUB_MESSAGE_PUBLISHED
    pubsub_topic = _BuildFullPubsubTopic(args.trigger_topic)
  elif args.trigger_bucket:
    bucket = args.trigger_bucket[5:].rstrip('/')  # strip 'gs://' and final '/'
    event_type = api_util.EA_STORAGE_FINALIZE
    event_filters = [messages.EventFilter(attribute='bucket', value=bucket)]
  elif args.trigger_event_filters:
    event_type = args.trigger_event_filters.get('type')
    event_filters = [
        messages.EventFilter(attribute=attr, value=val)
        for attr, val in args.trigger_event_filters.items()
        if attr != 'type'
    ]
    if args.trigger_event_filters_path_pattern:
      operator = 'match-path-pattern'
      event_filters.extend(
          [
              messages.EventFilter(attribute=attr, value=val, operator=operator)
              for attr, val in args.trigger_event_filters_path_pattern.items()
          ]
      )

  trigger_channel = None
  if args.trigger_channel:
    trigger_channel = args.CONCEPTS.trigger_channel.Parse().RelativeName()

  return messages.EventTrigger(
      eventFilters=event_filters,
      eventType=event_type,
      pubsubTopic=pubsub_topic,
      serviceAccountEmail=service_account_email,
      channel=trigger_channel,
      triggerRegion=trigger_location,
  )


def _GetRetry(args, messages, event_trigger):
  """Constructs an RetryPolicy enum from --(no-)retry flag.

  Args:
    args: argparse.Namespace, arguments that this command was invoked with
    messages: messages module, the GCFv2 message stubs
    event_trigger: cloudfunctions_v2alpha_messages.EventTrigger, used to request
      events sent from another service

  Returns:
    EventTrigger.RetryPolicyValueValuesEnum(
      'RETRY_POLICY_RETRY' | 'RETRY_POLICY_DO_NOT_RETRY')
    frozenset, set of update mask fields
  """

  if event_trigger is None:
    raise exceptions.FunctionsError(_INVALID_RETRY_FLAG_ERROR_MESSAGE)

  if args.retry:
    return messages.EventTrigger.RetryPolicyValueValuesEnum(
        'RETRY_POLICY_RETRY'
    ), frozenset(['eventTrigger.retryPolicy'])
  else:
    # explicitly using --no-retry flag
    return messages.EventTrigger.RetryPolicyValueValuesEnum(
        'RETRY_POLICY_DO_NOT_RETRY'
    ), frozenset(['eventTrigger.retryPolicy'])


def _BuildFullPubsubTopic(pubsub_topic):
  return 'projects/{}/topics/{}'.format(api_util.GetProject(), pubsub_topic)


def _GetBuildConfig(
    args, client, messages, region, function_name, existing_function
):
  """Constructs a BuildConfig message from the command-line arguments.

  Args:
    args: argparse.Namespace, arguments that this command was invoked with
    client: The GCFv2 API client
    messages: messages module, the GCFv2 message stubs
    region: str, the region to deploy the function to
    function_name: str, the name of the function
    existing_function: cloudfunctions_v2alpha_messages.Function | None

  Returns:
    build_config: cloudfunctions_v2alpha_messages.BuildConfig, describes the
      build step for the function
    updated_fields_set: frozenset[str], set of update mask fields
  """
  kms_key = _GetActiveKmsKey(args, existing_function)
  function_source, source_updated_fields = _GetSource(
      client,
      messages,
      region,
      function_name,
      args.source,
      args.stage_bucket,
      args.ignore_file,
      existing_function,
      kms_key,
  )

  old_build_env_vars = {}
  if (
      existing_function
      and existing_function.buildConfig
      and existing_function.buildConfig.environmentVariables
      and existing_function.buildConfig.environmentVariables.additionalProperties
  ):
    for (
        additional_property
    ) in (
        existing_function.buildConfig.environmentVariables.additionalProperties
    ):
      old_build_env_vars[additional_property.key] = additional_property.value

  build_env_var_flags = map_util.GetMapFlagsFromArgs('build-env-vars', args)
  # Dict
  build_env_vars = map_util.ApplyMapFlags(
      old_build_env_vars, **build_env_var_flags
  )

  updated_fields = set()

  if build_env_vars != old_build_env_vars:
    updated_fields.add('build_config.environment_variables')

  if args.entry_point is not None:
    updated_fields.add('build_config.entry_point')
  if args.runtime is not None:
    updated_fields.add('build_config.runtime')

  worker_pool = None if args.clear_build_worker_pool else args.build_worker_pool

  if args.build_worker_pool is not None or args.clear_build_worker_pool:
    updated_fields.add('build_config.worker_pool')

  build_updated_fields = frozenset.union(source_updated_fields, updated_fields)
  return (
      messages.BuildConfig(
          entryPoint=args.entry_point,
          runtime=args.runtime,
          source=function_source,
          workerPool=worker_pool,
          environmentVariables=messages.BuildConfig.EnvironmentVariablesValue(
              additionalProperties=[
                  messages.BuildConfig.EnvironmentVariablesValue.AdditionalProperty(
                      key=key, value=value
                  )
                  for key, value in sorted(build_env_vars.items())
              ]
          ),
      ),
      build_updated_fields,
  )


def _GetActiveKmsKey(args, existing_function):
  """Retrives KMS key applicable to the deployment request.

  Args:
    args: argparse.Namespace, arguments that this command was invoked with.
    existing_function: cloudfunctions_v2alpha_messages.Function | None.

  Returns:
    Either newly passed or pre-existing KMS key.
  """
  if args.IsSpecified('kms_key'):
    return args.kms_key
  elif args.IsSpecified('clear_kms_key'):
    return None
  return None if not existing_function else existing_function.kmsKeyName


def _GetIngressSettings(args, messages):
  """Constructs ingress setting enum from command-line arguments.

  Args:
    args: argparse.Namespace, arguments that this command was invoked with
    messages: messages module, the GCFv2 message stubs

  Returns:
    ingress_settings_enum: ServiceConfig.IngressSettingsValueValuesEnum, the
      ingress setting enum value
    updated_fields_set: frozenset[str], set of update mask fields
  """
  if args.ingress_settings:
    ingress_settings_enum = arg_utils.ChoiceEnumMapper(
        arg_name='ingress_settings',
        message_enum=messages.ServiceConfig.IngressSettingsValueValuesEnum,
        custom_mappings=flags.INGRESS_SETTINGS_MAPPING,
    ).GetEnumForChoice(args.ingress_settings)
    return ingress_settings_enum, frozenset(['service_config.ingress_settings'])
  else:
    return None, frozenset()


def _GetVpcAndVpcEgressSettings(args, messages, existing_function):
  """Constructs vpc connector and egress settings from command-line arguments.

  Args:
    args: argparse.Namespace, arguments that this command was invoked with
    messages: messages module, the GCFv2 message stubs
    existing_function: cloudfunctions_v2alpha_messages.Function | None

  Returns:
    vpc_connector: str, name of the vpc connector
    vpc_egress_settings:
    ServiceConfig.VpcConnectorEgressSettingsValueValuesEnum,
      the egress settings for the vpc connector
    vpc_updated_fields_set: frozenset[str], set of update mask fields
  """

  egress_settings = None
  vpc_connector = args.CONCEPTS.vpc_connector.Parse()
  if args.egress_settings:
    egress_settings = arg_utils.ChoiceEnumMapper(
        arg_name='egress_settings',
        message_enum=messages.ServiceConfig.VpcConnectorEgressSettingsValueValuesEnum,
        custom_mappings=flags.EGRESS_SETTINGS_MAPPING,
    ).GetEnumForChoice(args.egress_settings)

  if args.clear_vpc_connector:
    return (
        None,
        None,
        frozenset([
            'service_config.vpc_connector',
            'service_config.vpc_connector_egress_settings',
        ]),
    )
  elif vpc_connector:
    if args.egress_settings:
      return (
          vpc_connector.RelativeName(),
          egress_settings,
          frozenset([
              'service_config.vpc_connector',
              'service_config.vpc_connector_egress_settings',
          ]),
      )
    else:
      return (
          vpc_connector.RelativeName(),
          None,
          frozenset(['service_config.vpc_connector']),
      )
  elif args.egress_settings:
    if (
        existing_function
        and existing_function.serviceConfig
        and existing_function.serviceConfig.vpcConnector
    ):
      return (
          existing_function.serviceConfig.vpcConnector,
          egress_settings,
          frozenset(['service_config.vpc_connector_egress_settings']),
      )
    else:
      raise exceptions.RequiredArgumentException(
          'vpc-connector',
          'Flag `--vpc-connector` is required for setting `egress-settings`.',
      )
  else:
    return None, None, frozenset()


def _ValidateV1OnlyFlags(args, release_track):
  """Ensures that only the arguments supported in V2 are passing through."""
  for flag_variable, flag_name in _V1_ONLY_FLAGS:
    if args.IsKnownAndSpecified(flag_variable):
      raise exceptions.FunctionsError(_V1_ONLY_FLAG_ERROR % flag_name)
  # TODO(b/242182323): Special handling of transitive flags that are in the
  # process of being supported across tracks. Remove once they reach the GA.
  if args.IsSpecified('kms_key') or args.IsSpecified('clear_kms_key'):
    if release_track == calliope_base.ReleaseTrack.GA:
      flag_name = (
          '--kms-key' if args.IsSpecified('kms_key') else '--clear-kms-key'
      )
      raise exceptions.FunctionsError(_V1_ONLY_FLAG_ERROR % flag_name)
  if args.IsSpecified('docker_repository') or args.IsSpecified(
      'clear_docker_repository'
  ):
    if release_track == calliope_base.ReleaseTrack.GA:
      flag_name = (
          '--docker-repository'
          if args.IsSpecified('docker_repository')
          else '--clear-docker-repository'
      )
      raise exceptions.FunctionsError(_V1_ONLY_FLAG_ERROR % flag_name)


def _GetLabels(args, messages, existing_function):
  """Constructs labels from command-line arguments.

  Args:
    args: argparse.Namespace, arguments that this command was invoked with
    messages: messages module, the GCFv2 message stubs
    existing_function: cloudfunctions_v2alpha_messages.Function | None

  Returns:
    labels: Function.LabelsValue, functions labels metadata
    updated_fields_set: frozenset[str], list of update mask fields
  """
  if existing_function:
    required_labels = {}
  else:
    required_labels = {_DEPLOYMENT_TOOL_LABEL: _DEPLOYMENT_TOOL_VALUE}
  labels_diff = labels_util.Diff.FromUpdateArgs(
      args, required_labels=required_labels
  )
  labels_update = labels_diff.Apply(
      messages.Function.LabelsValue,
      existing_function.labels if existing_function else None,
  )
  if labels_update.needs_update:
    return labels_update.labels, frozenset(['labels'])
  else:
    return None, frozenset()


def _SetCmekFields(
    args, function, existing_function, function_ref, release_track
):
  """Sets CMEK-related fields on the function.

  Args:
    args: argparse.Namespace, arguments that this command was invoked with.
    function: cloudfunctions_v2alpha_messages.Function, recently created or
      updated GCF function.
    existing_function: pre-existing function
      (cloudfunctions_v2alpha_messages.Function | None).
    function_ref: resource reference.
    release_track: the release track (alpha|beta|ga).

  Returns:
    updated_fields_set: frozenset[str], set of update mask fields.
  """
  updated_fields = set()
  if release_track == calliope_base.ReleaseTrack.GA:
    return updated_fields
  function.kmsKeyName = (
      existing_function.kmsKeyName if existing_function else None
  )
  if args.IsSpecified('kms_key') or args.IsSpecified('clear_kms_key'):
    function.kmsKeyName = (
        None if args.IsSpecified('clear_kms_key') else args.kms_key
    )
  if (
      existing_function is None
      or function.kmsKeyName != existing_function.kmsKeyName
  ):
    if args.kms_key is not None:
      cmek_util.ValidateKMSKeyForFunction(function.kmsKeyName, function_ref)
    updated_fields.add('kms_key_name')
  return updated_fields


def _SetDockerRepositoryConfig(
    args, function, existing_function, function_ref, release_track
):
  """Sets user-provided docker repository field on the function.

  Args:
    args: argparse.Namespace, arguments that this command was invoked with
    function: cloudfunctions_v2alpha_messages.Function, recently created or
      updated GCF function.
    existing_function: pre-existing function.
      (cloudfunctions_v2alpha_messages.Function | None).
    function_ref: resource reference.
    release_track: the release track (alpha|beta|ga).

  Returns:
    updated_fields_set: frozenset[str], set of update mask fields.
  """

  updated_fields = set()
  if release_track == calliope_base.ReleaseTrack.GA:
    return updated_fields
  function.buildConfig.dockerRepository = (
      existing_function.buildConfig.dockerRepository
      if existing_function
      else None
  )
  if args.IsSpecified('docker_repository'):
    cmek_util.ValidateDockerRepositoryForFunction(
        args.docker_repository, function_ref
    )
  if args.IsSpecified('docker_repository') or args.IsSpecified(
      'clear_docker_repository'
  ):
    updated_docker_repository = (
        None
        if args.IsSpecified('clear_docker_repository')
        else args.docker_repository
    )
    function.buildConfig.dockerRepository = (
        cmek_util.NormalizeDockerRepositoryFormat(updated_docker_repository)
    )
    if (
        existing_function is None
        or function.buildConfig.dockerRepository
        != existing_function.buildConfig.dockerRepository
    ):
      updated_fields.add('build_config.docker_repository')
  if function.kmsKeyName and not function.buildConfig.dockerRepository:
    raise calliope_exceptions.RequiredArgumentException(
        '--docker-repository',
        (
            'A Docker repository must be specified when a KMS key is configured'
            ' for the function.'
        ),
    )
  return updated_fields


def _SetInvokerPermissions(args, function, is_new_function):
  """Add the IAM binding for the invoker role on the Cloud Run service, if applicable.

  Args:
    args: argparse.Namespace, arguments that this command was invoked with
    function: cloudfunctions_v2alpha_messages.Function, recently created or
      updated GCF function
    is_new_function: bool, true if the function is being created

  Returns:
    None
  """
  # This condition will be truthy if the user provided either
  # `--allow-unauthenticated` or `--no-allow-unauthenticated`. In other
  # words, it is only falsey when neither of those two flags is provided.
  if args.IsSpecified('allow_unauthenticated'):
    allow_unauthenticated = args.allow_unauthenticated
  else:
    if not is_new_function:
      # The function already exists, and the user didn't request any change to
      # the permissions. There is nothing to do in this case.
      return

    allow_unauthenticated = console_io.PromptContinue(
        prompt_string=(
            'Allow unauthenticated invocations of new function [{}]?'.format(
                args.NAME
            )
        ),
        default=False,
    )

  if is_new_function and not allow_unauthenticated:
    # No permissions to grant nor remove on the new function.
    return

  run_util.AddOrRemoveInvokerBinding(
      function,
      add_binding=allow_unauthenticated,
      member=serverless_operations.ALLOW_UNAUTH_POLICY_BINDING_MEMBER,
  )


def _GetFunction(client, messages, function_ref):
  """Get function and return None if doesn't exist.

  Args:
    client: apitools client, the GCFv2 API client
    messages: messages module, the GCFv2 message stubs
    function_ref: GCFv2 functions resource reference

  Returns:
    function: cloudfunctions_v2alpha_messages.Function, fetched GCFv2 function
  """
  try:
    # We got response for a GET request, so a function exists.
    return client.projects_locations_functions.Get(
        messages.CloudfunctionsProjectsLocationsFunctionsGetRequest(
            name=function_ref.RelativeName()
        )
    )
  except apitools_exceptions.HttpError as error:
    if error.status_code == six.moves.http_client.NOT_FOUND:
      return None
    raise


def _CreateAndWait(client, messages, function_ref, function):
  """Create a function.

  This does not include setting the invoker permissions.

  Args:
    client: The GCFv2 API client.
    messages: The GCFv2 message stubs.
    function_ref: The GCFv2 functions resource reference.
    function: The function to create.

  Returns:
    None
  """
  function_parent = 'projects/{}/locations/{}'.format(
      api_util.GetProject(), function_ref.locationsId
  )

  create_request = (
      messages.CloudfunctionsProjectsLocationsFunctionsCreateRequest(
          parent=function_parent,
          functionId=function_ref.Name(),
          function=function,
      )
  )
  operation = client.projects_locations_functions.Create(create_request)
  operation_description = 'Deploying function'

  api_util.WaitForOperation(
      client, messages, operation, operation_description, _EXTRA_STAGES
  )


def _UpdateAndWait(
    client, messages, function_ref, function, updated_fields_set
):
  """Update a function.

  This does not include setting the invoker permissions.

  Args:
    client: The GCFv2 API client.
    messages: The GCFv2 message stubs.
    function_ref: The GCFv2 functions resource reference.
    function: The function to update.
    updated_fields_set: A set of update mask fields.

  Returns:
    None
  """
  if updated_fields_set:
    updated_fields = list(updated_fields_set)
    updated_fields.sort()
    update_mask = ','.join(updated_fields)

    update_request = (
        messages.CloudfunctionsProjectsLocationsFunctionsPatchRequest(
            name=function_ref.RelativeName(),
            updateMask=update_mask,
            function=function,
        )
    )

    operation = client.projects_locations_functions.Patch(update_request)
    operation_description = 'Updating function (may take a while)'

    api_util.WaitForOperation(
        client, messages, operation, operation_description, _EXTRA_STAGES
    )
  else:
    log.status.Print('Nothing to update.')


def Run(args, release_track):
  """Runs a function deployment with the given args."""
  client = api_util.GetClientInstance(release_track=release_track)
  messages = api_util.GetMessagesModule(release_track=release_track)

  function_ref = args.CONCEPTS.name.Parse()

  _ValidateV1OnlyFlags(args, release_track)

  existing_function = _GetFunction(client, messages, function_ref)

  is_new_function = existing_function is None
  if is_new_function and not args.runtime:
    if not console_io.CanPrompt():
      raise calliope_exceptions.RequiredArgumentException(
          'runtime', 'Flag `--runtime` is required for new functions.'
      )
    gcf_client = api_client_v2.FunctionsClient(release_track=release_track)
    runtimes = [
        r.name
        for r in gcf_client.ListRuntimes(function_ref.locationsId).runtimes
    ]
    idx = console_io.PromptChoice(
        runtimes, message='Please select a runtime:\n'
    )
    args.runtime = runtimes[idx]
    log.status.Print(
        'To skip this prompt, add `--runtime={}` to your command next time.\n'
        .format(args.runtime)
    )

  if (
      flags.ShouldUseGen2()
      and existing_function
      and str(existing_function.environment) == 'GEN_1'
  ):
    raise exceptions.InvalidArgumentException(
        '--gen2',
        "Function already exist in 1st gen, can't change the environment.",
    )

  if existing_function and existing_function.serviceConfig:
    has_all_traffic_on_latest_revision = (
        existing_function.serviceConfig.allTrafficOnLatestRevision
    )
    if (
        has_all_traffic_on_latest_revision is not None
        and not has_all_traffic_on_latest_revision
    ):
      log.warning(_LATEST_REVISION_TRAFFIC_WARNING_MESSAGE)

  event_trigger, trigger_updated_fields = _GetEventTrigger(
      args, messages, existing_function
  )

  build_config, build_updated_fields = _GetBuildConfig(
      args,
      client,
      messages,
      function_ref.locationsId,
      function_ref.Name(),
      existing_function,
  )

  service_config, service_updated_fields = _GetServiceConfig(
      args, messages, existing_function
  )

  labels_value, labels_updated_fields = _GetLabels(
      args, messages, existing_function
  )

  # cs/symbol:google.cloud.functions.v2main.Function$
  function = messages.Function(
      name=function_ref.RelativeName(),
      buildConfig=build_config,
      eventTrigger=event_trigger,
      serviceConfig=service_config,
      labels=labels_value,
  )

  cmek_updated_fields = _SetCmekFields(
      args, function, existing_function, function_ref, release_track
  )
  docker_repository_updated_fields = _SetDockerRepositoryConfig(
      args, function, existing_function, function_ref, release_track
  )

  api_enablement.PromptToEnableApiIfDisabled('cloudbuild.googleapis.com')
  api_enablement.PromptToEnableApiIfDisabled('artifactregistry.googleapis.com')
  if is_new_function:
    _CreateAndWait(client, messages, function_ref, function)
  else:
    _UpdateAndWait(
        client,
        messages,
        function_ref,
        function,
        frozenset.union(
            trigger_updated_fields,
            build_updated_fields,
            service_updated_fields,
            labels_updated_fields,
            cmek_updated_fields,
            docker_repository_updated_fields,
        ),
    )

  function = client.projects_locations_functions.Get(
      messages.CloudfunctionsProjectsLocationsFunctionsGetRequest(
          name=function_ref.RelativeName()
      )
  )

  if event_trigger is None:
    _SetInvokerPermissions(args, function, is_new_function)

  log.status.Print(
      'You can view your function in the Cloud Console here: '
      + 'https://console.cloud.google.com/functions/details/{}/{}?project={}\n'
      .format(
          function_ref.locationsId, function_ref.Name(), api_util.GetProject()
      )
  )

  return function
