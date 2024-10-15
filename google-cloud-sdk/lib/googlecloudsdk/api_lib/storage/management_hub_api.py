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


class ManagementHubApi:
  """Client for Management Hub API."""

  def __init__(self):
    super(ManagementHubApi, self).__init__()
    self.client = core_apis.GetClientInstance("storage", "v2")
    self.messages = core_apis.GetMessagesModule("storage", "v2")
    self.edition_config = {
        "INHERIT": (
            self.messages.ManagementHub.EditionConfigValueValuesEnum.INHERIT
        ),
        "DISABLED": (
            self.messages.ManagementHub.EditionConfigValueValuesEnum.DISABLED
        ),
        "STANDARD": (
            self.messages.ManagementHub.EditionConfigValueValuesEnum.STANDARD
        ),
    }

  def get_sub_folder_management_hub(self, folder_id):
    """Gets the management hub for the given sub folder.

    Args:
      folder_id: Id of the GCP hierarchy folder.

    Returns:
      The management hub object for the given sub folder.
    """
    full_name = f"folders/{folder_id}/locations/global/managementHub"

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
    full_name = f"projects/{project_name}/locations/global/managementHub"

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
    full_name = (
        f"organizations/{organization_id}/locations/global/managementHub"
    )

    request = (
        self.messages.StorageOrganizationsLocationsGetManagementHubRequest(
            name=full_name
        )
    )
    return self.client.organizations_locations.GetManagementHub(request)
