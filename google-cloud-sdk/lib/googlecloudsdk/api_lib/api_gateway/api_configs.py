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

"""Client for interaction with Api Config CRUD on API Gateway API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager

from googlecloudsdk.api_lib.api_gateway import base
from googlecloudsdk.command_lib.api_gateway import common_flags


class ApiConfigClient(base.BaseClient):
  """Client for Api Config objects on Cloud API Gateway API."""

  def Get(self, api_config_ref):
    """Gets an Api Config object.

    Args:
      api_config_ref: Resource, a resource reference for the api

    Returns:
      Api Object
    """
    req = self.messages.ApigatewayProjectsLocationsApisConfigsGetRequest(
        name=api_config_ref.RelativeName())

    return self.client.projects_locations_apis_configs.Get(req)

  def Create(self, api_config_ref, rollout_id, display_name=None, labels=None,
             backend_auth=None):
    """Creates an Api Config object.

    Args:
      api_config_ref: Resource, a resource reference for the api
      rollout_id: Id of the service rollout
      display_name: Optional display name
      labels: Optional cloud labels
      backend_auth: Optional field to set the service account for backend auth

    Returns:
      Long running operation
    """
    labels = common_flags.ProcessLabelsFlag(
        labels,
        self.messages.ApigatewayApiConfig.LabelsValue)

    service_rollout = self.messages.ApigatewayApiConfigManagedServiceRollout(
        rolloutId=rollout_id)
    backend_config = self.messages.ApigatewayBackendConfig(
        googleServiceAccount=backend_auth)
    gateway_config = self.messages.ApigatewayGatewayConfig(
        backendConfig=backend_config)
    api_config = self.messages.ApigatewayApiConfig(
        name=api_config_ref.RelativeName(),
        serviceRollout=service_rollout,
        displayName=display_name,
        labels=labels,
        gatewayConfig=gateway_config)

    req = self.messages.ApigatewayProjectsLocationsApisConfigsCreateRequest(
        apiConfigId=api_config_ref.Name(),
        apigatewayApiConfig=api_config,
        parent=api_config_ref.Parent().RelativeName())

    return self.client.projects_locations_apis_configs.Create(req)

  def Delete(self, api_config_ref):
    """Deletes an API Config object.

    Args:
      api_config_ref: Resource, a reference for the API Config

    Returns:
      Long running operation.
    """

    req = self.messages.ApigatewayProjectsLocationsApisConfigsDeleteRequest(
        name=api_config_ref.RelativeName())

    return self.client.projects_locations_apis_configs.Delete(req)

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
    req = self.messages.ApigatewayProjectsLocationsApisConfigsListRequest(
        filter=filters,
        orderBy=sort_by,
        parent=parent_name
        )

    return list_pager.YieldFromList(
        self.client.projects_locations_apis_configs,
        req,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='apiConfigs')
