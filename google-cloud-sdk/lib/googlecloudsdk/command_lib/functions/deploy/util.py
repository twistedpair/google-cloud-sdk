# Copyright 2016 Google Inc. All Rights Reserved.
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

"""'functions deploy' utilities."""
import argparse

from googlecloudsdk.api_lib.functions import exceptions
from googlecloudsdk.api_lib.functions import util
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def GetLocalPath(args):
  return args.local_path or args.source or '.'


def ConvertTriggerArgsToRelativeName(trigger_provider, trigger_event,
                                     trigger_resource):
  """Prepares resource field for Function EventTrigger to use in API call.

  API uses relative resource name in EventTrigger message field. The
  structure of that identifier depends on the resource type which depends on
  combination of --trigger-provider and --trigger-event arguments' values.
  This function chooses the appropriate form, fills it with required data and
  returns as a string.

  Args:
    trigger_provider: The --trigger-provider flag value.
    trigger_event: The --trigger-event flag value.
    trigger_resource: The --trigger-resource flag value.
  Returns:
    Relative resource name to use in EventTrigger field.
  """
  project = properties.VALUES.core.project.Get(required=True)
  resource_type = util.trigger_provider_registry.Event(
      trigger_provider, trigger_event).resource_type
  resources.REGISTRY.SetParamDefault(api='cloudresourcemanager',
                                     collection=None,
                                     param='projectId',
                                     resolver=project)
  resources.REGISTRY.SetParamDefault(api='pubsub',
                                     collection=None,
                                     param='projectsId',
                                     resolver=project)
  resources.REGISTRY.SetParamDefault(api='cloudfunctions',
                                     collection=None,
                                     param='projectId',
                                     resolver=project)
  ref = resources.REGISTRY.Parse(
      trigger_resource,
      collection=resource_type.value.collection_id
  )
  return ref.RelativeName()


def DeduceAndCheckArgs(args):
  """Check command arguments and deduce information if possible.

  0. Check if --source-revision, --source-branch or --source-tag are present
     when --source-url is not present. (and fail if it is so)
  1. Check if --source-bucket is present when --source-url is present.
  2. Validate if local-path is a directory.
  3. Check if --source-path is present when --source-url is present.
  4. Warn about use of deprecated flags (if deprecated flags were used)
  5. Check if --trigger-event, --trigger-resource or --trigger-path are
     present when --trigger-provider is not present. (and fail if it is so)
  6. Check --trigger-* family of flags deducing default values if possible and
     necessary.

  Args:
    args: The argument namespace.

  Returns:
    args with all implicit information turned into explicit form.
  """
  # This function should raise ArgumentParsingError, but:
  # 1. ArgumentParsingError requires the  argument returned from add_argument)
  #    and Args() method is static. So there is no elegant way to save it
  #    to be reused here.
  # 2. _CheckArgs() is invoked from Run() and ArgumentParsingError thrown
  #    from Run are not caught.
  if args.source_url is None:
    if args.source_revision is not None:
      raise exceptions.FunctionsError(
          'argument --source-revision: can be given only if argument '
          '--source-url is provided')
    if args.source_branch is not None:
      raise exceptions.FunctionsError(
          'argument --source-branch: can be given only if argument '
          '--source-url is provided')
    if args.source_tag is not None:
      raise exceptions.FunctionsError(
          'argument --source-tag: can be given only if argument '
          '--source-url is provided')
    stage_bucket = args.bucket or args.stage_bucket
    if stage_bucket is None:
      raise exceptions.FunctionsError(
          'argument --stage-bucket: required when the function is deployed '
          'from a local directory (when argument --source-url is not '
          'provided)')
    util.ValidateDirectoryExistsOrRaiseFunctionError(GetLocalPath(args))
  else:
    if args.source is None and args.source_path is None:
      raise exceptions.FunctionsError(
          'argument --source-path: required when argument --source-url is '
          'provided')

  if args.bucket is not None:
    log.warn('--bucket flag is deprecated. Use --stage-bucket instead.')
  if args.source is not None:
    log.warn('--source flag is deprecated. Use --local-path (for sources on '
             'local file system) or --source-path (for sources in Cloud '
             'Source Repositories) instead.')
  if args.trigger_gs_uri is not None:
    log.warn('--trigger-gs-uri flag is deprecated. Use --trigger-bucket '
             'instead.')

  if args.trigger_params:
    log.warn('The --trigger-params argument is deprecated and will soon be '
             'removed. Please use --trigger-path instead.')
    if args.trigger_path:
      raise exceptions.FunctionsError(
          'Only one of --trigger-path and --trigger-params may be used.')
    args.trigger_path = args.trigger_params['path']
  if args.trigger_provider is None and ((args.trigger_event is not None) or
                                        (args.trigger_resource is not None) or
                                        (args.trigger_path is not None)):
    raise exceptions.FunctionsError(
        '--trigger-event, --trigger-resource, and --trigger-path may only '
        'be used with --trigger-provider')
  if args.trigger_provider is not None:
    return _CheckTriggerProviderArgs(args)


def _CheckTriggerProviderArgs(args):
  """Check --trigger-provider dependent arguments and deduce if possible.

  0. Check if --trigger-provider is correct.
  1. Check if --trigger-event is present, assign default if not.
  2. Check if --trigger-event is correct WRT to --trigger-provider.
  3. Check if --trigger-resource is present if necessary.
  4. Check if --trigger-resource is correct WRT to *-provider and *-event.
  5. Check if --trigger-path is present if necessary.
  6. Check if --trigger-path is not present if forbidden.
  7. Check if --trigger-path is correct if present.

  Args:
    args: The argument namespace.

  Returns:
    args with all implicit information turned into explicit form.
  """

  # Create a copy of namespace (copy.copy doesn't work here)
  result = argparse.Namespace(**vars(args))
  # check and infer correct usage of flags accompanying --trigger-provider
  if result.trigger_event is None:
    result.trigger_event = util.trigger_provider_registry.Provider(
        result.trigger_provider).default_event.label
  elif result.trigger_event not in util.trigger_provider_registry.EventsLabels(
      result.trigger_provider):
    raise exceptions.FunctionsError('You can use only one of [' + ','.join(
        util.trigger_provider_registry.EventsLabels(result.trigger_provider)
    ) + '] with --trigger-provider=' + result.trigger_provider)
  # checked if Event Type is correct

  if result.trigger_resource is None and util.trigger_provider_registry.Event(
      result.trigger_provider,
      result.trigger_event).resource_type != util.Resources.PROJECT:
    raise exceptions.FunctionsError(
        'You must provide --trigger-resource when using '
        '--trigger-provider={0} and --trigger-event={1}'.format(
            result.trigger_provider, result.trigger_event))
  path_allowance = util.trigger_provider_registry.Event(
      result.trigger_provider, result.trigger_event).path_obligatoriness
  if result.trigger_path is None and (
      path_allowance == util.Obligatoriness.REQUIRED):
    raise exceptions.FunctionsError(
        'You must provide --trigger-path when using '
        '--trigger-provider={0} and --trigger-event={1}'.format(
            result.trigger_provider, result.trigger_event))
  if result.trigger_path is not None and (
      path_allowance == util.Obligatoriness.FORBIDDEN):
    raise exceptions.FunctionsError(
        'You must not provide --trigger-path when using '
        '--trigger-provider={0} and --trigger-event={1}'.format(
            result.trigger_provider, result.trigger_event))
  # checked if Resource Type and Path were provided or not as required

  resource_type = util.trigger_provider_registry.Event(
      result.trigger_provider, result.trigger_event).resource_type
  if resource_type == util.Resources.TOPIC:
    result.trigger_resource = util.ValidatePubsubTopicNameOrRaise(
        result.trigger_resource)
  elif resource_type == util.Resources.BUCKET:
    result.trigger_resource = storage_util.BucketReference.FromBucketUrl(
        result.trigger_resource).bucket
  elif resource_type == util.Resources.PROJECT:
    if result.trigger_resource:
      properties.VALUES.core.project.Validate(result.trigger_resource)
  else:
    # Check if programmer allowed other methods in
    # util.PROVIDER_EVENT_RESOURCE but forgot to update code here
    raise core_exceptions.InternalError()
  if result.trigger_path is not None:
    util.ValidatePathOrRaise(result.trigger_path)
  # checked if provided resource and path have correct format
  return result
