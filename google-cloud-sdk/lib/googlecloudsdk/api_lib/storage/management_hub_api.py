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
"""Client for interacting with Management Hub."""

from googlecloudsdk.api_lib.util import apis as core_apis


_FULL_UPDATE_MASK = "edition_config,filter"
_FOLDER_RESOURCE_TYPE = "folders"
_ORGANIZATION_RESOURCE_TYPE = "organizations"
_PROJECT_RESOURCE_TYPE = "projects"


def _get_full_id_string(resource_type: str, resource_id: str) -> str:
  """Returns the full id of the resource."""
  return f"{resource_type}/{resource_id}/locations/global/managementHub"


# TODO: b/373586209 - Add GCS API error handling decorators for the API methods
# if needed.
class ManagementHubApi:
  """Client for Management Hub API."""

  def __init__(self):
    super(ManagementHubApi, self).__init__()
    self.client = core_apis.GetClientInstance("storage", "v2")
    self.messages = core_apis.GetMessagesModule("storage", "v2")

  def _disable_management_hub(
      self,
      full_id=None,
      request_message_class=None,
      patch_method=None,
  ):
    """Disables the management hub for the given resource."""
    management_hub = self.messages.ManagementHub()
    management_hub.editionConfig = (
        self.messages.ManagementHub.EditionConfigValueValuesEnum.DISABLED
    )
    management_hub.name = full_id

    request = request_message_class(
        managementHub=management_hub,
        updateMask=_FULL_UPDATE_MASK,
        name=full_id,
    )

    return patch_method(request)

  def get_sub_folder_management_hub(self, folder_id):
    """Gets the management hub for the given sub folder.

    Args:
      folder_id: Id of the GCP hierarchy folder.

    Returns:
      The management hub object for the given sub folder.
    """
    full_name = _get_full_id_string(
        resource_type=_FOLDER_RESOURCE_TYPE, resource_id=folder_id
    )

    request = self.messages.StorageFoldersLocationsGetManagementHubRequest(
        name=full_name
    )
    return self.client.folders_locations.GetManagementHub(request)

  def get_project_management_hub(self, project_name):
    """Gets the management hub for the given project.

    Args:
      project_name: Name of the GCP project.

    Returns:
      The management hub object for the given project.
    """
    full_name = _get_full_id_string(
        resource_type=_PROJECT_RESOURCE_TYPE, resource_id=project_name
    )

    request = self.messages.StorageProjectsLocationsGetManagementHubRequest(
        name=full_name
    )
    return self.client.projects_locations.GetManagementHub(request)

  def get_organization_management_hub(self, organization_id):
    """Gets the management hub for the given organization.

    Args:
      organization_id: Id of the GCP organization.

    Returns:
      The management hub object for the given organization.
    """
    full_name = _get_full_id_string(
        resource_type=_ORGANIZATION_RESOURCE_TYPE, resource_id=organization_id
    )

    request = (
        self.messages.StorageOrganizationsLocationsGetManagementHubRequest(
            name=full_name
        )
    )
    return self.client.organizations_locations.GetManagementHub(request)

  def disable_project_management_hub(self, project_name):
    """Disables the management hub for the given project.

    Args:
      project_name: Name of the GCP project.

    Returns:
      The management hub object for the given project.
    """
    full_name = _get_full_id_string(
        resource_type=_PROJECT_RESOURCE_TYPE, resource_id=project_name
    )

    return self._disable_management_hub(
        full_id=full_name,
        request_message_class=self.messages.StorageProjectsLocationsUpdateManagementHubRequest,
        patch_method=self.client.projects_locations.UpdateManagementHub,
    )

  def disable_organization_management_hub(self, organization_id):
    """Disables the management hub for the given organization.

    Args:
      organization_id: Id of the GCP organization.

    Returns:
      The management hub object for the given organization.
    """
    full_name = _get_full_id_string(
        resource_type=_ORGANIZATION_RESOURCE_TYPE, resource_id=organization_id
    )

    return self._disable_management_hub(
        full_id=full_name,
        request_message_class=self.messages.StorageOrganizationsLocationsUpdateManagementHubRequest,
        patch_method=self.client.organizations_locations.UpdateManagementHub,
    )

  def disable_sub_folder_management_hub(self, sub_folder_id):
    """Disables the management hub for the given sub folder.

    Args:
      sub_folder_id: Id of the GCP hierarchy folder.

    Returns:
      The management hub object for the given sub folder.
    """
    full_name = _get_full_id_string(
        resource_type=_FOLDER_RESOURCE_TYPE, resource_id=sub_folder_id
    )

    return self._disable_management_hub(
        full_id=full_name,
        request_message_class=self.messages.StorageFoldersLocationsUpdateManagementHubRequest,
        patch_method=self.client.folders_locations.UpdateManagementHub,
    )
