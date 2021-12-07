# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Version-agnostic Fleet API client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.fleet import util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base


class FleetClient(object):
  """Client for the Fleet API with related helper methods.

  If not provided, the default client is for the alpha (v1) track. This client
  is a thin wrapper around the base client, and does not handle any exceptions.

  Fields:
    client: The raw Fleet API client for the specified release track.
    messages: The matching messages module for the client.
    resourceless_waiter: A waiter.CloudOperationPollerNoResources for polling
      LROs that do not return a resource (like Deletes).
    fleet_waiter: A waiter.CloudOperationPoller for polling fleet LROs.
  """

  def __init__(self, release_track=base.ReleaseTrack.ALPHA):
    self.client = util.GetClientInstance(release_track)
    self.messages = util.GetMessagesModule(release_track)
    self.resourceless_waiter = waiter.CloudOperationPollerNoResources(
        operation_service=self.client.projects_locations_operations)
    self.fleet_waiter = waiter.CloudOperationPoller(
        result_service=self.client.projects_locations_fleets,
        operation_service=self.client.projects_locations_operations)

  def GetFleet(self, project):
    """Gets a fleet resource from the Fleet API.

    Args:
      project: the project containing the fleet.

    Returns:
      A fleet resource

    Raises:
      apitools.base.py.HttpError: if the request returns an HTTP error
    """
    req = self.messages.GkehubProjectsLocationsFleetsGetRequest(
        name=util.FleetResourceName(project))
    return self.client.projects_locations_fleets.Get(req)

  def CreateFleet(self, displayname, project):
    """Creates a fleet resource from the Fleet API.

    Args:
      displayname: the fleet display name.
      project: the project containing the fleet.

    Returns:
      A fleet resource

    Raises:
      apitools.base.py.HttpError: if the request returns an HTTP error
    """
    fleet = self.messages.Fleet(
        displayName=displayname,
        name=util.FleetResourceName(project))
    req = self.messages.GkehubProjectsLocationsFleetsCreateRequest(
        fleet=fleet, parent=util.FleetParentName(project))
    return self.client.projects_locations_fleets.Create(req)

  def DeleteFleet(self, project):
    """Deletes a fleet resource from the Fleet API.

    Args:
      project: the project containing the fleet.

    Returns:
      A fleet resource

    Raises:
      apitools.base.py.HttpError: if the request returns an HTTP error
    """
    req = self.messages.GkehubProjectsLocationsFleetsDeleteRequest(
        name=util.FleetResourceName(project))
    return self.client.projects_locations_fleets.Delete(req)

  def UpdateFleet(self, displayname, project):
    """Updates a fleet resource from the Fleet API.

    Args:
      displayname: the fleet display name.
      project: the project containing the fleet.

    Returns:
      A fleet resource

    Raises:
      apitools.base.py.HttpError: if the request returns an HTTP error
    """
    # Fleet containing fields with updated value(s)
    fleet = self.messages.Fleet(displayName=displayname)
    # Fields to be updated (currently only display_name)
    mask = 'display_name'
    req = self.messages.GkehubProjectsLocationsFleetsPatchRequest(
        fleet=fleet,
        name=util.FleetResourceName(project),
        updateMask=mask)
    return self.client.projects_locations_fleets.Patch(req)

  def ListFleets(self, project, organization):
    """Lists fleets in an organization.

    Args:
      project: the project to search.
      organization: the organization to search.

    Returns:
      A ListFleetResponse (list of fleets and next page token)

    Raises:
      apitools.base.py.HttpError: if the request returns an HTTP error
    """
    if organization:
      parent = util.FleetOrgParentName(organization)
    else:
      parent = util.FleetParentName(project)
    # Misleading name, parent is usually org, not project
    req = self.messages.GkehubProjectsLocationsFleetsListRequest(
        pageToken='',
        parent=parent)
    return list_pager.YieldFromList(
        self.client.projects_locations_fleets, req, field='fleets',
        batch_size_attribute=None)
