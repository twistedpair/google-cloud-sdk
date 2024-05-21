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
"""Utilities for Package Rollouts FleetPackages API."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.command_lib.container.fleet.packages import utils
from googlecloudsdk.command_lib.export import util as export_util
from googlecloudsdk.core import resources


def GetClientInstance(no_http=False):
  return apis.GetClientInstance(
      'configdelivery', utils.ApiVersion(), no_http=no_http
  )


def GetMessagesModule(client=None):
  client = client or GetClientInstance()
  return client.MESSAGES_MODULE


def GetFleetPackageURI(resource):
  fleet_package = resources.REGISTRY.ParseRelativeName(
      resource.name,
      collection='configdelivery.projects.locations.fleetPackages',
  )
  return fleet_package.SelfLink()


def GetSchemaPath():
  return export_util.GetSchemaPath('configdelivery', 'v1alpha', 'FleetPackage')


def _ParentPath(project, location):
  return f'projects/{project}/locations/{location}'


def _FullyQualifiedPath(project, location, name):
  return f'projects/{project}/locations/{location}/fleetPackages/{name}'


class FleetPackagesClient(object):
  """Client for FleetPackages in Config Delivery Package Rollouts API."""

  def __init__(self, client=None, messages=None):
    self.client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule(client)
    self._service = self.client.projects_locations_fleetPackages
    self.fleet_package_waiter = waiter.CloudOperationPollerNoResources(
        operation_service=self.client.projects_locations_operations,
        get_name_func=lambda x: x.name,
    )

  def List(self, project, location, limit=None, page_size=100):
    """List FleetPackages from Package Rollouts API.

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
        self.messages.ConfigdeliveryProjectsLocationsFleetPackagesListRequest(
            parent=_ParentPath(project, location)
        )
    )
    return list_pager.YieldFromList(
        self._service,
        list_request,
        field='fleetPackages',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize',
    )

  def Create(self, fleet_package, fleet_package_id, parent):
    """Create FleetPackage for Package Rollouts API.

    Args:
      fleet_package: A parsed FleetPackage resource
      fleet_package_id: Name of FleetPackage
      parent: Parent GCP location

    Returns:
      Created FleetPackage resource.
    """
    create_request = (
        self.messages.ConfigdeliveryProjectsLocationsFleetPackagesCreateRequest(
            fleetPackage=fleet_package,
            fleetPackageId=fleet_package_id,
            parent=parent,
        )
    )
    return waiter.WaitFor(
        self.fleet_package_waiter,
        self._service.Create(create_request),
        f'Creating FleetPackage {fleet_package_id}',
    )

  def Delete(self, project, location, name, force=False):
    """Delete a FleetPackage resource.

    Args:
      project: GCP project id.
      location: Valid GCP location (e.g., us-central1).
      name: Name of the FleetPackage.
      force: Whether to delete release of FleetPackage's ResourceBundle.

    Returns:
      Empty Response Message.
    """
    fully_qualified_path = _FullyQualifiedPath(project, location, name)
    delete_req = (
        self.messages.ConfigdeliveryProjectsLocationsFleetPackagesDeleteRequest(
            name=fully_qualified_path, force=force
        )
    )
    return waiter.WaitFor(
        self.fleet_package_waiter,
        self._service.Delete(delete_req),
        f'Deleting FleetPackage {fully_qualified_path}',
    )

  def Describe(self, project, location, name):
    """Describe a FleetPackage resource.

    Args:
      project: GCP project id.
      location: Valid GCP location (e.g., us-central1).
      name: Name of the FleetPackage.

    Returns:
      Empty Response Message.
    """
    fully_qualified_path = _FullyQualifiedPath(project, location, name)
    describe_req = (
        self.messages.ConfigdeliveryProjectsLocationsFleetPackagesGetRequest(
            name=fully_qualified_path
        )
    )
    return self._service.Get(describe_req)

  def Update(self, fleet_package, name):
    """Create FleetPackage for Package Rollouts API.

    Args:
      fleet_package: A parsed FleetPackage resource
      name: Fully qualified name of the FleetPackage.

    Returns:
      Updated FleetPackage resource.
    """
    update_request = (
        self.messages.ConfigdeliveryProjectsLocationsFleetPackagesPatchRequest(
            fleetPackage=fleet_package, name=name, updateMask=None
        )
    )
    return waiter.WaitFor(
        self.fleet_package_waiter,
        self._service.Patch(update_request),
        f'Updating FleetPackage {name}',
    )
