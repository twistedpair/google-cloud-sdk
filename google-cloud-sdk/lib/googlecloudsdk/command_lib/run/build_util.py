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
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.api_lib.iam import util as iam_api_util
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.projects import util as project_util
from googlecloudsdk.command_lib.run import exceptions as serverless_exceptions
from googlecloudsdk.core import log

_RUN_BUILDER_ROLE = 'roles/run.builder'
_EDITOR_ROLE = 'roles/editor'

_GCE_SA = '{project_number}-compute@developer.gserviceaccount.com'


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
    build_service_account_description = _DescribeServiceAccount(
        service_account_email
    )
    if build_service_account_description.disabled:
      raise serverless_exceptions.ServiceAccountError(
          'Could not build the function due to disabled service account used by'
          ' Cloud Build. Please make sure that the service account:'
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

  project_number = project_util.GetProjectNumber(project_id)
  if service_account_email == _GCE_SA.format(project_number=project_number):
    try:
      iam_policy = projects_api.GetIamPolicy(
          project_util.ParseProject(project_id)
      )
    except apitools_exceptions.HttpForbiddenError:
      log.warning(
          (
              'Your account does not have permission to check or bind IAM'
              ' policies to project [%s]. If the deployment fails, ensure [%s]'
              ' has the role [%s] before retrying.'
          ),
          project_id,
          build_service_account,
          _RUN_BUILDER_ROLE,
      )
      return

    account_string = f'serviceAccount:{service_account_email}'
    contained_roles = [
        binding.role
        for binding in iam_policy.bindings
        if account_string in binding.members
    ]
    if (
        _RUN_BUILDER_ROLE not in contained_roles
        and _EDITOR_ROLE not in contained_roles
    ):
      missing_builder_role_message = (
          f'\nThe default build service account [{build_service_account}] is'
          ' missing'
          f' the [{_RUN_BUILDER_ROLE}] role. This will cause issues when'
          ' deploying a Cloud Run function. You could fix it by running the'
          ' command: \ngcloud projects add-iam-policy-binding'
          f' {project_id} \\\n'
          f' --member={account_string}'
          ' \\\n --role=roles/run.builder \n Or provid a new build'
          ' serrvice account with [--build-service-account] flag. \nIf'
          ' this is'
          ' your first time deploying, it may take a few minutes for the'
          ' permissions to propagate. You could try again later. \nFor more'
          ' information, please refer to:'
          ' https://cloud.google.com/functions/docs/troubleshooting#build-service-account.\n'
      )
      log.warning(missing_builder_role_message)
      raise serverless_exceptions.ServiceAccountError(
          'Missing required permissions for default build service account:'
          f' {build_service_account}.'
      )
