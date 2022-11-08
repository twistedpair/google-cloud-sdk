
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
from googlecloudsdk.api_lib.container.gkeonprem import update_mask


class _BareMetalNodePoolsClient(client.ClientBase):
  """Base class for GKE OnPrem Bare Metal API clients."""

  def _node_pool_config(self, args):
    """Constructs proto message BareMetalNodePoolConfig."""
    kwargs = {
        'nodeConfigs': self._node_configs(args)
    }

    if any(kwargs.values()):
      return self._messages.BareMetalNodePoolConfig(**kwargs)

    return None

  def _node_configs(self, args):
    """Constructs proto message field node_configs."""
    node_configs = []
    node_config_flag_value = getattr(args, 'node_configs',
                                     None)
    if node_config_flag_value:
      for node_config in node_config_flag_value:
        node_configs.append(self._node_config(node_config))

    return node_configs

  def _node_config(self, node_config_args):
    """Constructs proto message BareMetalNodeConfig."""
    kwargs = {
        'nodeIp': node_config_args.get('node-ip', ''),
    }

    if any(kwargs.values()):
      return self._messages.BareMetalNodeConfig(**kwargs)

    return None

  def _bare_metal_node_pool(self, args):
    """Constructs proto message BareMetalNodePool."""
    kwargs = {
        'name': self._node_pool_name(args),
        'nodePoolConfig': self._node_pool_config(args),
    }

    return self._messages.BareMetalNodePool(**kwargs)


class NodePoolsClient(_BareMetalNodePoolsClient):
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

  def Create(self, args):
    """Creates a GKE On-Prem Bare Metal API node pool resource."""
    node_pool_ref = self._node_pool_ref(args)
    kwargs = {
        'parent': node_pool_ref.Parent().RelativeName(),
        'validateOnly': getattr(args, 'validate_only', False),
        'bareMetalNodePool': self._bare_metal_node_pool(args),
        'bareMetalNodePoolId': self._node_pool_id(args),
    }
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersBareMetalNodePoolsCreateRequest(
        **kwargs)
    return self._service.Create(req)

  def Update(self, args):
    """Updates a GKE On-Prem Bare Metal API node pool resource."""
    kwargs = {
        'allowMissing': getattr(args, 'allow_missing', False),
        'name': self._node_pool_name(args),
        'updateMask':
            update_mask.get_update_mask(
                args, update_mask.BARE_METAL_NODE_POOL_ARGS_TO_UPDATE_MASKS),
        'validateOnly': getattr(args, 'validate_only', False),
        'bareMetalNodePool': self._bare_metal_node_pool(args),
    }
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersBareMetalNodePoolsPatchRequest(
        **kwargs)
    return self._service.Patch(req)
