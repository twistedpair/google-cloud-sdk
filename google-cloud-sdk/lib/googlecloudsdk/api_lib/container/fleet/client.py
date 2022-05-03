# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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

import collections

from apitools.base.py import encoding
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.fleet import util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources


class HubClient(object):
  """Client for the GKE Hub API with related helper methods.

  If not provided, the default client is for the GA (v1) track. This client
  is a thin wrapper around the base client, and does not handle any exceptions.

  Fields:
    client: The raw GKE Hub API client for the specified release track.
    messages: The matching messages module for the client.
    resourceless_waiter: A waiter.CloudOperationPollerNoResources for polling
      LROs that do not return a resource (like Deletes).
    feature_waiter: A waiter.CloudOperationPoller for polling Feature LROs.
  """

  def __init__(self, release_track=base.ReleaseTrack.GA):
    self.client = util.GetClientInstance(release_track)
    self.messages = util.GetMessagesModule(release_track)
    self.resourceless_waiter = waiter.CloudOperationPollerNoResources(
        operation_service=self.client.projects_locations_operations)
    self.feature_waiter = waiter.CloudOperationPoller(
        result_service=self.client.projects_locations_features,
        operation_service=self.client.projects_locations_operations)
    # TODO(b/181243034): Add a membership_waiter when v1alpha+ is ready.

  def CreateFeature(self, parent, feature_id, feature):
    """Creates a Feature and returns the long-running operation message.

    Args:
      parent: The parent in the form /projects/*/locations/*.
      feature_id: The short ID for this Feature in the Hub API.
      feature: A Feature message specifying the Feature data to create.

    Returns:
      The long running operation reference. Use the feature_waiter and
      OperationRef to watch the operation and get the final status, typically
      using waiter.WaitFor to present a user-friendly spinner.
    """
    req = self.messages.GkehubProjectsLocationsFeaturesCreateRequest(
        feature=feature,
        featureId=feature_id,
        parent=parent,
    )
    return self.client.projects_locations_features.Create(req)

  def GetFeature(self, name):
    """Gets a Feature from the Hub API.

    Args:
      name: The full resource name in the form
        /projects/*/locations/*/features/*.

    Returns:
      The Feature message.
    """
    req = self.messages.GkehubProjectsLocationsFeaturesGetRequest(name=name)
    return self.client.projects_locations_features.Get(req)

  def ListFeatures(self, parent):
    """Lists Features from the Hub API.

    Args:
      parent: The parent in the form /projects/*/locations/*.

    Returns:
      A list of Features.
    """
    req = self.messages.GkehubProjectsLocationsFeaturesListRequest(
        parent=parent)
    # We skip the pagination for now, since it will never be hit.
    resp = self.client.projects_locations_features.List(req)
    return resp.resources

  def UpdateFeature(self, name, mask, feature):
    """Creates a Feature and returns the long-running operation message.

    Args:
      name: The full resource name in the form
        /projects/*/locations/*/features/*.
      mask: A string list of the field paths to update.
      feature: A Feature message containing the Feature data to update using the
        mask.

    Returns:
      The long running operation reference. Use the feature_waiter and
      OperationRef to watch the operation and get the final status, typically
      using waiter.WaitFor to present a user-friendly spinner.
    """
    req = self.messages.GkehubProjectsLocationsFeaturesPatchRequest(
        name=name,
        updateMask=','.join(mask),
        feature=feature,
    )
    return self.client.projects_locations_features.Patch(req)

  def DeleteFeature(self, name, force=False):
    """Deletes a Feature and returns the long-running operation message.

    Args:
      name: The full resource name in the form
        /projects/*/locations/*/features/*.
      force: Indicates the Feature should be force deleted.

    Returns:
      The long running operation. Use the feature_waiter and OperationRef to
      watch the operation and get the final status, typically using
      waiter.WaitFor to present a user-friendly spinner.
    """
    req = self.messages.GkehubProjectsLocationsFeaturesDeleteRequest(
        name=name,
        force=force,
    )
    return self.client.projects_locations_features.Delete(req)

  @staticmethod
  def OperationRef(op):
    """Parses a gkehub Operation reference from an operation."""
    return resources.REGISTRY.ParseRelativeName(
        op.name, collection='gkehub.projects.locations.operations')

  @staticmethod
  def ToPyDict(proto_map_value):
    """Helper to convert proto map Values to normal dictionaries.

    encoding.MessageToPyValue recursively converts values to dicts, while this
    method leaves the map values as proto objects.

    Args:
      proto_map_value: The map field "Value". For example, the `Feature.labels`
        value (of type `Features.LabelsValue`). Can be None.

    Returns:
      An OrderedDict of the map's keys/values, in the original order.
    """
    if proto_map_value is None or proto_map_value.additionalProperties is None:
      return {}
    return collections.OrderedDict(
        (p.key, p.value) for p in proto_map_value.additionalProperties)

  @staticmethod
  def ToProtoMap(map_value_cls, value):
    """encoding.DictToAdditionalPropertyMessage wrapper to match ToPyDict."""
    return encoding.DictToAdditionalPropertyMessage(
        value, map_value_cls, sort_items=True)

  def ToMembershipSpecs(self, spec_map):
    """Convenience wrapper for ToProtoMap for Feature.membershipSpecs."""
    return self.ToProtoMap(self.messages.Feature.MembershipSpecsValue, spec_map)


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
        displayName=displayname, name=util.FleetResourceName(project))
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
        fleet=fleet, name=util.FleetResourceName(project), updateMask=mask)
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
        pageToken='', parent=parent)
    return list_pager.YieldFromList(
        self.client.projects_locations_fleets,
        req,
        field='fleets',
        batch_size_attribute=None)

  def GetNamespace(self, project, name):
    """Gets a namespace resource from the GKEHub API.

    Args:
      project: the project containing the namespace.
      name: the namespace name.

    Returns:
      A namespace resource

    Raises:
      apitools.base.py.HttpError: if the request returns an HTTP error
    """
    req = self.messages.GkehubProjectsLocationsNamespacesGetRequest(
        name=util.NamespaceResourceName(project, name))
    return self.client.projects_locations_namespaces.Get(req)

  def CreateNamespace(self, name, project):
    """Creates a namespace resource from the GKEHub API.

    Args:
      name: the namespace name.
      project: the project containing the namespace.

    Returns:
      A namespace resource

    Raises:
      apitools.base.py.HttpError: if the request returns an HTTP error
    """
    namespace = self.messages.Namespace(
        name=util.NamespaceResourceName(project, name))
    req = self.messages.GkehubProjectsLocationsNamespacesCreateRequest(
        namespace=namespace,
        namespaceId=name,
        parent=util.NamespaceParentName(project))
    return self.client.projects_locations_namespaces.Create(req)

  def DeleteNamespace(self, project, name):
    """Deletes a namespace resource from the fleet.

    Args:
      project: the project containing the namespace.
      name: the name of the namespace.

    Returns:
      An operation

    Raises:
      apitools.base.py.HttpError: if the request returns an HTTP error
    """
    req = self.messages.GkehubProjectsLocationsNamespacesDeleteRequest(
        name=util.NamespaceResourceName(project, name))
    return self.client.projects_locations_namespaces.Delete(req)

  def UpdateNamespace(self, name, project):
    """Updates a namespace resource in the fleet.

    Args:
      name: the namespace name.
      project: the project containing the namespace.

    Returns:
      An operation

    Raises:
      apitools.base.py.HttpError: if the request returns an HTTP error
    """
    # Namespace containing fields with updated value(s)
    namespace = self.messages.Namespace(
        name=util.NamespaceResourceName(project, name))
    # Fields to be updated (currently no fields, only update_time is changed)
    mask = ''
    req = self.messages.GkehubProjectsLocationsNamespacesPatchRequest(
        namespace=namespace,
        name=util.NamespaceResourceName(project, name),
        updateMask=mask)
    return self.client.projects_locations_namespaces.Patch(req)

  def ListNamespaces(self, project):
    """Lists namespaces in a project.

    Args:
      project: the project to list namespaces from.

    Returns:
      A ListNamespaceResponse (list of namespaces and next page token)

    Raises:
      apitools.base.py.HttpError: if the request returns an HTTP error
    """
    req = self.messages.GkehubProjectsLocationsNamespacesListRequest(
        pageToken='', parent=util.NamespaceParentName(project))
    return list_pager.YieldFromList(
        self.client.projects_locations_namespaces,
        req,
        field='namespaces',
        batch_size_attribute=None)
