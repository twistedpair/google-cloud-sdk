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
"""API client library for Applications."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from __future__ import annotations

from collections.abc import Sequence
from functools import partial
import time
from typing import Any
import uuid

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.api_lib.design_center import utils
from googlecloudsdk.api_lib.iam import util as iam_api
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.projects import util as crm_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


def ConstructServiceAccountName(application_id, uuid_value=None):
  """Constructs a unique service account name with a UUID suffix.

  The service account ID must be between 6 and 30 characters.

  Args:
    application_id: str, The ID of the application.
    uuid_value: uuid.UUID, Optional. A UUID value to use instead of generating
      a new one.

  Returns:
    str, The constructed service account name.
  """
  # Service account IDs must be between 6 and 30 characters.
  # We'll use a prefix from the application_id and append a short UUID.
  uuid_str = str(uuid_value) if uuid_value is not None else str(uuid.uuid4())
  uuid_suffix, *_ = uuid_str.split('-')
  max_app_id_len = 30 - len(uuid_suffix) - 1  # Account for '-' separator
  app_id_part = application_id[:max(1, max_app_id_len)].rstrip('-')

  return f'{app_id_part}-{uuid_suffix}'


class ApplicationsClient(object):
  """Client for Applications in the Design Center API."""

  def __init__(self, release_track=base.ReleaseTrack.ALPHA):
    self.client = utils.GetClientInstance(release_track)
    self.messages = utils.GetMessagesModule(release_track)
    self._service = self.client.projects_locations_spaces_applications

  def _RetryIamOperation(
      self,
      operation_fn,
      error_message_fmt: str,
      error_message_args: Sequence[Any],
      max_retries: int = 5,
      delay_seconds: int = 5,
      sleeper=time.sleep,
  ):
    """Retries an IAM operation on HttpError."""
    last_exception = None
    for i in range(max_retries):
      try:
        operation_fn()
        return True
      except apitools_exceptions.HttpError as e:
        formatted_base_message = error_message_fmt % error_message_args
        log.warning(
            '%s (Attempt %d/%d): %r',
            formatted_base_message,
            i + 1,
            max_retries,
            e,
            exc_info=True,
        )
        if i < max_retries - 1:
          sleeper(delay_seconds)
        last_exception = e
    formatted_base_message = error_message_fmt % error_message_args
    log.error(
        '%s (Failed after %d attempts).',
        formatted_base_message,
        max_retries,
    )
    raise exceptions.Error(
        '%s (Failed after %d attempts).' % (formatted_base_message, max_retries)
    ) from last_exception

  def _AddRolesToServiceAccountOnProject(
      self,
      project_ref,
      *,
      service_account_email,
      roles: Sequence[str],
      project_id,
  ):
    """Adds a list of roles to a service account on a specific project.

    Args:
      project_ref: The project resource reference.
      service_account_email: str, The email address of the service account.
      roles: Sequence[str], A sequence of role names to grant.
      project_id: str, The ID of the project.

    Raises:
      exceptions.Error: If adding any role fails after retries.
    """
    for role_to_grant in roles:
      self._RetryIamOperation(
          lambda pr=project_ref, sae=service_account_email, role=role_to_grant: (
              projects_api.AddIamPolicyBinding(
                  pr,
                  f'serviceAccount:{sae}',
                  role,
              )
          ),
          'Failed to add role %s to service account on project %s',
          (role_to_grant, project_id),
      )

  def _AddServiceAccountRoles(
      self,
      project_parameters: Sequence[Any],
      service_account,
  ):
    """Adds required roles to the service account for each project parameter.

    Args:
      project_parameters: A sequence of project parameter objects.
      service_account: str, The email address of the service account.

    Raises:
      exceptions.Error: If adding any role fails.
    """
    for pp in project_parameters:
      current_project_id = pp.projectId
      current_project_ref = crm_util.ParseProject(current_project_id)
      self._AddRolesToServiceAccountOnProject(
          current_project_ref,
          service_account_email=service_account,
          roles=pp.roles,
          project_id=current_project_id,
      )
      log.status.Print(
          'Successfully added required project roles to service account '
          'for project %s.'% current_project_id
      )

  def _CreateAndConfigureServiceAccount(
      self,
      *,
      application_id,
      name,
      project,
      service_account,
      user_account,
      iam_client,
      iam_messages,
  ):
    """Creates and configures a service account for application deployment.

    Args:
      application_id: str, The ID of the application.
      name: str, The full resource name of the Application.
      project: str, The project ID.
      service_account: str, The email address of the service account, or None.
      user_account: str, The email address of the user.
      iam_client: The API client for IAM service accounts.
      iam_messages: The API messages module for IAM service accounts.

    Returns:
      str, The fully qualified service account resource name on success, or None
      on failure.
    Raises:
      exceptions.Error: If service account creation fails for reasons other than
      409.
    """
    # Check if the user has permission to create service accounts.
    project_ref = crm_util.ParseProject(project)
    response = projects_api.TestIamPermissions(
        project_ref, ['iam.serviceAccounts.create']
    )
    # Access the 'permissions' attribute of the response object
    allowed_permissions = (response.permissions or [])
    if 'iam.serviceAccounts.create' not in allowed_permissions:
      raise exceptions.Error(
          'User does not have permission to create service accounts in project'
          f' {project}. Required permission: iam.serviceAccounts.create'
      )

    sa_email = service_account
    if service_account is not None:
      sa_name = service_account.split('@')[0]
    else:
      sa_name = ConstructServiceAccountName(application_id)
      sa_email = f'{sa_name}@{project}.iam.gserviceaccount.com'

    # Describe the application to identify the required IAM roles.
    app_details = self._service.Get(
        self.messages.DesigncenterProjectsLocationsSpacesApplicationsGetRequest(
            name=name
        )
    )
    project_parameters = app_details.projectParameters
    log.status.Print(
        'Successfully described application and retrieved required roles.'
    )

    # Create the service account.
    log.status.Print(
        'Creating service account for application: %s' % application_id
    )
    iam_client.projects_serviceAccounts.Create(
        iam_messages.IamProjectsServiceAccountsCreateRequest(
            name=iam_util.ProjectToProjectResourceName(project),
            createServiceAccountRequest=iam_messages.CreateServiceAccountRequest(
                accountId=sa_name,
                serviceAccount=iam_messages.ServiceAccount(
                    displayName=f'Service account for {sa_email}'
                ),
            ),
        )
    )
    log.status.Print('Successfully created service account: %s' % sa_email)

    self._AddServiceAccountRoles(project_parameters, sa_email)

    def _GrantActAsToPrincipal(sa_email, member):
      """Helper function to grant actAs permission to a given member."""

      sa_resource_name = iam_util.EmailToAccountResourceName(sa_email)

      sa_policy = iam_client.projects_serviceAccounts.GetIamPolicy(
          iam_messages.IamProjectsServiceAccountsGetIamPolicyRequest(
              resource=sa_resource_name
          )
      )

      iam_util.AddBindingToIamPolicy(
          iam_messages.Binding,
          sa_policy,
          member,
          'roles/iam.serviceAccountUser',
      )

      iam_client.projects_serviceAccounts.SetIamPolicy(
          iam_messages.IamProjectsServiceAccountsSetIamPolicyRequest(
              resource=sa_resource_name,
              setIamPolicyRequest=iam_messages.SetIamPolicyRequest(
                  policy=sa_policy
              ),
          )
      )

    def _GrantActAsToUser(sa_email, user_account):
      """Grant `actAs` permission to the user."""
      member = f'user:{user_account}'
      _GrantActAsToPrincipal(sa_email, member)

    def _GrantActAsToAdcAgent(sa_email, adc_service_agent):
      """Grant `actAs` permission to the ADC service agent."""
      member = f'serviceAccount:{adc_service_agent}'
      _GrantActAsToPrincipal(sa_email, member)

    grant_user_func = partial(_GrantActAsToUser, sa_email, user_account)
    self._RetryIamOperation(
        grant_user_func,
        'Failed to grant actAs permission to user %s',
        (sa_email, user_account),
    )
    log.status.Print(
        'Successfully granted actAs permission to user %s.'% user_account
    )

    project_number = projects_api.Get(
        crm_util.ParseProject(project)
    ).projectNumber
    p4sa_host = utils.GetP4saHost()
    adc_service_agent = f'service-{project_number}@{p4sa_host}'

    grant_agent_func = partial(
        _GrantActAsToAdcAgent, sa_email, adc_service_agent
    )
    self._RetryIamOperation(
        grant_agent_func,
        'Failed to grant actAs permission to ADC service agent',
        (sa_email, adc_service_agent),
    )
    log.status.Print(
        'Successfully granted actAs permission to ADC service agent.'
    )
    return f'projects/{project}/serviceAccounts/{sa_email}'

  def ImportIac(self, name, gcs_uri=None, iac_module=None,
                allow_partial_import=False, validate_iac=False):
    """Calls the ImportApplicationIaC RPC.

    Args:
      name: str, The full resource name of the Application.
      gcs_uri: str, The GCS URI of the IaC source.
      iac_module: messages.IaCModule, The IaCModule object.
      allow_partial_import: bool, Whether to allow partial imports.
      validate_iac: bool, Whether to only validate the IaC.

    Returns:
      The response from the API call.
    """
    if not name:
      raise ValueError('Application name cannot be empty or None.')

    import_iac_request = self.messages.ImportApplicationIaCRequest(
        allowPartialImport=allow_partial_import,
        validateIac=validate_iac)

    if gcs_uri:
      import_iac_request.gcsUri = gcs_uri
    elif iac_module:
      import_iac_request.iacModule = iac_module

    request = (
        self.messages.DesigncenterProjectsLocationsSpacesApplicationsImportIaCRequest(
            name=name,
            importApplicationIaCRequest=import_iac_request))

    return self._service.ImportIaC(request)

  def DeployApplication(
      self,
      name: str,
      *,
      replace: bool = False,
      worker_pool: str | None = None,
      service_account: str | None = None,
      create_sa: bool = False,
  ) -> Any | None:
    """Calls the DeployApplication RPC.

    Args:
      name: str, The full resource name of the Application.
      replace: bool, Flag to update the existing deployment.
      worker_pool: str, The user-specified Worker Pool resource.
      service_account: str | None, The email address of the service account.
      create_sa: bool, Whether to create a new service account.

    Returns:
      The response from the API call.
    """
    if not name:
      raise ValueError('Application name cannot be empty or None.')
    application_id = name.split('/')[-1]
    project = properties.VALUES.core.project.Get()
    deploy_service_account = service_account
    if create_sa:
      user_account = properties.VALUES.core.account.Get()
      iam_client, iam_messages = iam_api.GetClientAndMessages()
      configured_sa = self._CreateAndConfigureServiceAccount(
          application_id=application_id,
          name=name,
          project=project,
          service_account=service_account,
          user_account=user_account,
          iam_client=iam_client,
          iam_messages=iam_messages
      )
      deploy_service_account = configured_sa

    return self._service.Deploy(
        self.messages.DesigncenterProjectsLocationsSpacesApplicationsDeployRequest(
            name=name,
            deployApplicationRequest=self.messages.DeployApplicationRequest(
                replace=replace,
                workerPool=worker_pool,
                serviceAccount=deploy_service_account,
            ),
        )
    )

  def GetApplication(self, name: str) -> Any | None:
    """Calls the GetApplication RPC."""
    if not name:
      raise ValueError('Application name cannot be empty or None.')
    return self._service.Get(
        self.messages.DesigncenterProjectsLocationsSpacesApplicationsGetRequest(
            name=name
        )
    )

  def PreviewApplication(
      self,
      name: str,
      worker_pool: str | None = None,
      service_account: str | None = None,
      create_sa: bool = False,
  ):
    """Calls the PreviewApplication RPC.

    Args:
      name: str, The full resource name of the Application.
      worker_pool: str, The user-specified Worker Pool resource.
      service_account: str, The email address of the service account.
      create_sa: bool, Whether to create a new service account.

    Returns:
      The response from the API call.
    """
    if not name:
      raise ValueError('Application name cannot be empty or None.')
    application_id = name.split('/')[-1]
    project = properties.VALUES.core.project.Get()
    preview_service_account = service_account
    if create_sa:
      user_account = properties.VALUES.core.account.Get()
      iam_client, iam_messages = iam_api.GetClientAndMessages()
      configured_sa = self._CreateAndConfigureServiceAccount(
          application_id=application_id,
          name=name,
          project=project,
          service_account=service_account,
          user_account=user_account,
          iam_client=iam_client,
          iam_messages=iam_messages
      )
      preview_service_account = configured_sa

    return self._service.Preview(
        self.messages.DesigncenterProjectsLocationsSpacesApplicationsPreviewRequest(
            name=name,
            previewApplicationRequest=self.messages.PreviewApplicationRequest(
                workerPool=worker_pool,
                serviceAccount=preview_service_account,
            ),
        )
    )
