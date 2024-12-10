# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Service account utils."""
import re
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.command_lib.projects import util as project_util
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io

_BUILDER_ROLE = 'roles/cloudbuild.builds.builder'
_EDITOR_ROLE = 'roles/editor'

_GCE_SA = '{project_number}-compute@developer.gserviceaccount.com'


def GetDefaultBuildServiceAccount(project_id, region='global'):
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


def ValidateDefaultBuildServiceAccountAndPromptWarning(
    project_id, region, build_service_account=None
):
  """Util to validate the default build service account permission.

  Prompt a warning to users if cloudbuild.builds.builder is missing.

  Args:
    project_id: id of project
    region: region to deploy the function
    build_service_account: user provided build service account. It will be None,
      if user doesn't provide it.
  """
  if build_service_account is None:
    build_service_account = _ExtractServiceAccountEmail(
        GetDefaultBuildServiceAccount(project_id, region)
    )
  project_number = project_util.GetProjectNumber(project_id)
  if build_service_account == _GCE_SA.format(project_number=project_number):
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
          _BUILDER_ROLE,
      )
      return

    account_string = f'serviceAccount:{build_service_account}'
    contained_roles = [
        binding.role
        for binding in iam_policy.bindings
        if account_string in binding.members
    ]
    if (
        _BUILDER_ROLE not in contained_roles
        and _EDITOR_ROLE not in contained_roles
        and console_io.CanPrompt()
    ):
      # Previously default compute engine service account was granted editor
      # role when it was provisioned, which naturally granted all of the
      # permission required to finish a build. Nowadays, editor role is not
      # granted by default anymore. We want to suggest users having
      # roles/cloudbuild.builds.builder instead to make sure build can be
      # completed successfully.
      console_io.PromptContinue(
          default=False,
          cancel_on_no=True,
          prompt_string=(
              f'\nThe default build service account [{build_service_account}]'
              f' is missing the [{_BUILDER_ROLE}] role. This may cause issues'
              ' when deploying a function. You could fix it by running the'
              ' command: \ngcloud projects add-iam-policy-binding'
              f' {project_id} \\\n'
              f' --member=serviceAccount:{project_number}-compute@developer.gserviceaccount.com'
              ' \\\n --role=roles/cloudbuild.builds.builder \nFor more'
              ' information, please refer to:'
              ' https://cloud.google.com/functions/docs/troubleshooting#build-service-account.\n'
              ' Would you like to continue?'
          ),
      )
