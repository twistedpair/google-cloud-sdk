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

"""Client for interaction with Gateway CRUD on API Gateway API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager

from googlecloudsdk.api_lib.api_gateway import base
from googlecloudsdk.command_lib.api_gateway import common_flags


class GatewayClient(base.BaseClient):
  """Client for gateway objects on Cloud API Gateway API."""

  def Create(self, gateway_ref, api_config, display_name=None, labels=None):
    """Creates a new gateway object.

    Args:
      gateway_ref: Resource, a resource reference for the gateway
      api_config: Resource, a resource reference for the gateway
      display_name: Optional display name
      labels: Optional cloud labels

    Returns:
      Long running operation.
    """
    labels = common_flags.ProcessLabelsFlag(
        labels,
        self.messages.ApigatewayGateway.LabelsValue)

    gateway = self.messages.ApigatewayGateway(
        name=gateway_ref.RelativeName(),
        labels=labels,
        apiConfig=api_config.RelativeName(),
        displayName=display_name,
        )

    req = self.messages.ApigatewayProjectsLocationsGatewaysCreateRequest(
        parent=gateway_ref.Parent().RelativeName(),
        gatewayId=gateway_ref.Name(),
        apigatewayGateway=gateway,
        )
    resp = self.client.projects_locations_gateways.Create(req)

    return resp

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
    req = self.messages.ApigatewayProjectsLocationsGatewaysListRequest(
        filter=filters,
        orderBy=sort_by,
        parent=parent_name
        )

    return list_pager.YieldFromList(
        self.client.projects_locations_gateways,
        req,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='gateways')

  def Delete(self, gateway_name):
    """Deletes a given gateway object given a resource name.

    Args:
      gateway_name: Resource name of the gateway

    Returns:
      Long running operation.
    """
    req = self.messages.ApigatewayProjectsLocationsGatewaysDeleteRequest(
        name=gateway_name)

    return self.client.projects_locations_gateways.Delete(req)

  def Update(self, gateway, update_mask=None):
    """Updates a gateway object.

    Args:
      gateway: ApigatewayGateway message that should be pushed for update,
      update_mask: Optional, fields to overwrite, if left blank all will be

    Returns:
      Long running operation response object.
    """

    req = self.messages.ApigatewayProjectsLocationsGatewaysPatchRequest(
        name=gateway.name,
        apigatewayGateway=gateway,
        updateMask=update_mask
        )

    return self.client.projects_locations_gateways.Patch(req)

  def Get(self, gateway_ref):
    """Gets a gateway object.

    Args:
      gateway_ref: Resource, a resource reference for the gateway

    Returns:
      A Gateway object
    """

    req = self.messages.ApigatewayProjectsLocationsGatewaysGetRequest(
        name=gateway_ref.RelativeName()
        )

    return self.client.projects_locations_gateways.Get(req)
