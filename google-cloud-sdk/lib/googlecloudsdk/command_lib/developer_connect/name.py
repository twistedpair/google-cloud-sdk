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
import re
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.command_lib.projects import util as projects_util
from googlecloudsdk.core import exceptions

_APPHUB_MANAGEMENT_PROJECT_PREFIX = "google-mfp"
_ARTIFACT_URI_PATTERN = (
    r"^([^\.]+)-docker.pkg.dev/([^/]+)/([^/]+)/([^@:]+)(@sha256:[a-f0-9]+)?$"
)
_PROJECT_PATTERN = r"projects/([^/]+)"
apphub_service_prefix = "//apphub.googleapis.com"
gke_service_prefix = "//container.googleapis.com"
name_segment_re = r"([a-zA-Z0-9-._~%!$&'()*+,;=@]{1,64})"

app_hub_application_path_regex = re.compile(
    rf"^(?:{apphub_service_prefix}/)?projects/((?:[^:]+:.)?[a-z0-9\\-]+)/locations/([\w-]{{2,40}})/applications/{name_segment_re}$"
)
gke_deployment_path_regex = re.compile(
    rf"^(?:{gke_service_prefix}/)?projects/((?:[^:]+:.)?[a-z0-9\\-]+)/(locations|zones)/([\w-]{{2,40}})/clusters/{name_segment_re}/k8s/namespaces/{name_segment_re}/apps/deployments/{name_segment_re}$"
)


class Project:
  """Represents a project."""

  def __init__(self, project_identifier):
    project_details = projects_api.Get(
        projects_util.ParseProject(project_identifier)
    )
    self.project_id = project_details.projectId
    self.project_number = project_details.projectNumber

  def resource_name(self):
    return f"projects/{self.project_id}"

  def project_id(self):
    return self.project_id

  def project_number(self):
    return self.project_number


def extract_project(uri):
  """Extracts the project from a resource URI."""
  match = re.search(_PROJECT_PATTERN, uri)
  if match:
    return match.group(1)
  return None


class ArtifactRegistryUri:
  """Parses and represents an Artifact Registry URI."""

  def __init__(self, location, project, repository, image_name, sha_suffix):
    self._location = location
    self._project = project
    self._repository = repository
    self._image_name = image_name
    self._sha_suffix = sha_suffix

  def project_id(self):
    """The project ID."""
    return self._project

  def sha_suffix(self):
    """The SHA suffix (e.g., '@sha256:...') if present, otherwise None."""
    return self._sha_suffix

  def base_uri(self):
    """The artifact URI without the SHA suffix."""
    return f"{self._location}-docker.pkg.dev/{self._project}/{self._repository}/{self._image_name}"


def validate_artifact_uri(uri):
  """Validates the artifact URI."""

  # Parse the URI if it matches the expected pattern.
  match = re.match(_ARTIFACT_URI_PATTERN, uri)
  if not match or len(match.groups()) != 5:
    return False

  location = match.group(1)
  project = match.group(2)
  repository = match.group(3)
  image_name = match.group(4)
  sha_suffix = match.group(5)
  return ArtifactRegistryUri(
      location, project, repository, image_name, sha_suffix
  )


def is_management_project(app_hub_application):
  """Checks if the app hub application is a management project."""
  return app_hub_application.startswith(_APPHUB_MANAGEMENT_PROJECT_PREFIX)


def validate_build_project(build_project):
  """Validates the build project."""
  return projects_api.Get(projects_util.ParseProject(build_project))


class GKECluster:
  """Represents a GKE cluster."""

  def __init__(self, project, location_id, cluster_id):
    self.project = project
    self.location_id = location_id
    self.cluster_id = cluster_id

  def id(self):
    return self.cluster_id

  def resource_name(self):
    return f"{gke_service_prefix}/projects/{self.project}/locations/{self.location_id}/clusters/{self.cluster_id}"


class GKENamespace:
  """Represents a GKE namespace."""

  def __init__(self, gke_cluster, namespace_id):
    self.gke_cluster = gke_cluster
    self.namespace_id = namespace_id

  def resource_name(self):
    return f"{gke_service_prefix}/projects/{self.gke_cluster.project}/locations/{self.gke_cluster.location_id}/clusters/{self.gke_cluster.cluster_id}/k8s/namespaces/{self.namespace_id}"


class GKEWorkload:
  """Represents a GKE workload."""

  def __init__(
      self,
      gke_namespace,
      deployment_id,
  ):
    self.gke_namespace = gke_namespace
    self.deployment_id = deployment_id

  def resource_name(self):
    return f"{gke_service_prefix}/projects/{self.gke_namespace.gke_cluster.project}/locations/{self.gke_namespace.gke_cluster.location_id}/clusters/{self.gke_namespace.gke_cluster.cluster_id}/k8s/namespaces/{self.gke_namespace.namespace_id}/apps/deployments/{self.deployment_id}"


def parse_gke_deployment_uri(uri):
  """Parses a GKE deployment URI into a GKEWorkload."""
  match = gke_deployment_path_regex.fullmatch(uri)
  if not match or len(match.groups()) != 6:
    return False

  return GKEWorkload(
      GKENamespace(
          GKECluster(
              match.group(1),
              match.group(3),
              match.group(4),
          ),
          match.group(5),
      ),
      deployment_id=match.group(6),
  )


class AppHubApplication:
  """Represents an App Hub Application."""

  def __init__(self, project, location_id, application_id):
    self.project = project
    self.location_id = location_id
    self.application_id = application_id

  def resource_name(self):
    return f"projects/{self.project}/locations/{self.location_id}/applications/{self.application_id}"

  def project_id(self):
    """Returns the project ID of the app hub application."""
    return self.project


def parse_app_hub_application_uri(uri):
  """Parses an App Hub Application URI into an AppHubApplication."""
  match = app_hub_application_path_regex.fullmatch(uri)
  if not match or len(match.groups()) != 3:
    raise ValueError(
        "app_hub_application must be in the format"
        " //apphub.googleapis.com/projects/{project}/locations/{location}/applications/{application}:"
        f" {uri}"
    )
  return AppHubApplication(
      match.group(1),
      match.group(2),
      match.group(3),
  )


def parse_artifact_configs(user_artifact_configs):
  """Parses a list of artifact configs into a dictionary."""
  artifact_configs_dict = {}
  if not user_artifact_configs:
    return artifact_configs_dict
  for user_config_data in user_artifact_configs:
    for uri, build_project in user_config_data.items():
      valid_uri = validate_artifact_uri(uri)
      try:
        validate_build_project(build_project)
      except apitools_exceptions.HttpForbiddenError:
        raise ValueError(
            "Permission denied when checking build project [{}]. Please"
            " ensure your account has necessary permissions "
            "or that the project exists.".format(build_project)
        )
      except apitools_exceptions.HttpBadRequestError:
        raise ValueError(
            "Invalid user provided build project ID [{}]. Please ensure it is a"
            " valid project ID".format(build_project)
        )
      except exceptions.Error as e:
        raise ValueError(
            f"Error validating build project [{build_project}]: {e}"
        )

      if valid_uri:
        artifact_configs_dict[valid_uri.base_uri()] = build_project
      else:
        raise ValueError(
            "Inalid user provided artifact uri, please check the format:"
            f" {user_config_data}"
        )
  return artifact_configs_dict
