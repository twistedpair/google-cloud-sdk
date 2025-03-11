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
from googlecloudsdk.command_lib.functions import run_util
from googlecloudsdk.command_lib.projects import util as project_util
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io

_BUILDER_ROLE = 'roles/cloudbuild.builds.builder'
_EDITOR_ROLE = 'roles/editor'
_RUN_INVOKER_ROLE = 'roles/run.invoker'
_PREDEFINE_ROLES_WITH_ROUTE_INVOKER_PERMISSION = [
    'roles/run.admin',
    'roles/run.developer',
    _RUN_INVOKER_ROLE,
    'roles/run.servicesInvoker',
    'roles/run.sourceDeveloper',
]

_ROUTE_INVOKER_PERMISSION = 'run.routes.invoke'

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


def ValidateAndBindTriggerServiceAccount(
    function,
    project_id,
    trigger_service_account,
    is_gen2=False,
):
  """Validates trigger service account has route.invoker permission on project.

  If missing, prompt user to add the run invoker role on the function's Cloud
  Run service.

  Args:
    function: the function to add the binding to
    project_id: the project id to validate
    trigger_service_account: the trigger service account to validate
    is_gen2: whether the function is a gen2 function
  """
  project_number = project_util.GetProjectNumber(project_id)
  trigger_service_account = (
      trigger_service_account
      if trigger_service_account
      else _GCE_SA.format(project_number=project_number)
  )
  try:
    iam_policy = projects_api.GetIamPolicy(
        project_util.ParseProject(project_id)
    )
    if _ShouldBindInvokerRole(iam_policy, trigger_service_account):
      run_util.AddOrRemoveInvokerBinding(
          function,
          f'serviceAccount:{trigger_service_account}',
          add_binding=True,
          is_gen2=is_gen2,
      )
      log.status.Print('Role successfully bound.\n')
  except apitools_exceptions.HttpForbiddenError:
    log.warning(
        'Your account does not have permission to check or bind IAM'
        ' policies to project [%s]. If your function encounters'
        ' authentication errors, ensure [%s] has the role [%s].',
        project_id,
        trigger_service_account,
        _RUN_INVOKER_ROLE,
    )


def _ShouldBindInvokerRole(iam_policy, service_account):
  """Prompts user to bind the invoker role if missing."""
  custom_role_detected = False
  account_string = f'serviceAccount:{service_account}'
  for binding in iam_policy.bindings:
    if account_string not in binding.members:
      continue
    if binding.role in _PREDEFINE_ROLES_WITH_ROUTE_INVOKER_PERMISSION:
      return False
    elif not binding.role.startswith('roles/'):
      # A custom role starts with "projects/" or "organizations/" while a
      # predefined role starts with "roles/".
      custom_role_detected = True

  prompt_string = (
      f'Your trigger service account [{service_account}] is missing'
      f' the [{_RUN_INVOKER_ROLE}] role. This will cause authentication'
      ' errors when running the function.\n'
  )
  if custom_role_detected:
    prompt_string = (
        f'Your trigger service account [{service_account}] likely'
        f' lacks the [{_ROUTE_INVOKER_PERMISSION}] permission, which will'
        ' cause authentication errors. Since this service account uses a'
        ' custom role, please verify that the custom role includes this'
        " permission. If not, you'll need to either add this permission to"
        f' the custom role, or grant the [{_RUN_INVOKER_ROLE}] role to the'
        ' service account directly.\n'
    )

  should_bind = console_io.CanPrompt() and console_io.PromptContinue(
      default=False,
      cancel_on_no=True,
      prompt_string=prompt_string
      + ' Do you want to add the invoker binding to the IAM policy of'
      ' your Cloud Run function?',
  )

  if not should_bind:
    log.warning(prompt_string)

  return should_bind
