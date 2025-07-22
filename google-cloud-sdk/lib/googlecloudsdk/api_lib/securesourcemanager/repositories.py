# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""The Secure Source Manager repositories client module."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources

VERSION_MAP = {base.ReleaseTrack.ALPHA: 'v1'}


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetClientInstance('securesourcemanager', api_version)


class RepositoriesClient(object):
  """Client for Secure Source Manager repositories."""

  def __init__(self):
    self.client = GetClientInstance(base.ReleaseTrack.ALPHA)
    self.messages = self.client.MESSAGES_MODULE
    self._service = self.client.projects_locations_repositories
    self._resource_parser = resources.Registry()
    self._resource_parser.RegisterApiByName('securesourcemanager', 'v1')

  def Create(
      self,
      repository_ref,
      instance_id,
      description,
      default_branch,
      gitignores,
      license_name,
      readme,
  ):
    """Create a new Secure Source Manager repository.

    Args:
      repository_ref: a resource reference to
        securesourcemanager.projects.locations.repositories.
      instance_id: a resource id for
        securesourcemanager.projects.locations.instances.
      description: description of the repository
      default_branch: default branch name of the repository
      gitignores: list of gitignore template names
      license_name: license template name
      readme: README template name

    Returns:
      Created repository.
    """
    initial_config = self.messages.InitialConfig(
        defaultBranch=default_branch,
        gitignores=gitignores,
        license=license_name,
        readme=readme,
    )
    instance = self._resource_parser.Parse(
        None,
        params={
            'projectsId': repository_ref.projectsId,
            'locationsId': repository_ref.locationsId,
            'instancesId': instance_id,
        },
        collection='securesourcemanager.projects.locations.instances',
    )
    repository = self.messages.Repository(
        description=description,
        instance=instance.RelativeName(),
        initialConfig=initial_config,
    )
    create_req = self.messages.SecuresourcemanagerProjectsLocationsRepositoriesCreateRequest(
        parent=repository_ref.Parent().RelativeName(),
        repository=repository,
        repositoryId=repository_ref.repositoriesId,
    )
    return self._service.Create(create_req)

  def Describe(self, repository_ref):
    """Get metadata for a Secure Source Manager repository.

    Args:
      repository_ref: a resource reference to
        securesourcemanager.projects.locations.repositories.

    Returns:
    Description of repository.
    """
    get_req = self.messages.SecuresourcemanagerProjectsLocationsRepositoriesGetRequest(
        name=repository_ref.RelativeName()
    )
    return self._service.Get(get_req)

  def Delete(self, repository_ref, allow_missing):
    """Delete a Secure Source Manager repository.

    Args:
      repository_ref: a Resource reference to a
        securesourcemanager.projects.locations.repositories resource.
      allow_missing: Optional. If set to true, and the repository is not found,
        the request will succeed but no action will be taken on the server.

    Returns:
    Deleted Repository Resource.
    """

    delete_req = self.messages.SecuresourcemanagerProjectsLocationsRepositoriesDeleteRequest(
        allowMissing=allow_missing, name=repository_ref.RelativeName()
    )
    return self._service.Delete(delete_req)

  def List(self, location_ref, instance_id, page_size, limit):
    """Lists repositories in a Secure Source Manager instance.

    Args:
      location_ref: a Resource reference to a
        securesourcemanager.projects.locations resource.
      instance_id: a resource id for
        securesourcemanager.projects.locations.instances.
      page_size: Optional. Requested page size. Server may return fewer items
        than requested. If unspecified, server will pick an appropriate default.
      limit: Optional. The maximum number of items to return. If unspecified,
        treated as unlimited.

    Returns:
    List of repositories.
    """
    instance = self._resource_parser.Parse(
        None,
        params={
            'projectsId': location_ref.projectsId,
            'locationsId': location_ref.locationsId,
            'instancesId': instance_id,
        },
        collection='securesourcemanager.projects.locations.instances',
    )
    list_req = self.messages.SecuresourcemanagerProjectsLocationsRepositoriesListRequest(
        parent=location_ref.RelativeName(),
        instance=instance.RelativeName(),
    )

    return list(
        list_pager.YieldFromList(
            self._service,
            list_req,
            limit=limit,
            batch_size=page_size,
            field='repositories',
            batch_size_attribute='pageSize',
        )
    )

  def Update(self, repository_ref, update_mask, validate_only, description):
    """Update a Secure Source Manager repository.

    Args:
      repository_ref: a Resource reference to a
        securesourcemanager.projects.locations.repositories resource.
      update_mask: Field mask is used to specify the fields to be overwritten in
        the repository resource by the update.
      validate_only: Optional. If set to true, and the repository is not found,
        the request will succeed but no action will be taken on the server.
      description: Description of the repository.

    Returns:
    Updated Repository Resource.
    """

    repository = self.messages.Repository(
        name=repository_ref.RelativeName(),
        description=description,
    )
    update_req = self.messages.SecuresourcemanagerProjectsLocationsRepositoriesPatchRequest(
        name=repository_ref.RelativeName(),
        repository=repository,
        updateMask=','.join(update_mask),
        validateOnly=validate_only,
    )
    return self._service.Patch(update_req)
