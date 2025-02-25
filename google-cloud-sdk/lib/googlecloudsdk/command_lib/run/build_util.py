# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Build utils."""
import re
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.api_lib.iam import util as iam_api_util
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.run import exceptions as serverless_exceptions
from googlecloudsdk.core import log


_LEGACY_BUILD_SA_FORMAT = r'^\d+@cloudbuild\.gserviceaccount\.com$'


def _GetDefaultBuildServiceAccount(project_id, region='global'):
  """Gets the default build service account for a project."""
  client = cloudbuild_util.GetClientInstance()
  name = f'projects/{project_id}/locations/{region}/defaultServiceAccount'
  return client.projects_locations.GetDefaultServiceAccount(
      client.MESSAGES_MODULE.CloudbuildProjectsLocationsGetDefaultServiceAccountRequest(
          name=name
      )
  ).serviceAccountEmail


def _ExtractServiceAccountEmail(service_account):
  """Extracts the service account email from the service account resource."""
  match = re.search(r'/serviceAccounts/([^/]+)$', service_account)
  if match:
    return match.group(1)
  else:
    return None


def _DescribeServiceAccount(service_account_email):
  client, messages = iam_api_util.GetClientAndMessages()
  return client.projects_serviceAccounts.Get(
      messages.IamProjectsServiceAccountsGetRequest(
          name=iam_util.EmailToAccountResourceName(service_account_email)
      )
  )


def ValidateBuildServiceAccountAndPromptWarning(
    project_id, region, build_service_account=None
):
  """Util to validate the default build service account permission.

  Prompt a warning to users if cloudbuild.builds.builder is missing.

  Args:
    project_id: id of project.
    region: region to deploy the service.
    build_service_account: user provided build service account. It will be None,
      if user doesn't provide it.

  Raises:
    ServiceAccountError: if the build service account is disabled/not
    found/missing required permissions.
  """

  if build_service_account is None:
    build_service_account = _GetDefaultBuildServiceAccount(project_id, region)
  service_account_email = _ExtractServiceAccountEmail(build_service_account)

  try:
    if not re.match(_LEGACY_BUILD_SA_FORMAT, service_account_email):
      build_service_account_description = _DescribeServiceAccount(
          service_account_email
      )
      if build_service_account_description.disabled:
        raise serverless_exceptions.ServiceAccountError(
            'Could not build the function due to disabled service account used'
            ' by Cloud Build. Please make sure that the service account:'
            f' [{build_service_account}] is active.'
        )
  except apitools_exceptions.HttpForbiddenError:
    # Just show a warning but not breaking the deployment.
    # We are doing best effort here.
    log.warning(
        'Your account does not have permission to check details of build'
        f' service account {build_service_account}. If the deployment fails,'
        f' please ensure {build_service_account} is active.'
    )
  except apitools_exceptions.HttpNotFoundError:
    log.warning(
        f'The build service account {build_service_account} does not exist. If'
        ' you just created this account, or if this is your first time'
        ' deploying with the default build service account, it may take a few'
        ' minutes for the service account to become fully available. Please'
        ' try again later.'
    )
    raise serverless_exceptions.ServiceAccountError(
        f'Build service account {build_service_account} does not exist.'
    )
