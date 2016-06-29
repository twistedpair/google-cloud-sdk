# Copyright 2014 Google Inc. All Rights Reserved.
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

"""This module holds common flags used by the gcloud app commands."""
import argparse

from googlecloudsdk.api_lib.app import cloud_storage
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.app import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.appengine.api import appinfo
from googlecloudsdk.third_party.appengine.api import validation

SERVER_FLAG = base.Argument(
    '--server',
    help=argparse.SUPPRESS)

VERSION_FLAG = base.Argument(
    '--version',
    required=True,
    help='The version of the app that you want to operate on.')

# TODO(user): Add service globbing.
MODULES_ARG = base.Argument(
    'modules',
    nargs='+',
    help='One or more service names to perform this action on.  To select the '
    'default service for your app, use "default".')

MODULES_OPTIONAL_ARG = base.Argument(
    'modules',
    nargs='*',
    help='An optional list of service names to perform this action on.  To '
    'select the default service for your app, use "default".  If no services '
    'are given, all services are used.')

IGNORE_CERTS_FLAG = base.Argument(
    '--ignore-bad-certs',
    action='store_true',
    default=False,
    help=argparse.SUPPRESS)

LOG_SEVERITIES = ['debug', 'info', 'warning', 'error', 'critical']


def GetCodeBucket(api_client, project, bucket):
  """Gets a bucket reference for a Cloud Build.

  Args:
    api_client: appengine_api_client.AppengineApiClient to get the bucket.
    project: str, The name of the current project.
    bucket: str, The name of the bucket to use if specified explicitly.

  Returns:
    cloud_storage.BucketReference, The bucket to use.
  """
  if bucket:
    bucket_with_gs = bucket
  else:
    # Attempt to retrieve the default appspot bucket, if one can be created.
    log.debug('No bucket specified, retrieving default bucket.')
    bucket_with_gs = api_client.GetApplicationCodeBucket()
    if not bucket_with_gs:
      raise exceptions.DefaultBucketAccessError(project)

  return cloud_storage.BucketReference(bucket_with_gs)


def ValidateVersion(version):
  """Check that version is in the correct format. If not, raise an error.

  Args:
    version: The version id to validate (must not be None).

  Raises:
    InvalidVersionIdError: If the version id is invalid.
  """
  validator = validation.Regex(appinfo.MODULE_VERSION_ID_RE_STRING)
  try:
    validator.Validate(version, 'version')
  except validation.ValidationError:
    raise exceptions.InvalidVersionIdError(version)
