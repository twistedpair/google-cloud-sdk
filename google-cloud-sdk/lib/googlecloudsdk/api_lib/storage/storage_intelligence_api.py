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
"""Client for interacting with Storage Intelligence API."""

from googlecloudsdk.api_lib.util import apis as core_apis


_FULL_UPDATE_MASK = "edition_config,filter"
_FOLDER_RESOURCE_TYPE = "folders"
_ORGANIZATION_RESOURCE_TYPE = "organizations"
_PROJECT_RESOURCE_TYPE = "projects"


def _get_full_id_string(resource_type: str, resource_id: str) -> str:
  """Returns the full id of the resource."""
  return f"{resource_type}/{resource_id}/locations/global/intelligenceConfig"


# TODO: b/373586209 - Add GCS API error handling decorators for the API methods
# if needed.
class StorageIntelligenceApi:
  """Client for Storage Intelligence API."""

  def __init__(self):
    super(StorageIntelligenceApi, self).__init__()
    self.client = core_apis.GetClientInstance("storage", "v2")
    self.messages = core_apis.GetMessagesModule("storage", "v2")

  def _disable_intelligence(
      self,
      full_id=None,
      request_message_class=None,
      patch_method=None,
  ):
    """Disables Intelligence for the given resource."""
    intelligence_config = self.messages.IntelligenceConfig()
    intelligence_config.editionConfig = (
        self.messages.IntelligenceConfig.EditionConfigValueValuesEnum.DISABLED
    )
    intelligence_config.name = full_id

    request = request_message_class(
        intelligenceConfig=intelligence_config,
        updateMask=_FULL_UPDATE_MASK,
        name=full_id,
    )

    return patch_method(request)

  def _set_intelligence_filter(
      self,
      intelligence_config,
      inherit_from_parent=False,
      trial_edition=False,
      include_locations=None,
      exclude_locations=None,
      include_bucket_id_regexes=None,
      exclude_bucket_id_regexes=None,
  ):
    """Updates the Intelligence filter and returns update_mask.

    Args:
      intelligence_config: The Intelligence Config object to be updated.
      inherit_from_parent: Whether to inherit config from the parent.
      trial_edition: Whether to enable Storage Intelligence for TRIAL edition.
      include_locations: List of locations to be included in the filter.
      exclude_locations: List of locations to be excluded in the filter.
      include_bucket_id_regexes: List of bucket id regexes to be included in the
        filter.
      exclude_bucket_id_regexes: List of bucket id regexes to be excluded in the
        filter.

    Returns:
      The update mask to be used for the request.
    """

    intelligence_config.filter = self.messages.Filter()
    update_mask = "edition_config"

    # Specific case for INHERIT config.
    if inherit_from_parent:
      intelligence_config.editionConfig = (
          self.messages.IntelligenceConfig.EditionConfigValueValuesEnum.INHERIT
      )
      return update_mask+",filter"

    intelligence_config.editionConfig = (
        self.messages.IntelligenceConfig.EditionConfigValueValuesEnum.TRIAL
        if trial_edition
        else self.messages.IntelligenceConfig.EditionConfigValueValuesEnum.STANDARD
    )

    # Set the locations filter.
    if include_locations is not None:
      intelligence_config.filter.includedCloudStorageLocations = (
          self.messages.CloudStorageLocations(locations=include_locations)
      )
      update_mask += ",filter.included_cloud_storage_locations"
    if exclude_locations is not None:
      intelligence_config.filter.excludedCloudStorageLocations = (
          self.messages.CloudStorageLocations(locations=exclude_locations)
      )
      update_mask += ",filter.excluded_cloud_storage_locations"

    # Set the bucket id regex filter.
    if include_bucket_id_regexes is not None:
      intelligence_config.filter.includedCloudStorageBuckets = (
          self.messages.CloudStorageBuckets(
              bucketIdRegexes=include_bucket_id_regexes
          )
      )
      update_mask += ",filter.included_cloud_storage_buckets"
    if exclude_bucket_id_regexes is not None:
      intelligence_config.filter.excludedCloudStorageBuckets = (
          self.messages.CloudStorageBuckets(
              bucketIdRegexes=exclude_bucket_id_regexes
          )
      )
      update_mask += ",filter.excluded_cloud_storage_buckets"

    return update_mask

  def _update_intelligence_config(
      self,
      full_id=None,
      inherit_from_parent=False,
      trial_edition=False,
      include_locations=None,
      exclude_locations=None,
      include_bucket_id_regexes=None,
      exclude_bucket_id_regexes=None,
      request_message_class=None,
      patch_method=None,
  ):
    """Updates the Intelligence Config for the given resource."""
    intelligence_config = self.messages.IntelligenceConfig()

    intelligence_config.name = full_id
    update_mask = self._set_intelligence_filter(
        intelligence_config,
        inherit_from_parent,
        trial_edition,
        include_locations,
        exclude_locations,
        include_bucket_id_regexes,
        exclude_bucket_id_regexes,
    )

    return patch_method(
        request_message_class(
            intelligenceConfig=intelligence_config,
            updateMask=update_mask,
            name=full_id,
        )
    )

  def get_sub_folder_intelligence_config(self, folder_id):
    """Gets the Intelligence Config for the given sub folder.

    Args:
      folder_id: Id of the GCP hierarchy folder.

    Returns:
      The Intelligence Config object.
    """
    full_name = _get_full_id_string(
        resource_type=_FOLDER_RESOURCE_TYPE, resource_id=folder_id
    )

    request = self.messages.StorageFoldersLocationsGetIntelligenceConfigRequest(
        name=full_name
    )
    return self.client.folders_locations.GetIntelligenceConfig(request)

  def get_project_intelligence_config(self, project_name):
    """Gets the Intelligence Config for the given project.

    Args:
      project_name: Name of the GCP project.

    Returns:
      The Intelligence Config object.
    """
    full_name = _get_full_id_string(
        resource_type=_PROJECT_RESOURCE_TYPE, resource_id=project_name
    )

    request = (
        self.messages.StorageProjectsLocationsGetIntelligenceConfigRequest(
            name=full_name
        )
    )
    return self.client.projects_locations.GetIntelligenceConfig(request)

  def get_organization_intelligence_config(self, organization_id):
    """Gets the Intelligence Config for the given organization.

    Args:
      organization_id: Id of the GCP organization.

    Returns:
      The Intelligence Config object.
    """
    full_name = _get_full_id_string(
        resource_type=_ORGANIZATION_RESOURCE_TYPE, resource_id=organization_id
    )

    request = (
        self.messages.StorageOrganizationsLocationsGetIntelligenceConfigRequest(
            name=full_name
        )
    )
    return self.client.organizations_locations.GetIntelligenceConfig(request)

  def disable_project_intelligence_config(self, project_name):
    """Disables the Storage Intelligence for the given project.

    Args:
      project_name: Name of the GCP project.

    Returns:
      The Intelligence Config object.
    """
    full_name = _get_full_id_string(
        resource_type=_PROJECT_RESOURCE_TYPE, resource_id=project_name
    )

    return self._disable_intelligence(
        full_id=full_name,
        request_message_class=self.messages.StorageProjectsLocationsUpdateIntelligenceConfigRequest,
        patch_method=self.client.projects_locations.UpdateIntelligenceConfig,
    )

  def disable_organization_intelligence_config(self, organization_id):
    """Disables the Storage Intelligence for the given organization.

    Args:
      organization_id: Id of the GCP organization.

    Returns:
      The Intelligence Config object.
    """
    full_name = _get_full_id_string(
        resource_type=_ORGANIZATION_RESOURCE_TYPE, resource_id=organization_id
    )

    return self._disable_intelligence(
        full_id=full_name,
        request_message_class=self.messages.StorageOrganizationsLocationsUpdateIntelligenceConfigRequest,
        patch_method=self.client.organizations_locations.UpdateIntelligenceConfig,
    )

  def disable_sub_folder_intelligence_config(self, sub_folder_id):
    """Disables the Storage Intelligence for the given sub folder.

    Args:
      sub_folder_id: Id of the GCP hierarchy folder.

    Returns:
      The Intelligence Config object.
    """
    full_name = _get_full_id_string(
        resource_type=_FOLDER_RESOURCE_TYPE, resource_id=sub_folder_id
    )

    return self._disable_intelligence(
        full_id=full_name,
        request_message_class=self.messages.StorageFoldersLocationsUpdateIntelligenceConfigRequest,
        patch_method=self.client.folders_locations.UpdateIntelligenceConfig,
    )

  def update_project_intelligence_config(
      self,
      project,
      inherit_from_parent=False,
      trial_edition=False,
      include_locations=None,
      exclude_locations=None,
      include_bucket_id_regexes=None,
      exclude_bucket_id_regexes=None,
  ):
    """Updates the Intelligence Config for the given GCP project.

    Args:
      project: Name of the GCP project.
      inherit_from_parent: Whether to inherit config from the parent.
      trial_edition: Whether to enable Storage Intelligence for TRIAL edition.
      include_locations: List of locations to be included in the filter.
      exclude_locations: List of locations to be excluded in the filter.
      include_bucket_id_regexes: List of bucket id regexes to be included in the
        filter.
      exclude_bucket_id_regexes: List of bucket id regexes to be excluded in the
        filter.

    Returns:
      The Intelligence Config object.
    """

    full_name = _get_full_id_string(
        resource_type="projects", resource_id=project
    )

    return self._update_intelligence_config(
        full_name,
        inherit_from_parent,
        trial_edition,
        include_locations,
        exclude_locations,
        include_bucket_id_regexes,
        exclude_bucket_id_regexes,
        self.messages.StorageProjectsLocationsUpdateIntelligenceConfigRequest,
        self.client.projects_locations.UpdateIntelligenceConfig,
    )

  def update_sub_folder_intelligence_config(
      self,
      sub_folder,
      inherit_from_parent=False,
      trial_edition=False,
      include_locations=None,
      exclude_locations=None,
      include_bucket_id_regexes=None,
      exclude_bucket_id_regexes=None,
  ):
    """Updates the Intelligence Config for the given GCP sub folder.

    Args:
      sub_folder: The GCP sub folder name.
      inherit_from_parent: Whether to inherit config from the parent.
      trial_edition: Whether to enable Storage Intelligence for TRIAL edition.
      include_locations: List of locations to be included in the filter.
      exclude_locations: List of locations to be excluded in the filter.
      include_bucket_id_regexes: List of bucket id regexes to be included in the
        filter.
      exclude_bucket_id_regexes: List of bucket id regexes to be excluded in the
        filter.

    Returns:
      The Intelligence Config object.
    """
    full_name = _get_full_id_string(
        resource_type="folders", resource_id=sub_folder
    )

    return self._update_intelligence_config(
        full_name,
        inherit_from_parent,
        trial_edition,
        include_locations,
        exclude_locations,
        include_bucket_id_regexes,
        exclude_bucket_id_regexes,
        self.messages.StorageFoldersLocationsUpdateIntelligenceConfigRequest,
        self.client.folders_locations.UpdateIntelligenceConfig,
    )

  def update_organization_intelligence_config(
      self,
      organization,
      inherit_from_parent=False,
      trial_edition=False,
      include_locations=None,
      exclude_locations=None,
      include_bucket_id_regexes=None,
      exclude_bucket_id_regexes=None,
  ):
    """Updates the Intelligence Config for the given GCP organization.

    Args:
      organization: The GCP organization name.
      inherit_from_parent: Whether to inherit config from the parent.
      trial_edition: Whether to enable Storage Intelligence for TRIAL edition.
      include_locations: List of locations to be included in the filter.
      exclude_locations: List of locations to be excluded in the filter.
      include_bucket_id_regexes: List of bucket id regexes to be included in the
        filter.
      exclude_bucket_id_regexes: List of bucket id regexes to be excluded in the
        filter.

    Returns:
      The Intelligence Config object.
    """
    full_name = _get_full_id_string(
        resource_type="organizations", resource_id=organization
    )

    return self._update_intelligence_config(
        full_name,
        inherit_from_parent,
        trial_edition,
        include_locations,
        exclude_locations,
        include_bucket_id_regexes,
        exclude_bucket_id_regexes,
        self.messages.StorageOrganizationsLocationsUpdateIntelligenceConfigRequest,
        self.client.organizations_locations.UpdateIntelligenceConfig,
    )
