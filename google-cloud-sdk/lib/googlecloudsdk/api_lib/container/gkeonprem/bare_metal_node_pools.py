
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
"""Utilities for node pool resources in Anthos clusters on bare metal."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkeonprem import client


# pylint: disable=protected-access
class NodePoolsClient(client.ClientBase):
  """Client for node pools in Anthos clusters on bare metal API."""

  def __init__(self, **kwargs):
    super(NodePoolsClient, self).__init__(**kwargs)
    self._service = self._client.projects_locations_bareMetalClusters_bareMetalNodePools

  def List(self, location_ref, limit=None, page_size=None):
    """Lists Node Pools in the Anthos clusters on bare metal API."""
    list_req = self._messages.GkeonpremProjectsLocationsBareMetalClustersBareMetalNodePoolsListRequest(
        parent=location_ref.RelativeName())

    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='bareMetalNodePools',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize',
    )

  def Describe(self, resource_ref):
    """Gets a GKE On-Prem Bare Metal API node pool resource."""
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersBareMetalNodePoolsGetRequest(
        name=resource_ref.RelativeName())

    return self._service.Get(req)

  def Delete(self, args):
    """Deletes a GKE On-Prem Bare Metal API node pool resource."""
    kwargs = {
        'name': self._node_pool_name(args),
        'allowMissing': getattr(args, 'allow_missing', False),
        'validateOnly': getattr(args, 'validate_only', False),
    }
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersBareMetalNodePoolsDeleteRequest(
        **kwargs)

    return self._service.Delete(req)
