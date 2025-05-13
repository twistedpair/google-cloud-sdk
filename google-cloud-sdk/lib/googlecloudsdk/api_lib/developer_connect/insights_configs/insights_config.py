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

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.api_lib.developer_connect import common
from googlecloudsdk.api_lib.developer_connect.insights_configs import discover_apphub
from googlecloudsdk.api_lib.developer_connect.insights_configs import discover_artifact_configs as discover_artifacts
from googlecloudsdk.api_lib.resource_manager import folders
from googlecloudsdk.api_lib.services import serviceusage
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.developer_connect import name
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.projects import util as projects_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io


_ROLES = (
    'roles/developerconnect.insightsAgent',
)
# Wait till service account is available for setIamPolicy
_MAX_WAIT_TIME_IN_MS = 20 * 1000
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
    self.p4sa_email = None

  def Create(self, insight_config_ref, app_hub, user_artifact_configs):
    """Creates the insight config."""
    app_hub_application = name.parse_app_hub_application_uri(app_hub)
    user_artifact_configs_dict = name.parse_artifact_configs(
        user_artifact_configs
    )
    # Handle the management project and get the dependent projects and gke
    # workloads.
    dependent_projects, gke_workloads = (
        self.FindGkeWorkloadsAndGrantSAPermissions(
            insight_config_ref, app_hub_application
        )
    )
    cais_artifact_configs_dict = self.GetArtifactConfigsFromCAIS(gke_workloads)
    merged_artifact_configs_dict = self.MergeArtifactConfigs(
        cais_artifact_configs_dict, user_artifact_configs_dict
    )

    # Get the artifact configs and add new projects to the dependent projects
    # set.
    artifact_projects, artifact_configs = self.BuildArtifactConfigs(
        merged_artifact_configs_dict, cais_artifact_configs_dict
    )
    # Add the artifact projects to the dependent projects set.
    dependent_projects.update(artifact_projects)
    # Get the P4SA and grant IAM roles to it.
    if dependent_projects:
      self.InitServiceAccount(
          insight_config_ref.projectsId,
          dependent_projects,
          management_project=False,
      )

    create_request = self.messages.DeveloperconnectProjectsLocationsInsightsConfigsCreateRequest(
        parent=insight_config_ref.Parent().RelativeName(),
        insightsConfigId=insight_config_ref.insightsConfigsId,
        insightsConfig=self.messages.InsightsConfig(
            name=insight_config_ref.RelativeName(),
            appHubApplication=app_hub_application.resource_name(),
            artifactConfigs=artifact_configs,
        ),
    )
    try:
      return self.client.projects_locations_insightsConfigs.Create(
          request=create_request
      )
    except apitools_exceptions.HttpConflictError:
      raise exceptions.Error(
          f'Insights Config [{insight_config_ref.insightsConfigsId}] already'
          f' exists in project [{insight_config_ref.projectsId}] location'
          f' [{insight_config_ref.locationsId}].'
      )

  def MergeArtifactConfigs(
      self, artifact_configs_dict, user_provided_artifact_configs
  ):
    """Merges artifact configs from CAIS and user provided configs user provided configs will overwrite configs extracted from CAIS if URIs match.
    """
    merged_artifact_configs_dict = {}
    # First, populate with CAIS-discovered configs
    if artifact_configs_dict:
      for uri, config_msg in artifact_configs_dict.items():
        merged_artifact_configs_dict[uri] = config_msg

    if not user_provided_artifact_configs:
      return merged_artifact_configs_dict

    for uri, build_project in user_provided_artifact_configs.items():
      # Create a new ArtifactConfig message to populate from user_config_data
      merged_artifact_configs_dict[uri] = self.messages.ArtifactConfig(
          uri=uri,
          googleArtifactAnalysis=self.messages.GoogleArtifactAnalysis(
              projectId=build_project
          ),
      )

    return merged_artifact_configs_dict

  def FindGkeWorkloadsAndGrantSAPermissions(
      self, insight_config_ref, app_hub_application
  ):
    """Finds the GKE workloads and grants SA permissions at the folder level for management project or returns the dependent projects for non-management projects.

    Args:
      insight_config_ref: The insight config reference.
      app_hub_application: The app hub application.

    Returns:
      A tuple of dependent projects(based on if it is a management project or
      not) and gke workloads.
    """
    dependent_projects, gke_workloads = self.GetRuntimes(
        app_hub_application.resource_name()
    )
    # If the app hub application is not a management project, return the
    # dependent projects from the runtime configs, we'll grant permissions to
    # this set of projects later.
    if not name.is_management_project(app_hub_application.project_id()):
      return dependent_projects, gke_workloads

    # Management project, assign permissions to the folder and we don't need
    # dependent projects here.
    self.AssignManagementPermissions(insight_config_ref, app_hub_application)
    return set(), gke_workloads

  def GetArtifactConfigsFromCAIS(self, gke_workloads):
    """Queries CAIS for artifacts associated with the gke workloads in the resources scope.

    Args:
      gke_workloads: A list of GKE workloads.

    Returns:
      A dict of artifact configs IC type.
    """
    # Use a dict to deduplicate artifact configs and allow users to overwrite
    # build projects.
    artifact_configs_dict = {}
    for gke_workload in gke_workloads:
      assets = discover_artifacts.QueryCaisForAssets(gke_workload)
      artifact_uris = discover_artifacts.GetArtifactURIsFromAssets(assets)
      for artifact in artifact_uris:
        validated_artifact_uri = name.validate_artifact_uri(artifact)
        if not validated_artifact_uri:
          continue
        base_uri = validated_artifact_uri.base_uri()
        artifact_configs_dict[base_uri] = self.messages.ArtifactConfig(
            uri=base_uri,
            googleArtifactAnalysis=self.messages.GoogleArtifactAnalysis(
                projectId=validated_artifact_uri.project_id()
            ),
        )
    return artifact_configs_dict

  def BuildArtifactConfigs(
      self, merged_artifact_configs_dict, cais_artifact_configs_dict
  ):
    """Builds the artifact configs and returns the dependent projects and artifact configs.

    Args:
      merged_artifact_configs_dict: A combined dict of artifact configs IC type
        from CAIS and user provided configs.
      cais_artifact_configs_dict: A dict of artifact configs IC type from CAIS.

    Returns:
      A tuple of dependent projects and artifact configs.
    """
    dependent_projects = set()
    # Print existing artifact configs if they exist.
    if not merged_artifact_configs_dict:
      log.status.Print('No existing artifact configurations found.')
      return dependent_projects, []
    # Prompt for build projects ONLY if we have CAIS-discovered
    # artifact configs.
    if cais_artifact_configs_dict:
      for artifact_config in merged_artifact_configs_dict.values():
        build_project = artifact_config.googleArtifactAnalysis.projectId
        log.status.Print(
            '\nBuild project'
            f' [{build_project}] will be'
            ' used to extract provenance information for artifact'
            f' [{artifact_config.uri}]'
        )
        change_build_project = (
            console_io.CanPrompt()
            and console_io.PromptContinue(
                prompt_string='Would you like to change the build project?',
                default=False,
            )
        )
        if change_build_project:
          build_project = self.PromptForBuildProject(artifact_config.uri)

        merged_artifact_configs_dict[artifact_config.uri] = (
            self.messages.ArtifactConfig(
                uri=artifact_config.uri,
                googleArtifactAnalysis=self.messages.GoogleArtifactAnalysis(
                    projectId=build_project
                ),
            )
        )

    # Return the dependent projects and the artifact configs.
    artifact_configs = list(merged_artifact_configs_dict.values())
    # Add the dependent build projects to the dependent projects list. We do
    # this here because users could overwrite build project selections while
    # prompting for artifact configs.
    dependent_projects.update(
        artifact.googleArtifactAnalysis.projectId
        for artifact in artifact_configs
    )
    return dependent_projects, artifact_configs

  def PromptForBuildProject(self, artifact_uri):
    """Prompts the user for the build project."""
    found = False
    build_project = None
    while not found:
      build_project = console_io.PromptResponse(
          'Please enter the build project for your artifact'
          f' [{artifact_uri}]: '
      )

      try:
        name.validate_build_project(build_project)
        found = True
      except apitools_exceptions.HttpForbiddenError:
        log.status.Print(
            'Permission denied when checking build project [{}]. Please'
            ' ensure your account has necessary permissions '
            'or that the project exists.'
            .format(build_project)
        )
      except apitools_exceptions.HttpBadRequestError:
        log.status.Print(
            'Invalid build project ID [{}]. Please ensure it is a valid'
            ' project ID (e.g., "my-project-123")'.format(build_project)
        )
      except exceptions.Error as e:
        log.warning(f'Error validating build project [{build_project}]: {e}')
    return build_project

  def GetRuntimes(self, app_hub):
    """Gets the runtime configs.

    Args:
      app_hub: The app hub application.

    Returns:
      A tuple of runtime configs projects and gke workloads associated with the
      app hub application.
    """
    runtime_configs_projects = set()
    gke_workloads = []
    client = discover_apphub.DiscoveredWorkloadsClient()
    workloads = client.List(
        page_size=100,
        parent=app_hub,
    )

    for workload in workloads:
      gke_workload = name.parse_gke_deployment_uri(
          workload.workloadReference.uri
      )
      if gke_workload:
        # Add the *project id* to the runtime configs projects set, ensuring it
        # is project id and not project number so that we don't add the same
        # project multiple times.
        runtime_configs_projects.add(
            name.Project(
                gke_workload.gke_namespace.gke_cluster.project
            ).project_id
        )
        gke_workloads.append(gke_workload)
    return runtime_configs_projects, gke_workloads

  def AssignManagementPermissions(self, insight_config_ref, app_hub):
    """Assigns permissions to at the folder level for management project."""
    # Management project, get permissions on the folder.
    folder_number = projects_api.Get(
        projects_util.ParseProject(
            app_hub.project_id()
        )
    ).parent.id
    dependent_folder = [folder_number]
    self.InitServiceAccount(
        insight_config_ref.projectsId,
        dependent_folder,
        management_project=True,
    )
    return

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

    if not name.is_management_project(
        name.extract_project(old_insights_config.appHubApplication)
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
              name.extract_project(old_insights_config.appHubApplication)
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
    artifact_project = name.validate_artifact_uri(artifact_uri)
    if not artifact_project:
      raise exceptions.Error(
          f'Invalid artifact URI: {artifact_uri}. Artifact URI must be in the'
          ' format '
          '{location}-docker.pkg.dev/{project}/{repository}/{package}.'
      )
    # Check if the build project exists.
    try:
      name.validate_build_project(build_project)
    # Catch specific API errors first
    except apitools_exceptions.HttpForbiddenError:
      # Specific handling for permission errors
      raise exceptions.Error(
          'Permission denied when checking build project [{}]. Please ensure'
          ' the account [{}] has necessary permissions (e.g.,'
          ' resourcemanager.projects.get) or that the project exists.'
          .format(build_project, iam_util.GetAuthenticatedAccount())
      )
    except apitools_exceptions.HttpBadRequestError as e:
      raise exceptions.Error(
          'Invalid build project ID [{}]: {}. Please ensure it is a valid'
          ' project ID (e.g., "my-project-123") and not an artifact URI.'
          .format(build_project, e)
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
    try:
      return self.client.projects_locations_insightsConfigs.Get(
          request=self.messages.DeveloperconnectProjectsLocationsInsightsConfigsGetRequest(
              name=insight_config_ref.RelativeName(),
          )
      )
    except apitools_exceptions.HttpNotFoundError:
      raise exceptions.Error(
          f'Insights Config [{insight_config_ref.insightsConfigsId}] not found'
          f' in project [{insight_config_ref.projectsId}] location'
          f' [{insight_config_ref.locationsId}].'
      )

  def GetDependentProjects(self, insights_config):
    """Gets the P4SA projects for the insight config."""
    projects = set()
    projects.add(name.extract_project(insights_config.appHubApplication))
    for artifact_config in insights_config.artifactConfigs:
      if artifact_config.uri:
        artifact_uri = name.validate_artifact_uri(artifact_config.uri)
        if artifact_uri:
          projects.add(artifact_uri.project_id())
      if (
          artifact_config.googleArtifactAnalysis
          and artifact_config.googleArtifactAnalysis.projectId
      ):
        projects.add(artifact_config.googleArtifactAnalysis.projectId)
    for runtime_config in insights_config.runtimeConfigs:
      if runtime_config.uri:
        projects.add(name.extract_project(runtime_config.uri))
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
    if self.p4sa_email is None:
      self.p4sa_email = _GetP4SA(p4sa_project, service_name)
    if not self.p4sa_email:
      raise InsightsConfigInitializationError(
          'Failed to get P4SA for project {}.'.format(p4sa_project)
      )
    if management_project:
      if len(dependent_resources) == 1:
        self.BindRolesToServiceAccount(
            self.p4sa_email, dependent_resources[0], True
        )
      else:
        log.warning(
            'Could not find folder number for the management project.'
            'Skipping permissions checks/binding.'
        )
    else:
      for project in dependent_resources:
        project_ref = projects_util.ParseProject(project)
        self.BindRolesToServiceAccount(self.p4sa_email, project_ref, False)

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
          '\nService account [{}] is missing the role [{}].\n{}'.format(
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
