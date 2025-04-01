# -*- coding: utf-8 -*- #
#
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
"""Common utility functions for Developer Connect Insights Configs."""

import datetime
import re

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.api_lib.developer_connect import common
from googlecloudsdk.api_lib.resource_manager import folders
from googlecloudsdk.api_lib.services import serviceusage
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.projects import util as projects_util

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io


_ROLES = (
    'roles/developerconnect.insightsAgent',
)
_ARTIFACT_URI_PATTERN = r'^([^\.]+)-docker.pkg.dev/([^/]+)/([^/]+)/([^@:]+)$'
_PROJECT_PATTERN = r'projects/([^/]+)'
# Wait till service account is available for setIamPolicy
_MAX_WAIT_TIME_IN_MS = 20 * 1000
_APPHUB_MANAGEMENT_PROJECT_PREFIX = 'google-mfp'
VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1',
}


class InsightsConfigInitializationError(exceptions.InternalError):
  """Error initializing the Developer Connect Insights Config."""


def _GetP4SA(project, service_name):
  """Gets the P4SA for the given project and location.

  If the P4SA does not exist for this project, it will be created. Otherwise,
  the email address of the existing P4SA will be returned.

  Args:
    project: The project to get the P4SA for.
    service_name: The service name to get the P4SA for.

  Returns:
    The email address of the P4SA.
  """
  response = serviceusage.GenerateServiceIdentity(project, service_name)
  return response['email']


def _ShouldRetryHttpError(
    exc_type, unused_exc_value, unused_exc_traceback, unused_state
):
  """Whether to retry the request when receiving errors.

  Args:
    exc_type: type of the raised exception.
    unused_exc_value: the instance of the raise the exception.
    unused_exc_traceback: Traceback, traceback encapsulating the call stack at
      the point where the exception occurred.
    unused_state: RetryerState, state of the retryer.

  Returns:
    True if exception and is due to NOT_FOUND or INVALID_ARGUMENT.
  """
  return (exc_type == apitools_exceptions.HttpBadRequestError or
          exc_type == apitools_exceptions.HttpNotFoundError)


# The messages module can also be accessed from client.MESSAGES_MODULE
def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetMessagesModule('developerconnect', api_version)


def ExtractProject(uri):
  """Extracts the project from a resource URI."""
  match = re.search(_PROJECT_PATTERN, uri)
  if match:
    return match.group(1)
  return None


def ValidateArtifactUri(artifact_uri):
  """Validates an artifact URI and extracts the project if the format is valid.

  Validates an artifact URI and extracts the project if the format is valid.
  Args:
      artifact_uri: The artifact URI string to validate.
  Returns:
      The project name if the URI is valid, or None if invalid.
  """
  match = re.match(_ARTIFACT_URI_PATTERN, artifact_uri)
  if match:
    return match.group(2)
  else:
    return None


def IsManagementProject(app_hub_application):
  """Checks if the app hub application is a management project."""
  return app_hub_application.startswith(_APPHUB_MANAGEMENT_PROJECT_PREFIX)


class InsightsConfigClient(object):
  """Wrapper for Developer Connect Insights API client."""

  def __init__(self, release_track):
    api_version = VERSION_MAP.get(release_track)
    self.release_track = release_track
    self.client = apis.GetClientInstance('developerconnect', api_version)
    self._resource_parser = resources.Registry()
    self._resource_parser.RegisterApiByName('developerconnect', 'v1')
    self.messages = GetMessagesModule(release_track)
    self.api_version = api_version

  def Update(
      self,
      insight_config_ref,
      discovery,
      build_project,
      artifact_uri,
  ):
    """Updates the insight config."""
    if artifact_uri and build_project:
      old_insights_config = self.HandleArtifactConfigs(
          insight_config_ref, artifact_uri, build_project
      )
    else:
      old_insights_config = self.GetExistingInsightsConfig(insight_config_ref)

    if not IsManagementProject(
        ExtractProject(old_insights_config.appHubApplication)
    ):
      dependent_projects = self.GetDependentProjects(old_insights_config)
      self.InitServiceAccount(
          insight_config_ref.projectsId,
          dependent_projects,
          management_project=False,
      )
    else:
      # Management project, get permissions on the folder.
      folder_number = projects_api.Get(
          projects_util.ParseProject(
              ExtractProject(old_insights_config.appHubApplication)
          )
      ).parent.id
      dependent_folder = [folder_number]
      self.InitServiceAccount(
          insight_config_ref.projectsId,
          dependent_folder,
          management_project=True,
      )

    new_insights_config = self.InsightsConfigMessageType(old_insights_config)
    if discovery:
      new_insights_config.state = (
          self.messages.InsightsConfig.StateValueValuesEnum.PENDING
      )
    update_request = self.messages.DeveloperconnectProjectsLocationsInsightsConfigsPatchRequest(
        insightsConfig=new_insights_config,
        name=insight_config_ref.RelativeName(),
    )
    return self.client.projects_locations_insightsConfigs.Patch(
        request=update_request
    )

  def HandleArtifactConfigs(self, insights_ref, artifact_uri, build_project):
    """Handles the artifact config."""
    artifact_project = ValidateArtifactUri(artifact_uri)
    if not artifact_project:
      raise exceptions.Error(
          f'Invalid artifact URI: {artifact_uri}. Artifact URI must be in the'
          ' format '
          '{location}-docker.pkg.dev/{project}/{repository}/{package}.'
      )
    # Check if the build project exists.
    projects_api.Get(
        projects_util.ParseProject(build_project)
    )

    ic = self.GetExistingInsightsConfig(insights_ref)
    for index, artifact_config in enumerate(ic.artifactConfigs):
      if artifact_config.uri == artifact_uri:
        updated_artifact = self.messages.ArtifactConfig(
            uri=artifact_uri,
            googleArtifactAnalysis=self.messages.GoogleArtifactAnalysis(
                projectId=build_project
            ),
        )
        ic.artifactConfigs[index] = updated_artifact
        return ic
    # Add a new artifact config since it doesn't exist.
    ic.artifactConfigs.append(
        self.messages.ArtifactConfig(
            uri=artifact_uri,
            googleArtifactAnalysis=self.messages.GoogleArtifactAnalysis(
                projectId=build_project
            ),
        )
    )
    return ic

  def InsightsConfigMessageType(self, current_insights_config):
    """Creates a new insights config message type."""
    return self.messages.InsightsConfig(
        state=current_insights_config.state,
        artifactConfigs=current_insights_config.artifactConfigs,
    )

  def GetExistingInsightsConfig(self, insight_config_ref):
    """Gets the insight config."""
    return self.client.projects_locations_insightsConfigs.Get(
        request=self.messages.DeveloperconnectProjectsLocationsInsightsConfigsGetRequest(
            name=insight_config_ref.RelativeName(),
        )
    )

  def GetDependentProjects(self, insights_config):
    """Gets the P4SA projects for the insight config."""
    projects = set()
    projects.add(ExtractProject(insights_config.appHubApplication))
    for artifact_config in insights_config.artifactConfigs:
      if artifact_config.uri:
        artifact_project = ValidateArtifactUri(artifact_config.uri)
        if artifact_project:
          projects.add(artifact_project)
      if (
          artifact_config.googleArtifactAnalysis
          and artifact_config.googleArtifactAnalysis.projectId
      ):
        projects.add(artifact_config.googleArtifactAnalysis.projectId)
    for runtime_config in insights_config.runtimeConfigs:
      if runtime_config.uri:
        projects.add(ExtractProject(runtime_config.uri))
    return sorted(list(projects))

  def InitServiceAccount(
      self, p4sa_project, dependent_resources, management_project
  ):
    """Get the Developer Connect P4SA, and grant IAM roles to it.

    1) First, get the P4SA for the project.
    Args:
      p4sa_project: The project to get the P4SA for.
      dependent_resources: The resources to grant the P4SA permissions to.
      management_project: Whether the resource is a management project.

    2) Then grant necessary roles needed to the P4SA for updating an insight
      config.

    3) If the app hub application is a management project, grant the P4SA
      permissions on the folder.

    4) If the app hub application is a non management project, grant the P4SA
      permissions on the dependent projects.

    Raises:
      InsightsConfigInitializationError: P4SA failed to be created.
    """
    service_name = common.GetApiServiceName(self.api_version)
    p4sa_email = _GetP4SA(p4sa_project, service_name)
    if not p4sa_email:
      raise InsightsConfigInitializationError(
          'Failed to get P4SA for project {}.'.format(p4sa_project)
      )
    if management_project:
      if len(dependent_resources) == 1:
        self.BindRolesToServiceAccount(p4sa_email, dependent_resources[0], True)
      else:
        log.warning('Could not find folder number for the management project.'
                    'Skipping permissions checks/binding.')
    else:
      for project in dependent_resources:
        project_ref = projects_util.ParseProject(project)
        self.BindRolesToServiceAccount(p4sa_email, project_ref, False)

  def BindRolesToServiceAccount(
      self, sa_email, resource_ref, management_project
  ):
    """Binds roles to the provided service account.

    Args:
      sa_email: str, the service account to bind roles to.
      resource_ref: str, the resource to bind roles to.
      management_project: bool, whether the resource is a management project.
    """
    for role in _ROLES:
      self.PromptToBindRoleIfMissing(
          sa_email,
          resource_ref,
          role,
          management_project,
          reason='required to update the Developer Connect Insights Config',
      )

  def PromptToBindRoleIfMissing(
      self, sa_email, resource_ref, role, management_project, reason=''
  ):
    """Prompts to bind the role to the service account in project level if missing.

    If the console cannot prompt, a warning is logged instead.

    Args:
      sa_email: The service account email to bind the role to.
      resource_ref: The resource to bind the role to.
      role: The role to bind if missing.
      management_project: Whether the resource is a management project.
      reason: Extra information to print explaining why the binding is
        necessary.
    """
    member = 'serviceAccount:{}'.format(sa_email)
    try:
      if management_project:
        iam_policy = folders.GetIamPolicy(resource_ref)
      else:
        iam_policy = projects_api.GetIamPolicy(resource_ref)
      if self.HasRoleBinding(iam_policy, sa_email, role):
        return

      log.status.Print(
          'Service account [{}] is missing the role [{}].\n{}'.format(
              sa_email, role, reason
          )
      )

      bind = console_io.CanPrompt() and console_io.PromptContinue(
          prompt_string='\nBind the role [{}] to service account [{}]?'.format(
              role, sa_email
          )
      )
      if not bind:
        log.warning('Manual binding of above role will be necessary.\n')
        return

      if management_project:
        messages = folders.FoldersMessages()
        iam_util.AddBindingToIamPolicy(
            messages.Binding, iam_policy, member, role
        )
        folders.SetIamPolicy(resource_ref, iam_policy)
      else:
        projects_api.AddIamPolicyBinding(resource_ref, member, role)

      log.status.Print(
          'Successfully bound the role [{}] to service account [{}]'.format(
              role, sa_email
          )
      )
    except apitools_exceptions.HttpForbiddenError:
      log.warning(
          (
              'Your account does not have permission to check or bind IAM'
              ' policies to resource [%s]. If the deployment fails, ensure [%s]'
              ' has the role [%s] before retrying.'
          ),
          resource_ref,
          sa_email,
          role,
      )

  def HasRoleBinding(self, iam_policy, sa_email, role):
    """Returns whether the given SA has the given role bound in given policy.

    Args:
      iam_policy: The IAM policy to check.
      sa_email: The service account to check.
      role: The role to check for.
    """
    return any(
        'serviceAccount:{}'.format(sa_email) in b.members and b.role == role
        for b in iam_policy.bindings
    )

  def GetOperationRef(self, operation):
    """Converts an operation to a resource that can be used with `waiter.WaitFor`."""
    return self._resource_parser.ParseRelativeName(
        operation.name, 'securesourcemanager.projects.locations.operations')

  def WaitForOperation(
      self,
      operation_ref,
      message,
      has_result=True,
      max_wait=datetime.timedelta(seconds=600),
  ):
    """Waits for a Developer Connect operation to complete.

      Polls the Developer Connect Insights Operation service until the operation
      completes, fails, or max_wait_seconds elapses.

    Args:
      operation_ref: a resource reference created by GetOperationRef describing
        the operation.
      message: a message to display to the user while they wait.
      has_result: If True, the function will return the target of the operation
        (i.e. the InsightConfig) when it completes. If False, nothing will be
        returned (useful for Delete operations).
      max_wait: The time to wait for the operation to complete before returning.

    Returns:
      A resource reference to the target of the operation if has_result is True,
      otherwise None.
    """
    if has_result:
      poller = waiter.CloudOperationPoller(
          self.client.projects_locations_insightsConfigs,
          self.client.projects_locations_operations,
      )
    else:
      poller = waiter.CloudOperationPollerNoResources(
          self.client.projects_locations_operations
      )

    return waiter.WaitFor(
        poller, operation_ref, message, max_wait_ms=max_wait.seconds * 1000
    )
