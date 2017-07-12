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
import os
import random
import re
import string

from googlecloudsdk.api_lib.functions import cloud_storage as storage
from googlecloudsdk.api_lib.functions import exceptions
from googlecloudsdk.api_lib.functions import util
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import archive


def GetLocalPath(args):
  return args.local_path or '.'


def GetIgnoreFilesRegex(include_ignored_files):
  if include_ignored_files:
    return None
  else:
    return r'(node_modules{}.*)|(node_modules)'.format(re.escape(os.sep))


def CreateSourcesZipFile(zip_dir, source_path, include_ignored_files):
  """Prepare zip file with source of the function to upload.

  Args:
    zip_dir: str, directory in which zip file will be located. Name of the file
             will be `fun.zip`.
    source_path: str, directory containing the sources to be zipped.
    include_ignored_files: bool, indicates whether `node_modules` directory and
                           its content will be included in the zip.
  Returns:
    Path to the zip file (str).
  Raises:
    FunctionsError
  """
  zip_file_name = os.path.join(zip_dir, 'fun.zip')
  try:
    if include_ignored_files:
      log.info('Not including node_modules in deployed code. To include '
               'node_modules in uploaded code use --include-ignored-files '
               'flag.')
    archive.MakeZipFromDir(
        zip_file_name,
        source_path,
        skip_file_regex=GetIgnoreFilesRegex(include_ignored_files))
  except ValueError as e:
    raise exceptions.FunctionsError(
        'Error creating a ZIP archive with the source code '
        'for directory {0}: {1}'.format(source_path, str(e)))
  return zip_file_name


def _GenerateRemoteZipFileName(function_name):
  sufix = ''.join(random.choice(string.ascii_lowercase) for _ in range(12))
  return '{0}-{1}-{2}.zip'.format(
      properties.VALUES.functions.region.Get(), function_name, sufix)


def UploadFile(source, function_name, stage_bucket):
  remote_zip_file = _GenerateRemoteZipFileName(function_name)
  gcs_url = storage.BuildRemoteDestination(stage_bucket, remote_zip_file)
  if storage.Upload(source, gcs_url) != 0:
    raise exceptions.FunctionsError(
        'Failed to upload the function source code to the bucket {0}'
        .format(stage_bucket))
  return gcs_url


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
  resource_type = util.input_trigger_provider_registry.Event(
      trigger_provider, trigger_event).resource_type
  params = {}
  if resource_type.value.collection_id == 'cloudresourcemanager.projects':
    params['projectId'] = properties.VALUES.core.project.GetOrFail
  elif resource_type.value.collection_id == 'pubsub.projects.topics':
    params['projectsId'] = properties.VALUES.core.project.GetOrFail
  elif resource_type.value.collection_id == 'cloudfunctions.projects.buckets':
    pass

  ref = resources.REGISTRY.Parse(
      trigger_resource,
      params,
      collection=resource_type.value.collection_id,
  )
  return ref.RelativeName()


def DeduceAndCheckArgs(args):
  """Check command arguments and deduce information if possible.

  0. Check if --source-revision, --source-branch or --source-tag are present
     when --source-url is not present. (and fail if it is so)
  1. Check if --source-bucket is present when --source-url is present.
  2. Validate if local-path is a directory.
  3. Check if --source-path is present when --source-url is present.
  4. Check if --trigger-event, --trigger-resource or --trigger-path are
     present when --trigger-provider is not present. (and fail if it is so)
  5. Check --trigger-* family of flags deducing default values if possible and
     necessary.

  Args:
    args: The argument namespace.

  Returns:
    None, when using HTTPS trigger. Otherwise a dictionary containing
    trigger_provider, trigger_event, and trigger_resource.
  """
  # This function should raise ArgumentParsingError, but:
  # 1. ArgumentParsingError requires the  argument returned from add_argument)
  #    and Args() method is static. So there is no elegant way to save it
  #    to be reused here.
  # 2. _CheckArgs() is invoked from Run() and ArgumentParsingError thrown
  #    from Run are not caught.
  _ValidateSourceArgs(args)
  _ValidateTriggerArgs(args)
  return _CheckTriggerProviderArgs(args)


def _ValidateSourceArgs(args):
  """Check if args related to source code to deploy are valid.

  Args:
    args: parsed command line arguments.
  Raises:
    FunctionsError.
  """
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
    if args.stage_bucket is None:
      raise exceptions.FunctionsError(
          'argument --stage-bucket: required when the function is deployed '
          'from a local directory (when argument --source-url is not '
          'provided)')
    util.ValidateDirectoryExistsOrRaiseFunctionError(GetLocalPath(args))
  else:
    if args.source_path is None:
      raise exceptions.FunctionsError(
          'argument --source-path: required when argument --source-url is '
          'provided')


def _ValidateTriggerArgs(args):
  """Check if args related function triggers are valid.

  Args:
    args: parsed command line arguments.
  Raises:
    FunctionsError.
  """

  if args.trigger_provider is None and (args.trigger_event is not None or
                                        args.trigger_resource is not None):
    raise exceptions.FunctionsError(
        '--trigger-event, --trigger-resource, and --trigger-path may only '
        'be used with --trigger-provider')


def _BucketTrigger(trigger_bucket):
  bucket_name = trigger_bucket[5:-1]
  return {
      'trigger_provider': 'cloud.storage',
      'trigger_event': 'object.change',
      'trigger_resource': bucket_name,
  }


def _TopicTrigger(trigger_topic):
  return {
      'trigger_provider': 'cloud.pubsub',
      'trigger_event': 'topic.publish',
      'trigger_resource': trigger_topic,
  }


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
    None, when using HTTPS trigger. Otherwise a dictionary containing
    trigger_provider, trigger_event, and trigger_resource.
  """
  if args.trigger_http:
    return None
  if args.trigger_bucket:
    return _BucketTrigger(args.trigger_bucket)
  if args.trigger_topic:
    return _TopicTrigger(args.trigger_topic)

  # TODO(b/36020181): move validation to a separate function.
  trigger_provider = args.trigger_provider
  trigger_event = args.trigger_event
  trigger_resource = args.trigger_resource
  # check and infer correct usage of flags accompanying --trigger-provider
  if trigger_event is None:
    trigger_event = util.input_trigger_provider_registry.Provider(
        trigger_provider).default_event.label
  elif trigger_event not in util.input_trigger_provider_registry.EventsLabels(
      trigger_provider):
    raise exceptions.FunctionsError('You can use only one of [' + ','.join(
        util.input_trigger_provider_registry.EventsLabels(trigger_provider)
    ) + '] with --trigger-provider=' + trigger_provider)
  # checked if Event Type is correct

  if trigger_resource is None and util.input_trigger_provider_registry.Event(
      trigger_provider, trigger_event).resource_type != util.Resources.PROJECT:
    raise exceptions.FunctionsError(
        'You must provide --trigger-resource when using '
        '--trigger-provider={0} and --trigger-event={1}'.format(
            trigger_provider, trigger_event))
  # checked if Resource Type and Path were provided or not as required

  resource_type = util.input_trigger_provider_registry.Event(
      trigger_provider, trigger_event).resource_type
  if resource_type == util.Resources.TOPIC:
    trigger_resource = util.ValidatePubsubTopicNameOrRaise(
        trigger_resource)
  elif resource_type == util.Resources.BUCKET:
    trigger_resource = storage_util.BucketReference.FromBucketUrl(
        trigger_resource).bucket
  elif resource_type == util.Resources.PROJECT:
    if trigger_resource:
      properties.VALUES.core.project.Validate(trigger_resource)
  else:
    # Check if programmer allowed other methods in
    # util.PROVIDER_EVENT_RESOURCE but forgot to update code here
    raise core_exceptions.InternalError()
  # checked if provided resource and path have correct format
  return {
      'trigger_provider': trigger_provider,
      'trigger_event': trigger_event,
      'trigger_resource': trigger_resource,
  }
