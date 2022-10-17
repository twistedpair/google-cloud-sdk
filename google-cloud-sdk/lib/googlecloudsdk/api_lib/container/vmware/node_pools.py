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
"""Utilities for node pool resources in Anthos clusters on VMware."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.vmware import client
from googlecloudsdk.api_lib.container.vmware import update_mask
from googlecloudsdk.command_lib.container.vmware import flags


class NodePoolsClient(client.ClientBase):
  """Client for node pools in Anthos clusters on VMware API."""

  def __init__(self, **kwargs):
    super(NodePoolsClient, self).__init__(**kwargs)
    self._service = self._client.projects_locations_vmwareClusters_vmwareNodePools

  def List(self, args):
    """Lists Node Pools in the Anthos clusters on VMware API."""
    list_req = self._messages.GkeonpremProjectsLocationsVmwareClustersVmwareNodePoolsListRequest(
        parent=self._user_cluster_name(args))
    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='vmwareNodePools',
        batch_size=flags.Get(args, 'page_size'),
        limit=flags.Get(args, 'limit'),
        batch_size_attribute='pageSize',
    )

  def Delete(self, args):
    """Deletes a gkeonprem node pool API resource."""
    kwargs = {
        'allowMissing': flags.Get(args, 'allow_missing'),
        'etag': flags.Get(args, 'etag'),
        'name': self._node_pool_name(args),
        'validateOnly': flags.Get(args, 'validate_only'),
    }
    req = self._messages.GkeonpremProjectsLocationsVmwareClustersVmwareNodePoolsDeleteRequest(
        **kwargs)
    return self._service.Delete(req)

  def Create(self, args):
    """Creates a gkeonprem node pool API resource."""
    node_pool_ref = self._node_pool_ref(args)
    kwargs = {
        'parent': node_pool_ref.Parent().RelativeName(),
        'validateOnly': flags.Get(args, 'validate_only'),
        'vmwareNodePool': self._vmware_node_pool(args),
        'vmwareNodePoolId': self._node_pool_id(args),
    }
    req = self._messages.GkeonpremProjectsLocationsVmwareClustersVmwareNodePoolsCreateRequest(
        **kwargs)
    return self._service.Create(req)

  def Update(self, args):
    """Updates a gkeonprem node pool API resource."""
    kwargs = {
        'allowMissing':
            flags.Get(args, 'allow_missing'),
        'name':
            self._node_pool_name(args),
        'updateMask':
            update_mask.get_update_mask(
                args, update_mask.VMWARE_NODE_POOL_ARGS_TO_UPDATE_MASKS),
        'validateOnly':
            flags.Get(args, 'validate_only'),
        'vmwareNodePool':
            self._vmware_node_pool(args),
    }
    req = self._messages.GkeonpremProjectsLocationsVmwareClustersVmwareNodePoolsPatchRequest(
        **kwargs)
    return self._service.Patch(req)

  def _vmware_node_pool(self, args):
    """Constructs proto message VmwareNodePool."""
    kwargs = {
        'name': self._node_pool_name(args),
        'displayName': flags.Get(args, 'display_name'),
        'config': self._vmware_node_config(args),
        'nodePoolAutoscaling': self._vmware_node_pool_autoscaling_config(args),
    }
    return self._messages.VmwareNodePool(**kwargs)

  def _vmware_node_config(self, args):
    """Constructs proto message VmwareNodeConfig."""
    kwargs = {
        'enableLoadBalancer': flags.Get(args, 'enable_load_balancer'),
        'imageType': flags.Get(args, 'image_type'),
        'replicas': flags.Get(args, 'replicas'),
    }
    if any(kwargs.values()):
      return self._messages.VmwareNodeConfig(**kwargs)
    return None

  def _vmware_node_pool_autoscaling_config(self, args):
    """Constructs proto message VmwareNodePoolAutoscalingConfig."""
    kwargs = {
        'minReplicas': flags.Get(args, 'min_replicas'),
        'maxReplicas': flags.Get(args, 'max_replicas'),
    }
    if any(kwargs.values()):
      return self._messages.VmwareNodePoolAutoscalingConfig(**kwargs)
    return None
