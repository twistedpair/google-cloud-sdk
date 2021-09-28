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
"""Cloud Bare Metal Solution client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis

_DEFAULT_API_VERSION = 'v2'
_GLOBAL_REGION = 'global'


class BmsClient(object):
  """Cloud Bare Metal Solution client."""

  def __init__(self, api_version=_DEFAULT_API_VERSION):
    self._client = apis.GetClientInstance('baremetalsolution', api_version)
    self._messages = apis.GetMessagesModule('baremetalsolution', api_version)
    self.service = self._client.projects_locations_instances
    self.locations_service = self._client.projects_locations
    self.operations_service = self.client.projects_locations_operations

  @property
  def client(self):
    return self._client

  @property
  def messages(self):
    return self._messages

  def Get(self, resource):
    request = self.messages.BaremetalsolutionProjectsLocationsInstancesGetRequest(
        name=resource.RelativeName())
    return self.service.Get(request)

  def AggregateYieldFromList(self,
                             service,
                             project_resource,
                             global_params=None,
                             limit=None,
                             method='List',
                             predicate=None):
    """Make a series of List requests, across locations in a project.

    Args:
      service: apitools_base.BaseApiService, A service with a .List() method.
      project_resource: str, The resource name of the project.
      global_params: protorpc.messages.Message, The global query parameters to
        provide when calling the given method.
      limit: int, The maximum number of records to yield. None if all available
        records should be yielded.
      method: str, The name of the method used to fetch resources.
      predicate: lambda, A function that returns true for items to be yielded.

    Yields:
      protorpc.message.Message, The resources listed by the service.

    """
    for location in self.ListLocations(project_resource):
      # TODO (b/198857865): Global region will be used when it is ready.
      location_name = location.name.split('/')[-1]
      if location_name == _GLOBAL_REGION:
        continue
      request = self.messages.BaremetalsolutionProjectsLocationsInstancesListRequest(
          parent=location.name, filter=None)
      try:
        response = getattr(service, method)(
            request, global_params=global_params)
      except Exception:
        # Continue to list entries from other locations.
        continue
      items = getattr(response, 'instances')
      if predicate:
        items = list(filter(predicate, items))
      for item in items:
        yield item
        if limit is None:
          continue
        limit -= 1
        if not limit:
          return

  def ListLocations(self,
                    project_resource,
                    filter_expression=None,
                    limit=None,
                    page_size=None):
    request = self.messages.BaremetalsolutionProjectsLocationsListRequest(
        name='projects/' + project_resource, filter=filter_expression)
    return list_pager.YieldFromList(
        self.locations_service,
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='locations')

  def List(self,
           location_resource,
           filter_expression=None,
           limit=None,
           page_size=None):
    location = location_resource.RelativeName()
    request = self.messages.BaremetalsolutionProjectsLocationsInstancesListRequest(
        parent=location, filter=filter_expression)
    return list_pager.YieldFromList(
        self.service,
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='instances')

  def AggregateList(self, project_resource, limit=None):
    return self.AggregateYieldFromList(
        self.service, project_resource, limit=limit)

  def IsClientNetwork(self, network):
    if network.type == self.messages.Network.TypeValueValuesEnum.CLIENT:
      return True
    return False

  def IsPrivateNetwork(self, network):
    if network.type == self.messages.Network.TypeValueValuesEnum.PRIVATE:
      return True
    return False
