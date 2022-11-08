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

"""A library that is used to support Functions commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import functools
import json
import os
import re

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.functions.v1 import exceptions
from googlecloudsdk.api_lib.functions.v1 import operations
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import exceptions as exceptions_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.calliope import exceptions as base_exceptions
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import encoding

import six.moves.http_client

_DEPLOY_WAIT_NOTICE = 'Deploying function (may take a while - up to 2 minutes)'

_FUNCTION_NAME_RE = re.compile(r'^[A-Za-z](?:[-_A-Za-z0-9]{0,61}[A-Za-z0-9])?$')
_FUNCTION_NAME_ERROR = (
    'Function name must contain only Latin letters, digits and a '
    'hyphen (-). It must start with letter, must not end with a hyphen, '
    'and must be at most 63 characters long.')

_TOPIC_NAME_RE = re.compile(r'^[a-zA-Z][\-\._~%\+a-zA-Z0-9]{2,254}$')
_TOPIC_NAME_ERROR = (
    'Topic must contain only Latin letters (lower- or upper-case), digits and '
    'the characters - + . _ ~ %. It must start with a letter and be from 3 to '
    '255 characters long.')

_DEPRECATED_NODEJS_RUNTIMES = (
    'nodejs6',
    'nodejs8',
    'nodejs10',
    )
_DEPRECATED_GO_RUNTIMES = ('go111',)
_SUGGESTED_NODEJS_RUNTIME = 'nodejs12'
_SUGGESTED_GO_RUNTIME = 'go113'

_BUCKET_RESOURCE_URI_RE = re.compile(r'^projects/_/buckets/.{3,222}$')

_KMS_KEY_RE = re.compile(
    r'^projects/[^/]+/locations/(?P<location>[^/]+)/keyRings/[a-zA-Z0-9_-]+'
    '/cryptoKeys/[a-zA-Z0-9_-]+$')
_DOCKER_REPOSITORY_RE = re.compile(
    r'^projects/(?P<project>[^/]+)/locations/(?P<location>[^/]+)'
    '/repositories/[a-z]([a-z0-9-]*[a-z0-9])?$')

_API_NAME = 'cloudfunctions'
_API_VERSION = 'v1'


def _GetApiVersion(track=calliope_base.ReleaseTrack.GA):  # pylint: disable=unused-argument
  """Returns the current cloudfunctions Api Version configured in the sdk.

  NOTE: Currently the value is hard-coded to v1, and surface/functions/deploy.py
  assumes this to parse OperationMetadataV1 from the response.
  Please change the parsing if more versions should be supported.

  Args:
    track: The gcloud track.

  Returns:
    The current cloudfunctions Api Version.
  """
  return _API_VERSION


def GetApiClientInstance(track=calliope_base.ReleaseTrack.GA):
  return apis.GetClientInstance(_API_NAME, _GetApiVersion(track))


def GetResourceManagerApiClientInstance():
  return apis.GetClientInstance('cloudresourcemanager', 'v1')


def GetApiMessagesModule(track=calliope_base.ReleaseTrack.GA):
  return apis.GetMessagesModule(_API_NAME, _GetApiVersion(track))


def GetFunctionRef(name):
  return resources.REGISTRY.Parse(
      name, params={
          'projectsId': properties.VALUES.core.project.Get(required=True),
          'locationsId': properties.VALUES.functions.region.Get()},
      collection='cloudfunctions.projects.locations.functions')


_ID_CHAR = '[a-zA-Z0-9_]'
_P_CHAR = "[][~@#$%&.,?:;+*='()-]"
# capture: '{' ID_CHAR+ ('=' '*''*'?)? '}'
# Named wildcards may be written in curly brackets (e.g. {variable}). The
# value that matched this parameter will be included  in the event
# parameters.
_CAPTURE = r'(\{' + _ID_CHAR + r'(=\*\*?)?})'
# segment: (ID_CHAR | P_CHAR)+
_SEGMENT = '((' + _ID_CHAR + '|' + _P_CHAR + ')+)'
# part: '/' segment | capture
_PART = '(/(' + _SEGMENT + '|' + _CAPTURE + '))'
# path: part+ (but first / is optional)
_PATH = '(/?(' + _SEGMENT + '|' + _CAPTURE + ')' + _PART + '*)'

_PATH_RE_ERROR = ('Path must be a slash-separated list of segments and '
                  'captures. For example, [users/{userId}/profilePic].')


def GetHttpErrorMessage(error):
  """Returns a human readable string representation from the http response.

  Args:
    error: HttpException representing the error response.

  Returns:
    A human readable string representation of the error.
  """
  status = error.response.status
  code = error.response.reason
  message = ''
  try:
    data = json.loads(error.content)
    if 'error' in data:
      error_info = data['error']
      if 'message' in error_info:
        message = error_info['message']
      violations = _GetViolationsFromError(error)
      if violations:
        message += '\nProblems:\n' + violations
      if status == 403:
        permission_issues = _GetPermissionErrorDetails(error_info)
        if permission_issues:
          message += '\nPermission Details:\n' + permission_issues
  except (ValueError, TypeError):
    message = error.content
  return 'ResponseError: status=[{0}], code=[{1}], message=[{2}]'.format(
      status, code, encoding.Decode(message))


def _ValidateArgumentByRegexOrRaise(argument, regex, error_message):
  if isinstance(regex, str):
    match = re.match(regex, argument)
  else:
    match = regex.match(argument)
  if not match:
    raise arg_parsers.ArgumentTypeError(
        "Invalid value '{0}': {1}".format(argument, error_message))
  return argument


def ValidateFunctionNameOrRaise(name):
  """Checks if a function name provided by user is valid.

  Args:
    name: Function name provided by user.
  Returns:
    Function name.
  Raises:
    ArgumentTypeError: If the name provided by user is not valid.
  """
  return _ValidateArgumentByRegexOrRaise(name, _FUNCTION_NAME_RE,
                                         _FUNCTION_NAME_ERROR)


def ValidateAndStandarizeBucketUriOrRaise(bucket):
  """Checks if a bucket uri provided by user is valid.

  If the Bucket uri is valid, converts it to a standard form.

  Args:
    bucket: Bucket uri provided by user.
  Returns:
    Sanitized bucket uri.
  Raises:
    ArgumentTypeError: If the name provided by user is not valid.
  """
  if _BUCKET_RESOURCE_URI_RE.match(bucket):
    bucket_ref = storage_util.BucketReference.FromUrl(bucket)
  else:
    try:
      bucket_ref = storage_util.BucketReference.FromArgument(
          bucket, require_prefix=False)
    except argparse.ArgumentTypeError as e:
      raise arg_parsers.ArgumentTypeError(
          "Invalid value '{}': {}".format(bucket, e))

  # strip any extrenuous '/' and append single '/'
  bucket = bucket_ref.ToUrl().rstrip('/') + '/'
  return bucket


def ValidatePubsubTopicNameOrRaise(topic):
  """Checks if a Pub/Sub topic name provided by user is valid.

  Args:
    topic: Pub/Sub topic name provided by user.
  Returns:
    Topic name.
  Raises:
    ArgumentTypeError: If the name provided by user is not valid.
  """
  topic = _ValidateArgumentByRegexOrRaise(topic, _TOPIC_NAME_RE,
                                          _TOPIC_NAME_ERROR)
  return topic


def ValidateRuntime(runtime):
  """Checks if runtime is deprecated based on runtimes.textproto.

  Args:
    runtime: str, the runtime.

  Returns:
    warning: None|str, the warning if deprecated
  """
  # TODO(b/178004928): replace hardcoded warnings with ListRuntimes api
  if runtime in _DEPRECATED_NODEJS_RUNTIMES:
    return ('The {} runtime is deprecated on Cloud Functions. '
            'Please migrate to a newer Node.js version '
            '(--runtime={}). '
            'See https://cloud.google.com/functions/docs/migrating/'
            'nodejs-runtimes'.format(runtime, _SUGGESTED_NODEJS_RUNTIME))
  elif runtime in _DEPRECATED_GO_RUNTIMES:
    return ('The {} runtime is deprecated on Cloud Functions. '
            'Please migrate to a newer Golang version '
            '(--runtime={}).'.format(runtime, _SUGGESTED_GO_RUNTIME))
  return None


def ValidateDirectoryExistsOrRaiseFunctionError(directory):
  """Checks if a source directory exists.

  Args:
    directory: A string: a local path to directory provided by user.
  Returns:
    The argument provided, if found valid.
  Raises:
    ArgumentTypeError: If the user provided a directory which is not valid.
  """
  if not os.path.exists(directory):
    raise exceptions.FunctionsError(
        'argument `--source`: Provided directory does not exist')
  if not os.path.isdir(directory):
    raise exceptions.FunctionsError(
        'argument `--source`: Provided path does not point to a directory')
  return directory


def ValidatePathOrRaise(path):
  """Check if path provided by user is valid.

  Args:
    path: A string: resource path
  Returns:
    The argument provided, if found valid.
  Raises:
    ArgumentTypeError: If the user provided a path which is not valid
  """
  path = _ValidateArgumentByRegexOrRaise(path, _PATH, _PATH_RE_ERROR)
  return path


def ValidateKMSKeyForFunction(kms_key, function_ref):
  """Checks that the KMS key is compatible with the function.

  Args:
    kms_key: Fully qualified KMS key name.
    function_ref: Function resource reference.

  Raises:
    InvalidArgumentException: If the specified KMS key is not compatible with
      the function.
  """
  function_project = function_ref.projectsId
  function_location = function_ref.locationsId
  kms_key_match = _KMS_KEY_RE.search(kms_key)
  if kms_key_match:
    kms_keyring_location = kms_key_match.group('location')
    if kms_keyring_location == 'global':
      raise base_exceptions.InvalidArgumentException(
          '--kms-key', 'Global KMS keyrings are not allowed.')
    if function_location != kms_keyring_location:
      raise base_exceptions.InvalidArgumentException(
          '--kms-key',
          'KMS keyrings should be created in the same region as the function.')


def ValidateDockerRepositoryForFunction(docker_repository, function_ref):
  """Checks that the Docker repository is compatible with the function.

  Args:
    docker_repository: Fully qualified Docker repository resource name.
    function_ref: Function resource reference.

  Raises:
    InvalidArgumentException: If the specified Docker repository is not
      compatible with the function.
  """
  function_project = function_ref.projectsId
  function_location = function_ref.locationsId
  repo_match = _DOCKER_REPOSITORY_RE.search(docker_repository)
  if repo_match:
    repo_project = repo_match.group('project')
    repo_location = repo_match.group('location')
    if function_project != repo_project and function_project.isdigit(
    ) == repo_project.isdigit():
      raise base_exceptions.InvalidArgumentException(
          '--docker-repository',
          'Cross-project repositories are not supported.')
    if function_location != repo_location:
      raise base_exceptions.InvalidArgumentException(
          '--docker-repository',
          'Cross-location repositories are not supported.')


def _GetViolationsFromError(error):
  """Looks for violations descriptions in error message.

  Args:
    error: HttpError containing error information.
  Returns:
    String of newline-separated violations descriptions.
  """
  error_payload = exceptions_util.HttpErrorPayload(error)
  errors = []
  errors.extend(
      ['{}:\n{}'.format(k, v) for k, v in error_payload.violations.items()])
  errors.extend([
      '{}:\n{}'.format(k, v) for k, v in error_payload.field_violations.items()
  ])
  if errors:
    return '\n'.join(errors) + '\n'
  return ''


def _GetPermissionErrorDetails(error_info):
  """Looks for permission denied details in error message.

  Args:
    error_info: json containing error information.
  Returns:
    string containing details on permission issue and suggestions to correct.
  """
  try:
    if 'details' in error_info:
      details = error_info['details'][0]
      if 'detail' in details:
        return details['detail']

  except (ValueError, TypeError):
    pass
  return None


def CatchHTTPErrorRaiseHTTPException(func):
  """Decorator that catches HttpError and raises corresponding exception."""

  @functools.wraps(func)
  def CatchHTTPErrorRaiseHTTPExceptionFn(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except apitools_exceptions.HttpError as error:
      core_exceptions.reraise(
          base_exceptions.HttpException(GetHttpErrorMessage(error)))

  return CatchHTTPErrorRaiseHTTPExceptionFn


def FormatTimestamp(timestamp):
  """Formats a timestamp which will be presented to a user.

  Args:
    timestamp: Raw timestamp string in RFC3339 UTC "Zulu" format.

  Returns:
    Formatted timestamp string.
  """
  return re.sub(r'(\.\d{3})\d*Z$', r'\1', timestamp.replace('T', ' '))


@CatchHTTPErrorRaiseHTTPException
def GetFunction(function_name):
  """Returns the Get method on function response, None if it doesn't exist."""
  client = GetApiClientInstance()
  messages = client.MESSAGES_MODULE
  try:
    # We got response for a get request so a function exists.
    return client.projects_locations_functions.Get(
        messages.CloudfunctionsProjectsLocationsFunctionsGetRequest(
            name=function_name))
  except apitools_exceptions.HttpError as error:
    if error.status_code == six.moves.http_client.NOT_FOUND:
      # The function has not been found.
      return None
    raise


@CatchHTTPErrorRaiseHTTPException
def ListRegions():
  """Returns the list of regions where GCF 1st Gen is supported."""
  client = GetApiClientInstance()
  messages = client.MESSAGES_MODULE
  return list_pager.YieldFromList(
      service=client.projects_locations,
      request=messages.CloudfunctionsProjectsLocationsListRequest(
          name='projects/' + properties.VALUES.core.project.Get(required=True)),
      field='locations',
      batch_size_attribute='pageSize')


# TODO(b/130604453): Remove try_set_invoker option
@CatchHTTPErrorRaiseHTTPException
def WaitForFunctionUpdateOperation(op, try_set_invoker=None,
                                   on_every_poll=None):
  """Wait for the specied function update to complete.

  Args:
    op: Cloud operation to wait on.
    try_set_invoker: function to try setting invoker, see above TODO.
    on_every_poll: list of functions to execute every time we poll.
                   Functions should take in Operation as an argument.
  """
  client = GetApiClientInstance()
  operations.Wait(op, client.MESSAGES_MODULE, client, _DEPLOY_WAIT_NOTICE,
                  try_set_invoker=try_set_invoker,
                  on_every_poll=on_every_poll)


@CatchHTTPErrorRaiseHTTPException
def PatchFunction(function, fields_to_patch):
  """Call the api to patch a function based on updated fields.

  Args:
    function: the function to patch
    fields_to_patch: the fields to patch on the function

  Returns:
    The cloud operation for the Patch.
  """
  client = GetApiClientInstance()
  messages = client.MESSAGES_MODULE
  fields_to_patch_str = ','.join(sorted(fields_to_patch))
  return client.projects_locations_functions.Patch(
      messages.CloudfunctionsProjectsLocationsFunctionsPatchRequest(
          cloudFunction=function,
          name=function.name,
          updateMask=fields_to_patch_str,
      )
  )


@CatchHTTPErrorRaiseHTTPException
def CreateFunction(function, location):
  """Call the api to create a function.

  Args:
    function: the function to create
    location: location for function

  Returns:
    Cloud operation for the create.
  """
  client = GetApiClientInstance()
  messages = client.MESSAGES_MODULE
  return client.projects_locations_functions.Create(
      messages.CloudfunctionsProjectsLocationsFunctionsCreateRequest(
          location=location, cloudFunction=function))


@CatchHTTPErrorRaiseHTTPException
def GetFunctionIamPolicy(function_resource_name):
  client = GetApiClientInstance()
  messages = client.MESSAGES_MODULE
  return client.projects_locations_functions.GetIamPolicy(
      messages.CloudfunctionsProjectsLocationsFunctionsGetIamPolicyRequest(
          resource=function_resource_name))


@CatchHTTPErrorRaiseHTTPException
def AddFunctionIamPolicyBinding(function_resource_name,
                                member='allUsers',
                                role='roles/cloudfunctions.invoker'):
  client = GetApiClientInstance()
  messages = client.MESSAGES_MODULE
  policy = GetFunctionIamPolicy(function_resource_name)
  iam_util.AddBindingToIamPolicy(messages.Binding, policy, member, role)
  return client.projects_locations_functions.SetIamPolicy(
      messages.CloudfunctionsProjectsLocationsFunctionsSetIamPolicyRequest(
          resource=function_resource_name,
          setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy)))


@CatchHTTPErrorRaiseHTTPException
def RemoveFunctionIamPolicyBindingIfFound(
    function_resource_name,
    member='allUsers',
    role='roles/cloudfunctions.invoker'):
  """Removes the specified policy binding if it is found."""
  client = GetApiClientInstance()
  messages = client.MESSAGES_MODULE
  policy = GetFunctionIamPolicy(function_resource_name)
  if iam_util.BindingInPolicy(policy, member, role):
    iam_util.RemoveBindingFromIamPolicy(policy, member, role)
    client.projects_locations_functions.SetIamPolicy(
        messages.CloudfunctionsProjectsLocationsFunctionsSetIamPolicyRequest(
            resource=function_resource_name,
            setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy)))
    return True
  else:
    return False


@CatchHTTPErrorRaiseHTTPException
def CanAddFunctionIamPolicyBinding(project):
  """Returns True iff the caller can add policy bindings for project."""
  client = GetResourceManagerApiClientInstance()
  messages = client.MESSAGES_MODULE
  needed_permissions = [
      'resourcemanager.projects.getIamPolicy',
      'resourcemanager.projects.setIamPolicy']
  iam_request = messages.CloudresourcemanagerProjectsTestIamPermissionsRequest(
      resource=project,
      testIamPermissionsRequest=messages.TestIamPermissionsRequest(
          permissions=needed_permissions))
  iam_response = client.projects.TestIamPermissions(iam_request)
  can_add = True
  for needed_permission in needed_permissions:
    if needed_permission not in iam_response.permissions:
      can_add = False
  return can_add
