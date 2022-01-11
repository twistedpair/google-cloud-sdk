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
"""Cloud vmware Privateclouds client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.vmware import util
from googlecloudsdk.command_lib.vmware import flags


class PrivateCloudsClient(util.VmwareClientBase):
  """cloud vmware privateclouds client."""

  def __init__(self):
    super(PrivateCloudsClient, self).__init__()
    self.service = self.client.projects_locations_privateClouds

  def Get(self, resource):
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsGetRequest(
        name=resource.RelativeName())

    response = self.service.Get(request)
    if response.vcenter is not None:
      response.vcenter.fdqn = None
    if response.hcx is not None:
      response.hcx.fdqn = None
    if response.nsx is not None:
      response.nsx.fdqn = None
    return response

  def Create(self,
             resource,
             labels=None,
             description=None,
             cluster_id=None,
             node_type=None,
             node_count=None,
             network_cidr=None,
             network=None,
             network_project=None,
             external_ip_access=None,
             node_custom_core_count=None):
    parent = resource.Parent().RelativeName()
    private_cloud_id = resource.Name()
    private_cloud = self.messages.PrivateCloud(description=description)
    flags.AddLabelsToMessage(labels, private_cloud)
    network_config = self.messages.NetworkConfig(
        managementCidr=network_cidr,
        network=network,
        externalIpAccess=external_ip_access,
    )
    if not network.startswith('project'):
      if not bool(network_project):
        network_project = resource.Parent().Parent().Name()
      network_config.network = 'projects/{}/global/networks/{}'.format(
          network_project, network)
    management_cluster = self.messages.ManagementCluster(
        clusterId=cluster_id, nodeCount=node_count,
        nodeTypeId=node_type, nodeCustomCoreCount=node_custom_core_count)
    private_cloud.managementCluster = management_cluster
    private_cloud.networkConfig = network_config
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsCreateRequest(
        parent=parent,
        privateCloudId=private_cloud_id,
        privateCloud=private_cloud)
    return self.service.Create(request)

  def Update(self,
             resource,
             labels=None,
             description=None,
             external_ip_access=None):
    private_cloud = self.Get(resource)
    update_mask = ['labels']
    if labels is not None:
      flags.AddLabelsToMessage(labels, private_cloud)
    if description is not None:
      private_cloud.description = description
      update_mask.append('description')
    if external_ip_access is not None:
      private_cloud.networkConfig.externalIpAccess = external_ip_access
      update_mask.append('network_config.external_ip_access')
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsPatchRequest(
        privateCloud=private_cloud,
        name=resource.RelativeName(),
        updateMask=','.join(update_mask))
    return self.service.Patch(request)

  def UnDelete(self, resource):
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsUndeleteRequest(
        name=resource.RelativeName())
    return self.service.Undelete(request)

  def Delete(self, resource, delay_hours=None):
    return self.service.Delete(
        self.messages.VmwareengineProjectsLocationsPrivateCloudsDeleteRequest(
            name=resource.RelativeName(), delayHours=delay_hours))

  def List(self,
           location_resource,
           filter_expression=None,
           limit=None,
           page_size=None,
           sort_by=None):
    location = location_resource.RelativeName()
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsListRequest(
        parent=location, filter=filter_expression)
    if page_size:
      request.page_size = page_size
    return list_pager.YieldFromList(
        self.service,
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='privateClouds')

  def GetNsxCredentials(self, resource):
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsShowNsxCredentialsRequest(
        privateCloud=resource.RelativeName())
    return self.service.ShowNsxCredentials(request)

  def ResetNsxCredentials(self, resource):
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsResetNsxCredentialsRequest(
        privateCloud=resource.RelativeName())
    return self.service.ResetNsxCredentials(request)

  def GetVcenterCredentials(self, resource):
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsShowVcenterCredentialsRequest(
        privateCloud=resource.RelativeName())
    return self.service.ShowVcenterCredentials(request)

  def ResetVcenterCredentials(self, resource):
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsResetVcenterCredentialsRequest(
        privateCloud=resource.RelativeName())
    return self.service.ResetVcenterCredentials(request)
