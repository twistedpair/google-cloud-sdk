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

  def Create(self, resource, nodes_configs, autoscaling_settings=None):
    parent = resource.Parent().RelativeName()
    cluster_id = resource.Name()

    node_type_configs = util.ConstructNodeParameterConfigMessage(
        self.messages.Cluster.NodeTypeConfigsValue,
        self.messages.NodeTypeConfig, nodes_configs)
    cluster = self.messages.Cluster(nodeTypeConfigs=node_type_configs)
    cluster.autoscalingSettings = util.ConstructAutoscalingSettingsMessage(
        self.messages.AutoscalingSettings,
        self.messages.AutoscalingPolicy,
        self.messages.Thresholds,
        autoscaling_settings,
    )
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsClustersCreateRequest(
        parent=parent,
        cluster=cluster,
        clusterId=cluster_id)

    return self.service.Create(request)

  def Delete(self, resource):
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsClustersDeleteRequest(
        name=resource.RelativeName())
    return self.service.Delete(request)

  def List(self, private_cloud_resource):
    private_cloud = private_cloud_resource.RelativeName()
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsClustersListRequest(
        parent=private_cloud
    )
    return list_pager.YieldFromList(
        self.service,
        request,
        batch_size_attribute='pageSize',
        field='clusters')

  def Update(self, resource, nodes_configs, autoscaling_settings):
    node_type_configs, node_type_configs_update_mask = None, []
    if nodes_configs is not None:
      node_type_configs = util.ConstructNodeParameterConfigMessage(
          self.messages.Cluster.NodeTypeConfigsValue,
          self.messages.NodeTypeConfig,
          nodes_configs,
      )
      node_type_configs_update_mask = ['node_type_configs.*.node_count']

    if autoscaling_settings is not None:
      autoscaling_settings_update_mask = ['autoscaling_settings']
    else:
      autoscaling_settings_update_mask = []

    # If a customer removes the last policy from the settings, the settings do
    # not provide any additional value. So, in this case, we are removing the
    # entire setting.
    if (
        autoscaling_settings is not None
        and autoscaling_settings.autoscaling_policies
    ):
      autoscaling_settings_message = util.ConstructAutoscalingSettingsMessage(
          self.messages.AutoscalingSettings,
          self.messages.AutoscalingPolicy,
          self.messages.Thresholds,
          autoscaling_settings,
      )
    else:
      autoscaling_settings_message = None

    cluster = self.messages.Cluster(
        nodeTypeConfigs=node_type_configs,
        autoscalingSettings=autoscaling_settings_message,
    )
    update_mask = ','.join(
        node_type_configs_update_mask + autoscaling_settings_update_mask
    )
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsClustersPatchRequest(
        name=resource.RelativeName(), cluster=cluster, updateMask=update_mask
    )
    return self.service.Patch(request)

  def MountDatastore(
      self,
      cluster_ref,
      datastore,
      subnet,
      mtu,
      connection_count,
      access_mode,
      nfs_version,
      ignore_colocation,
  ):
    """Mounts a datastore to a cluster."""
    datastore_network = self.messages.DatastoreNetwork(
        subnet=cluster_ref.Parent().RelativeName() + '/subnets/' + subnet
    )
    if mtu is not None:
      datastore_network.mtu = mtu
    if connection_count is not None:
      datastore_network.connectionCount = connection_count

    datastore_mount_config = self.messages.DatastoreMountConfig(
        datastore=datastore,
        datastoreNetwork=datastore_network,
    )
    if access_mode:
      datastore_mount_config.accessMode = (
          self.messages.DatastoreMountConfig.AccessModeValueValuesEnum(
              access_mode
          )
      )
    if nfs_version:
      if nfs_version == 'NFS_V4':
        nfs_version_enum_str = 'NFS_V41'
      else:
        nfs_version_enum_str = nfs_version
      datastore_mount_config.nfsVersion = (
          self.messages.DatastoreMountConfig.NfsVersionValueValuesEnum(
              nfs_version_enum_str
          )
      )
    mount_datastore_request = self.messages.MountDatastoreRequest(
        datastoreMountConfig=datastore_mount_config,
        ignoreColocation=ignore_colocation,
    )
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsClustersMountDatastoreRequest(
        name=cluster_ref.RelativeName(),
        mountDatastoreRequest=mount_datastore_request,
    )
    return self.service.MountDatastore(request)

  def UnmountDatastore(self, cluster_ref, datastore):
    """Unmounts a datastore from a cluster."""
    unmount_datastore_request = self.messages.UnmountDatastoreRequest(
        datastore=datastore
    )
    request = self.messages.VmwareengineProjectsLocationsPrivateCloudsClustersUnmountDatastoreRequest(
        name=cluster_ref.RelativeName(),
        unmountDatastoreRequest=unmount_datastore_request,
    )
    return self.service.UnmountDatastore(request)
