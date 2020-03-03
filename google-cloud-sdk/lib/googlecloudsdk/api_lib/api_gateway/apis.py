# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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

"""Client for interaction with Api CRUD on API Gateway API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import list_pager

from googlecloudsdk.api_lib.api_gateway import base


class ApiClient(base.BaseClient):
  """Client for Api objects on Cloud API Gateway API."""

  def Get(self, api_ref):
    """Gets an Api object.

    Args:
      api_ref: Resource, a resource reference for the api

    Raises:
      HttpNotFoundError: The requested object could not be found.

    Returns:
      Api object
    """
    req = self.messages.ApigatewayProjectsLocationsApisGetRequest(
        name=api_ref.RelativeName())

    return self.client.projects_locations_apis.Get(req)

  def DoesExist(self, api_ref):
    """Checks if an Api object exists.

    Args:
      api_ref: Resource, a resource reference for the api

    Returns:
      Boolean, indicating whether or not exists
    """
    try:
      self.Get(api_ref)
    except apitools_exceptions.HttpNotFoundError:
      return False

    return True

  def Create(self, api_ref, managed_service, labels=None, display_name=None):
    """Creates a new Api object.

    Args:
      api_ref: Resource, a resource reference for the api
      managed_service: String, reference name for OP service
      labels: Optional cloud labels
      display_name: Optional display name

    Returns:
      Long running operation response object.
    """
    api_controller = self.messages.ApigatewayApiApiController(
        managedService=managed_service)
    api = self.messages.ApigatewayApi(
        name=api_ref.RelativeName(),
        apiController=api_controller,
        labels=labels,
        displayName=display_name)

    req = self.messages.ApigatewayProjectsLocationsApisCreateRequest(
        apiId=api_ref.Name(),
        apigatewayApi=api,
        parent=api_ref.Parent().RelativeName())

    return self.client.projects_locations_apis.Create(req)

  def List(self, parent_name, filters=None, limit=None, page_size=None,
           sort_by=None):
    """Lists the gateway objects under a given parent.

    Args:
      parent_name: Resource name of the parent to list under
      filters: Filters to be applied to results (optional)
      limit: Limit to the number of results per page (optional)
      page_size: the number of results per page (optional)
      sort_by: Instructions about how to sort the results (optional)

    Returns:
      List Pager
    """
    req = self.messages.ApigatewayProjectsLocationsApisListRequest(
        filter=filters,
        orderBy=sort_by,
        parent=parent_name)

    return list_pager.YieldFromList(
        self.client.projects_locations_apis,
        req,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='apis')
