# -*- coding: utf-8 -*- # Lint as: python3
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Default values and fallbacks for missing surface arguments."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import os

from googlecloudsdk.api_lib import apigee
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.apigee import errors
from googlecloudsdk.core import config
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files


def _CachedDataWithName(name):
  """Returns the contents of a named cache file.

  Cache files are saved as hidden YAML files in the gcloud config directory.

  Args:
    name: The name of the cache file.

  Returns:
    The decoded contents of the file, or an empty dictionary if the file could
    not be read for whatever reason.
  """
  config_dir = config.Paths().global_config_dir
  cache_path = os.path.join(config_dir, ".apigee-cached-" + name)
  if not os.path.isfile(cache_path):
    return {}
  try:
    return yaml.load_path(cache_path)
  except yaml.YAMLParseError:
    # Another gcloud command might be in the process of writing to the file.
    # Handle as a cache miss.
    return {}


def _SaveCachedDataWithName(data, name):
  """Saves `data` to a named cache file.

  Cache files are saved as hidden YAML files in the gcloud config directory.

  Args:
    data: The data to cache.
    name: The name of the cache file.
  """
  config_dir = config.Paths().global_config_dir
  cache_path = os.path.join(config_dir, ".apigee-cached-" + name)
  files.WriteFileContents(cache_path, yaml.dump(data))


def _DeleteCachedDataWithName(name):
  """Deletes a named cache file."""
  config_dir = config.Paths().global_config_dir
  cache_path = os.path.join(config_dir, ".apigee-cached-" + name)
  if os.path.isfile(cache_path):
    try:
      os.remove(cache_path)
    except OSError:
      return


class Fallthrough(deps.Fallthrough):
  """Base class for Apigee resource argument fallthroughs."""
  _handled_fields = []

  def __init__(self, hint, active=False, plural=False):
    super(Fallthrough, self).__init__(None, hint, active, plural)

  def __contains__(self, field):
    """Returns whether `field` is handled by this fallthrough class."""
    return field in self._handled_fields

  def _Call(self, parsed_args):
    raise NotImplementedError(
        "Subclasses of googlecloudsdk.commnand_lib.apigee.Fallthrough must "
        "actually provide a fallthrough."
    )


def _GetProjectMapping(project, user_provided_org=None):
  """Returns the project mapping for the given GCP project.

  Args:
    project: The GCP project name.
    user_provided_org: The organization ID provided by the user, if any.

  Returns:
    The project mapping for the given GCP project.
  """

  project_mappings = _CachedDataWithName("project-mapping-v2") or {}

  if user_provided_org:
    mapping = project_mappings.get(user_provided_org, None)
    if mapping:
      return mapping
    else:
      try:
        project_mapping = apigee.OrganizationsClient.ProjectMapping(
            {"organizationsId": user_provided_org}
        )
        if "organization" not in project_mapping:
          raise errors.UnauthorizedRequestError(
              message=(
                  'Permission denied on resource "organizations/%s" (or it may'
                  " not exist)"
              )
              % user_provided_org
          )

        project_mappings[project] = project_mapping
        _SaveCachedDataWithName(project_mappings, "project-mapping-v2")
        return project_mapping
      except (errors.EntityNotFoundError, errors.UnauthorizedRequestError):
        raise errors.UnauthorizedRequestError(
            message=(
                'Permission denied on resource "organizations/%s" (or it may'
                " not exist)"
            )
            % user_provided_org
        )
      except errors.RequestError as e:
        raise e

  if project not in project_mappings:
    try:
      project_mapping = apigee.OrganizationsClient.ProjectMapping(
          {"organizationsId": project}
      )
      if "organization" not in project_mapping:
        return None

      if project_mapping.get("projectId", None) != project:
        return None

      project_mappings[project] = project_mapping
      _SaveCachedDataWithName(project_mappings, "project-mapping-v2")
    except (errors.EntityNotFoundError, errors.UnauthorizedRequestError):
      return None
    except errors.RequestError as e:
      raise e

  return project_mappings[project]


def _FindMappingForProject(project):
  """Returns the Apigee organization for the given GCP project."""
  project_mapping = _CachedDataWithName("project-mapping-v2") or {}

  if project in project_mapping:
    return project_mapping[project]

  # Listing organizations is an expensive operation for users with a lot of GCP
  # projects. Since the GCP project -> Apigee organization mapping is immutable
  # once created, cache known mappings to avoid the extra API call.
  overrides = properties.VALUES.api_endpoint_overrides.apigee.Get()
  if overrides:
    list_orgs = apigee.OrganizationsClient.List()
  else:
    list_orgs = apigee.OrganizationsClient.ListOrganizationsGlobal()

  for organization in list_orgs["organizations"]:
    for matching_project in organization["projectIds"]:
      project_mapping[matching_project] = {}
      project_mapping[matching_project] = organization
  _SaveCachedDataWithName(project_mapping, "project-mapping-v2")
  _DeleteCachedDataWithName("project-mapping")

  if project not in project_mapping:
    return None

  return project_mapping[project]


def OrganizationFromGCPProject():
  """Returns the organization associated with the active GCP project."""
  project = properties.VALUES.core.project.Get()
  if project is None:
    log.warning("Neither Apigee organization nor GCP project is known.")
    return None

  # Use the cached project_mapping_v2 if available. This should handle all the
  # cases where the project name is same as the organization name when cache
  # miss happens.
  project_mapping = _GetProjectMapping(project)
  if project_mapping:
    return project_mapping["organization"]

  # Otherwise, list all organizations and update the project_mapping cache for
  # all the projects in the response.
  mapping = _FindMappingForProject(project)
  if mapping:
    return mapping["organization"]

  log.warning("No Apigee organization is known for GCP project %s.", project)
  log.warning(
      "Please provide the argument [--organization] on the command "
      "line, or set the property [api_endpoint_overrides/apigee]."
  )
  return None


class GCPProductOrganizationFallthrough(Fallthrough):
  """Falls through to the organization for the active GCP project."""

  _handled_fields = ["organization"]

  def __init__(self):
    super(GCPProductOrganizationFallthrough, self).__init__(
        "set the property [project] or provide the argument [--project] on the "
        "command line, using a Cloud Platform project with an associated "
        "Apigee organization"
    )

  def _Call(self, parsed_args):
    return OrganizationFromGCPProject()


class StaticFallthrough(Fallthrough):
  """Falls through to a hardcoded value."""

  def __init__(self, argument, value):
    super(StaticFallthrough, self).__init__(
        "leave the argument unspecified for it to be chosen automatically")
    self._handled_fields = [argument]
    self.value = value

  def _Call(self, parsed_args):
    return self.value


def FallBackToDeployedProxyRevision(args):
  """If `args` provides no revision, adds the deployed revision, if unambiguous.

  Args:
    args: a dictionary of resource identifiers which identifies an API proxy and
      an environment, to which the deployed revision should be added.

  Raises:
    EntityNotFoundError: no deployment that matches `args` exists.
    AmbiguousRequestError: more than one deployment matches `args`.
  """
  deployments = apigee.DeploymentsClient.List(args)

  if not deployments:
    error_identifier = collections.OrderedDict([
        ("organization", args["organizationsId"]),
        ("environment", args["environmentsId"]), ("api", args["apisId"])
    ])
    raise errors.EntityNotFoundError("deployment", error_identifier, "undeploy")

  if len(deployments) > 1:
    message = "Found more than one deployment that matches this request.\n"
    raise errors.AmbiguousRequestError(message + yaml.dump(deployments))

  deployed_revision = deployments[0]["revision"]
  log.status.Print("Using deployed revision `%s`" % deployed_revision)
  args["revisionsId"] = deployed_revision


def GetOrganizationLocation(organization):
  """Returns the location of the Apigee organization."""
  project = properties.VALUES.core.project.Get()
  mapping = _GetProjectMapping(project, organization)
  if mapping:
    return mapping.get("location", None)

  # Project mapping is not available, assume projectId is not same as
  # organization.
  mapping = _FindMappingForProject(project)
  if mapping:
    return mapping.get("location", None)

  log.warning("No Apigee organization is known for GCP project %s.", project)
  log.warning(
      "Please provide the argument [--organization] on the command "
      "line, or set the property [api_endpoint_overrides/apigee]."
  )
  raise errors.LocationResolutionError()
