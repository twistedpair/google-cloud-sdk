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
"""Cloud vmware Clusters client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.vmware import util


class ClustersClient(util.VmwareClientBase):
  """cloud vmware Clusters client."""

  def __init__(self):
    super(ClustersClient, self).__init__()
    self.service = self.client.projects_locations_privateClouds_clusters

  def Get(self, resource):
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsClustersGetRequest(
        name=resource.RelativeName())
    return self.service.Get(request)

  def Create(self,
             resource,
             node_type=None,
             node_count=None,
             node_custom_core_count=None):
    parent = resource.Parent().RelativeName()
    cluster_id = resource.Name()

    cluster = self.messages.Cluster(
        nodeCount=node_count, nodeTypeId=node_type)
    if node_custom_core_count is not None:
      cluster.nodeCustomCoreCount = node_custom_core_count
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsClustersCreateRequest(
        parent=parent,
        cluster=cluster,
        clusterId=cluster_id)

    return self.service.Create(request)

  def Delete(self, resource):
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsClustersDeleteRequest(
        name=resource.RelativeName())
    return self.service.Delete(request)

  def List(self,
           private_cloud_resource,
           filter_expression=None,
           limit=None,
           page_size=None,
           sort_by=None):
    private_cloud = private_cloud_resource.RelativeName()
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsClustersListRequest(
        parent=private_cloud, filter=filter_expression)
    if page_size:
      request.page_size = page_size
    return list_pager.YieldFromList(
        self.service,
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='clusters')

  def Update(self,
             resource,
             node_count=None):
    cluster = self.messages.Cluster(
        nodeCount=node_count)
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsClustersPatchRequest(
        name=resource.RelativeName(),
        cluster=cluster)
    return self.service.Patch(request)
