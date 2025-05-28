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
"""Utilities for Package Rollouts ResourceBundle API."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.fleet.packages import util
from googlecloudsdk.api_lib.util import waiter

_LIST_REQUEST_BATCH_SIZE_ATTRIBUTE = 'pageSize'

RESOURCE_BUNDLE_COLLECTION = 'configdelivery.projects.locations.resourceBundles'


def _ParentPath(project, location):
  return f'projects/{project}/locations/{location}'


def _FullyQualifiedPath(project, location, name):
  return f'projects/{project}/locations/{location}/resourceBundles/{name}'


class ResourceBundlesClient(object):
  """Client for ResourceBundles in Config Delivery Package Rollouts API."""

  def __init__(self, api_version, client=None, messages=None):
    self._api_version = api_version or util.DEFAULT_API_VERSION
    self.client = client or util.GetClientInstance(self._api_version)
    self.messages = messages or util.GetMessagesModule(self.client)
    self._service = self.client.projects_locations_resourceBundles
    self.resource_bundle_waiter = waiter.CloudOperationPollerNoResources(
        operation_service=self.client.projects_locations_operations,
        get_name_func=lambda x: x.name,
    )

  def List(self, project, location, limit=None, page_size=100):
    """List ResourceBundles from Package Rollouts API.

    Args:
      project: GCP project id.
      location: Valid GCP location (e.g. us-central1).
      limit: int or None, the total number of results to return.
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results).

    Returns:
      Generator of matching devices.
    """
    list_request = (
        self.messages.ConfigdeliveryProjectsLocationsResourceBundlesListRequest(
            parent=_ParentPath(project, location),
        )
    )
    return list_pager.YieldFromList(
        self._service,
        list_request,
        field='resourceBundles',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute=_LIST_REQUEST_BATCH_SIZE_ATTRIBUTE,
    )

  def Create(self, project, location, name, description=None):
    """Create ResourceBundle for Package Rollouts API.

    Args:
      project: GCP project id.
      location: Valid GCP location (e.g. us-central1).
      name: Name of the ResourceBundle.
      description: Description of the ResourceBundle.

    Returns:
      Created ResourceBundle resource.
    """
    fully_qualified_path = _FullyQualifiedPath(project, location, name)
    resource_bundle = self.messages.ResourceBundle(
        name=fully_qualified_path, description=description, labels=None
    )
    create_request = self.messages.ConfigdeliveryProjectsLocationsResourceBundlesCreateRequest(
        resourceBundle=resource_bundle,
        parent=_ParentPath(project, location),
        resourceBundleId=name,
    )
    result = waiter.WaitFor(
        self.resource_bundle_waiter,
        self._service.Create(create_request),
        f'Creating ResourceBundle {name}',
    )
    return result

  def Delete(self, project, location, name, force=False):
    """Delete a ResourceBundle resource.

    Args:
      project: GCP project id.
      location: Valid GCP location (e.g., us-central1).
      name: Name of the ResourceBundle.
      force: Nested resource deletion flag.

    Returns:
      Empty Response Message.
    """
    fully_qualified_path = _FullyQualifiedPath(project, location, name)
    delete_req = self.messages.ConfigdeliveryProjectsLocationsResourceBundlesDeleteRequest(
        name=fully_qualified_path, force=force
    )
    return waiter.WaitFor(
        self.resource_bundle_waiter,
        self._service.Delete(delete_req),
        f'Deleting ResourceBundle {name}',
    )

  def Describe(self, project, location, name):
    """Describe a ResourceBundle resource.

    Args:
      project: GCP project id.
      location: Valid GCP location (e.g., us-central1).
      name: Name of the ResourceBundle.

    Returns:
      Requested ResourceBundle resource.
    """
    fully_qualified_path = _FullyQualifiedPath(project, location, name)
    describe_req = (
        self.messages.ConfigdeliveryProjectsLocationsResourceBundlesGetRequest(
            name=fully_qualified_path
        )
    )
    return self._service.Get(describe_req)

  def Update(
      self,
      project,
      location,
      name,
      description=None,
      labels=None,
      update_mask=None,
  ):
    """Update ResourceBundle for Package Rollouts API.

    Args:
      project: GCP project id.
      location: Valid GCP location (e.g. us-central1).
      name: Name of the ResourceBundle.
      description: Description of the ResourceBundle.
      labels: Kubernetes labels to apply to your ResourceBundle.
      update_mask: Fields to be updated.

    Returns:
      Updated ResourceBundle resource.
    """
    fully_qualified_path = _FullyQualifiedPath(project, location, name)
    resource_bundle = self.messages.ResourceBundle(
        name=fully_qualified_path, description=description, labels=labels
    )
    update_request = self.messages.ConfigdeliveryProjectsLocationsResourceBundlesPatchRequest(
        resourceBundle=resource_bundle,
        name=fully_qualified_path,
        updateMask=update_mask,
    )
    return waiter.WaitFor(
        self.resource_bundle_waiter,
        self._service.Patch(update_request),
        f'Updating ResourceBundle {name}',
    )
