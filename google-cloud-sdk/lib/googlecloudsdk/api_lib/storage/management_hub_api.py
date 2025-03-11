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

  def _get_cloud_storage_buckets_filter(self, bucket_ids, bucket_id_regexes):
    """Returns the cloud storage buckets filter for the given args.

    Args:
      bucket_ids: List of bucket ids to be included in the filter.
      bucket_id_regexes: List of bucket id regexes to be included in the filter.

    Returns:
      The cloud storage buckets filter message.
    """
    buckets_filter = []

    if bucket_ids is not None:
      buckets_filter.extend([
          self.messages.CloudStorageBucket(bucketId=bucket_id)
          for bucket_id in bucket_ids
      ])

    if bucket_id_regexes is not None:
      buckets_filter.extend([
          self.messages.CloudStorageBucket(bucketIdRegex=bucket_id_regex)
          for bucket_id_regex in bucket_id_regexes
      ])

    return self.messages.ManagementHubFilterCloudStorageBuckets(
        cloudStorageBuckets=buckets_filter
    )

  def _set_management_hub_filter(
      self,
      management_hub,
      inherit_from_parent=False,
      include_locations=None,
      exclude_locations=None,
      include_bucket_ids=None,
      exclude_bucket_ids=None,
      include_bucket_id_regexes=None,
      exclude_bucket_id_regexes=None,
  ):
    """Updates the management hub filter and returns update_mask.

    Args:
      management_hub: The management hub object to be updated.
      inherit_from_parent: Whether to inherit config from the parent.
      include_locations: List of locations to be included in the filter.
      exclude_locations: List of locations to be excluded in the filter.
      include_bucket_ids: List of bucket ids to be included in the filter.
      exclude_bucket_ids: List of bucket ids to be excluded in the filter.
      include_bucket_id_regexes: List of bucket id regexes to be included in the
        filter.
      exclude_bucket_id_regexes: List of bucket id regexes to be excluded in the
        filter.

    Returns:
      The update mask to be used for the request.
    """

    management_hub.filter = self.messages.ManagementHubFilter()
    update_mask = "edition_config"

    # Specific case for INHERIT config.
    if inherit_from_parent:
      management_hub.editionConfig = (
          self.messages.ManagementHub.EditionConfigValueValuesEnum.INHERIT
      )
      return update_mask+",filter"

    management_hub.editionConfig = (
        self.messages.ManagementHub.EditionConfigValueValuesEnum.STANDARD
    )

    # Set the locations filter.
    if include_locations is not None:
      management_hub.filter.includedCloudStorageLocations = (
          self.messages.ManagementHubFilterCloudStorageLocations(
              locations=include_locations
          )
      )
      update_mask += ",filter.included_cloud_storage_locations"
    if exclude_locations is not None:
      management_hub.filter.excludedCloudStorageLocations = (
          self.messages.ManagementHubFilterCloudStorageLocations(
              locations=exclude_locations
          )
      )
      update_mask += ",filter.excluded_cloud_storage_locations"

    # Set the cloud storage buckets filter.
    if include_bucket_ids is not None or include_bucket_id_regexes is not None:
      management_hub.filter.includedCloudStorageBuckets = (
          self._get_cloud_storage_buckets_filter(
              include_bucket_ids, include_bucket_id_regexes
          )
      )
      update_mask += ",filter.included_cloud_storage_buckets"
    if exclude_bucket_ids is not None or exclude_bucket_id_regexes is not None:
      management_hub.filter.excludedCloudStorageBuckets = (
          self._get_cloud_storage_buckets_filter(
              exclude_bucket_ids, exclude_bucket_id_regexes
          )
      )
      update_mask += ",filter.excluded_cloud_storage_buckets"

    return update_mask

  def _update_management_hub(
      self,
      full_id=None,
      inherit_from_parent=None,
      include_locations=None,
      exclude_locations=None,
      include_bucket_ids=None,
      exclude_bucket_ids=None,
      include_bucket_id_regexes=None,
      exclude_bucket_id_regexes=None,
      request_message_class=None,
      patch_method=None,
  ):
    """Updates the management hub for the given resource."""
    management_hub = self.messages.ManagementHub()

    management_hub.name = full_id
    update_mask = self._set_management_hub_filter(
        management_hub,
        inherit_from_parent,
        include_locations,
        exclude_locations,
        include_bucket_ids,
        exclude_bucket_ids,
        include_bucket_id_regexes,
        exclude_bucket_id_regexes,
    )

    return patch_method(
        request_message_class(
            managementHub=management_hub, updateMask=update_mask, name=full_id
        )
    )

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

  def update_project_management_hub(
      self,
      project,
      inherit_from_parent=None,
      include_locations=None,
      exclude_locations=None,
      include_bucket_ids=None,
      exclude_bucket_ids=None,
      include_bucket_id_regexes=None,
      exclude_bucket_id_regexes=None,
  ):
    """Updates the management hub for the given GCP project.

    Args:

      project: Name of the GCP project.
      inherit_from_parent: Whether to inherit config from the parent.
      include_locations: List of locations to be included in the filter.
      exclude_locations: List of locations to be excluded in the filter.
      include_bucket_ids: List of bucket ids to be included in the filter.
      exclude_bucket_ids: List of bucket ids to be excluded in the filter.
      include_bucket_id_regexes: List of bucket id regexes to be included in the
        filter.
      exclude_bucket_id_regexes: List of bucket id regexes to be excluded in the
        filter.

    Returns:
      The management hub object.
    """

    full_name = _get_full_id_string(
        resource_type="projects", resource_id=project
    )

    return self._update_management_hub(
        full_name,
        inherit_from_parent,
        include_locations,
        exclude_locations,
        include_bucket_ids,
        exclude_bucket_ids,
        include_bucket_id_regexes,
        exclude_bucket_id_regexes,
        self.messages.StorageProjectsLocationsUpdateManagementHubRequest,
        self.client.projects_locations.UpdateManagementHub,
    )

  def update_sub_folder_management_hub(
      self,
      sub_folder,
      inherit_from_parent=None,
      include_locations=None,
      exclude_locations=None,
      include_bucket_ids=None,
      exclude_bucket_ids=None,
      include_bucket_id_regexes=None,
      exclude_bucket_id_regexes=None,
  ):
    """Updates the management hub for the given GCP sub folder.

    Args:

      sub_folder: The GCP sub folder name.
      inherit_from_parent: Whether to inherit config from the parent.
      include_locations: List of locations to be included in the filter.
      exclude_locations: List of locations to be excluded in the filter.
      include_bucket_ids: List of bucket ids to be included in the filter.
      exclude_bucket_ids: List of bucket ids to be excluded in the filter.
      include_bucket_id_regexes: List of bucket id regexes to be included in the
        filter.
      exclude_bucket_id_regexes: List of bucket id regexes to be excluded in the
        filter.

    Returns:
      The management hub object.
    """
    full_name = _get_full_id_string(
        resource_type="folders", resource_id=sub_folder
    )

    return self._update_management_hub(
        full_name,
        inherit_from_parent,
        include_locations,
        exclude_locations,
        include_bucket_ids,
        exclude_bucket_ids,
        include_bucket_id_regexes,
        exclude_bucket_id_regexes,
        self.messages.StorageFoldersLocationsUpdateManagementHubRequest,
        self.client.folders_locations.UpdateManagementHub,
    )

  def update_organization_management_hub(
      self,
      organization,
      inherit_from_parent=None,
      include_locations=None,
      exclude_locations=None,
      include_bucket_ids=None,
      exclude_bucket_ids=None,
      include_bucket_id_regexes=None,
      exclude_bucket_id_regexes=None,
  ):
    """Updates the management hub for the given GCP organization.

    Args:

      organization: The GCP organization name.
      inherit_from_parent: Whether to inherit config from the parent.
      include_locations: List of locations to be included in the filter.
      exclude_locations: List of locations to be excluded in the filter.
      include_bucket_ids: List of bucket ids to be included in the filter.
      exclude_bucket_ids: List of bucket ids to be excluded in the filter.
      include_bucket_id_regexes: List of bucket id regexes to be included in the
        filter.
      exclude_bucket_id_regexes: List of bucket id regexes to be excluded in the
        filter.

    Returns:
      The management hub object.
    """
    full_name = _get_full_id_string(
        resource_type="organizations", resource_id=organization
    )

    return self._update_management_hub(
        full_name,
        inherit_from_parent,
        include_locations,
        exclude_locations,
        include_bucket_ids,
        exclude_bucket_ids,
        include_bucket_id_regexes,
        exclude_bucket_id_regexes,
        self.messages.StorageOrganizationsLocationsUpdateManagementHubRequest,
        self.client.organizations_locations.UpdateManagementHub,
    )
