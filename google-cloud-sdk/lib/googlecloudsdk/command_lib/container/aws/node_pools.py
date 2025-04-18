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
"""Command utilities for aws node-pools commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkemulticloud import util as api_util
from googlecloudsdk.calliope import base

NODEPOOLS_FORMAT = """\
  table(
    name.basename(),
    version:label=NODE_VERSION,
    config.instanceType,
    autoscaling.minNodeCount.yesno(no='0'):label=MIN_NODES,
    autoscaling.maxNodeCount:label=MAX_NODES,
    state)"""


class NodePoolsClient(object):
  """Client for creating GKE node pools on AWS."""

  def __init__(self, client=None, messages=None, track=base.ReleaseTrack.GA):
    self.client = client or api_util.GetClientInstance(release_track=track)
    self.messages = messages or api_util.GetMessagesModule(release_track=track)
    self.service = self.client.projects_locations_awsClusters_awsNodePools
    self.track = track
    self.version = api_util.GetApiVersionForTrack(track).capitalize()

  def _AddAwsNodePool(self, req):
    msg = 'GoogleCloudGkemulticloud{}AwsNodePool'.format(self.version)
    attr = 'googleCloudGkemulticloud{}AwsNodePool'.format(self.version)
    np = getattr(self.messages, msg)()
    setattr(req, attr, np)
    return np

  def _AddAwsNodeConfig(self, nodepool):
    msg = 'GoogleCloudGkemulticloud{}AwsNodeConfig'.format(self.version)
    config = getattr(self.messages, msg)()
    nodepool.config = config
    return config

  def _AddAwsNodePoolAutoscaling(self, nodepool):
    msg = 'GoogleCloudGkemulticloud{}AwsNodePoolAutoscaling'.format(
        self.version)
    autoscaling = getattr(self.messages, msg)()
    nodepool.autoscaling = autoscaling
    return autoscaling

  def _AddMaxPodsConstraint(self, nodepool):
    msg = 'GoogleCloudGkemulticloud{}MaxPodsConstraint'.format(self.version)
    mpc = getattr(self.messages, msg)()
    nodepool.maxPodsConstraint = mpc
    return mpc

  def _AddAwsNodePoolRootVolume(self, config):
    msg = 'GoogleCloudGkemulticloud{}AwsVolumeTemplate'.format(self.version)
    v = getattr(self.messages, msg)()
    config.rootVolume = v
    return v

  def _AddAwsNodePoolSshConfig(self, config):
    msg = 'GoogleCloudGkemulticloud{}AwsSshConfig'.format(self.version)
    ssh_config = getattr(self.messages, msg)()
    config.sshConfig = ssh_config
    return ssh_config

  def _AddAwsProxyConfig(self, req):
    msg = 'GoogleCloudGkemulticloud{}AwsProxyConfig'.format(self.version)
    pc = getattr(self.messages, msg)()
    req.proxyConfig = pc
    return pc

  def _CreateAwsProxyConfig(self, secret_arn, secret_version_id):
    msg = 'GoogleCloudGkemulticloud{}AwsProxyConfig'.format(self.version)
    return getattr(self.messages, msg)(
        secretArn=secret_arn, secretVersion=secret_version_id)

  def _CreateAwsConfigEncryption(self, kms_key_arn):
    msg = 'GoogleCloudGkemulticloud{}AwsConfigEncryption'.format(self.version)
    return getattr(self.messages, msg)(kmsKeyArn=kms_key_arn)

  def _CreateAwsVolumeTemplate(self, size_gib, volume_type, iops, kms_key_arn):
    msg = 'GoogleCloudGkemulticloud{}AwsVolumeTemplate'.format(self.version)
    return getattr(self.messages, msg)(
        sizeGib=size_gib,
        volumeType=volume_type,
        iops=iops,
        kmsKeyArn=kms_key_arn)

  def _CreateAwsInstancePlacement(self, instance_placement_key):
    msg = 'GoogleCloudGkemulticloud{}AwsInstancePlacement'.format(self.version)
    return getattr(self.messages, msg)(tenancy=instance_placement_key)

  def Create(self, node_pool_ref, args):
    """Create an AWS node pool."""
    validate_only = getattr(args, 'validate_only', False)
    req = self.messages.GkemulticloudProjectsLocationsAwsClustersAwsNodePoolsCreateRequest(
        awsNodePoolId=node_pool_ref.awsNodePoolsId,
        parent=node_pool_ref.Parent().RelativeName(),
        validateOnly=validate_only)

    nodepool = self._AddAwsNodePool(req)
    nodepool.name = node_pool_ref.awsNodePoolsId
    nodepool.version = args.node_version
    nodepool.subnetId = args.subnet_id

    mpc = self._AddMaxPodsConstraint(nodepool)
    mpc.maxPodsPerNode = args.max_pods_per_node

    autoscaling = self._AddAwsNodePoolAutoscaling(nodepool)
    autoscaling.minNodeCount = args.min_nodes
    autoscaling.maxNodeCount = args.max_nodes

    config = self._AddAwsNodeConfig(nodepool)
    config.iamInstanceProfile = args.iam_instance_profile
    config.instanceType = args.instance_type
    if args.security_group_ids:
      config.securityGroupIds.extend(args.security_group_ids)
    if args.proxy_secret_arn and args.proxy_secret_version_id:
      config.proxyConfig = self._CreateAwsProxyConfig(
          args.proxy_secret_arn, args.proxy_secret_version_id)
    if args.config_encryption_kms_key_arn:
      config.configEncryption = self._CreateAwsConfigEncryption(
          args.config_encryption_kms_key_arn)
    if args.instance_placement:
      config.instancePlacement = self._CreateAwsInstancePlacement(
          args.instance_placement)
    root_volume = self._AddAwsNodePoolRootVolume(config)
    root_volume.sizeGib = args.root_volume_size
    root_volume.volumeType = args.root_volume_type
    root_volume.iops = args.root_volume_iops
    root_volume.kmsKeyArn = args.root_volume_kms_key_arn

    ssh_config = self._AddAwsNodePoolSshConfig(config)
    ssh_config.ec2KeyPair = args.ssh_ec2_key_pair

    config.taints.extend(args.node_taints)

    if args.tags:
      tag_type = type(config).TagsValue.AdditionalProperty
      config.tags = type(config).TagsValue(additionalProperties=[
          tag_type(key=k, value=v) for k, v in args.tags.items()
      ])

    if args.node_labels:
      label_type = type(config).LabelsValue.AdditionalProperty
      config.labels = type(config).LabelsValue(additionalProperties=[
          label_type(key=k, value=v) for k, v in args.node_labels.items()
      ])

    if args.image_type:
      config.imageType = args.image_type

    return self.service.Create(req)

  def Delete(self, node_pool_ref, args):
    """Delete an AWS node pool."""
    validate_only = getattr(args, 'validate_only', False)
    req = self.messages.GkemulticloudProjectsLocationsAwsClustersAwsNodePoolsDeleteRequest(
        name=node_pool_ref.RelativeName(), validateOnly=validate_only)

    return self.service.Delete(req)

  def Get(self, node_pool_ref):
    """Get an AWS node pool."""
    req = self.messages.GkemulticloudProjectsLocationsAwsClustersAwsNodePoolsGetRequest(
        name=node_pool_ref.RelativeName())
    return self.service.Get(req)

  def List(self, cluster_ref, args):
    """List AWS node pools."""
    for node_pool in list_pager.YieldFromList(
        service=self.service,
        request=self.messages
        .GkemulticloudProjectsLocationsAwsClustersAwsNodePoolsListRequest(
            parent=cluster_ref.RelativeName()),
        limit=args.limit,
        field='awsNodePools',
        batch_size_attribute='pageSize'):
      yield node_pool

  def Update(self, node_pool_ref, args):
    """Updates a node pool in an Anthos cluster on AWS.

    Args:
      node_pool_ref: gkemulticloud.GoogleCloudGkemulticloudV1AwsNodePool object.
      args: argparse.Namespace, Arguments parsed from the command.

    Returns:
      Response to the update request.
    """
    validate_only = getattr(args, 'validate_only', False)
    req = self.messages.GkemulticloudProjectsLocationsAwsClustersAwsNodePoolsPatchRequest(
        name=node_pool_ref.RelativeName(),
        validateOnly=validate_only)

    update_mask = []
    nodepool = self._AddAwsNodePool(req)
    if args.node_version:
      nodepool.version = args.node_version
      update_mask.append('version')

    autoscaling = self._AddAwsNodePoolAutoscaling(nodepool)
    if args.min_nodes is not None:
      autoscaling.minNodeCount = args.min_nodes
      update_mask.append('autoscaling.minNodeCount')
    if args.max_nodes is not None:
      autoscaling.maxNodeCount = args.max_nodes
      update_mask.append('autoscaling.maxNodeCount')

    config = self._AddAwsNodeConfig(nodepool)
    if args.clear_security_group_ids is not None:
      update_mask.append('config.security_group_ids')
    elif args.security_group_ids:
      config.securityGroupIds.extend(args.security_group_ids)
      update_mask.append('config.security_group_ids')

    if args.config_encryption_kms_key_arn:
      config.configEncryption = self._CreateAwsConfigEncryption(
          args.config_encryption_kms_key_arn)
      update_mask.append('config.config_encryption.kms_key_arn')
    config.rootVolume = self._CreateAwsVolumeTemplate(
        args.root_volume_size, args.root_volume_type, args.root_volume_iops,
        args.root_volume_kms_key_arn)
    if args.root_volume_size:
      update_mask.append('config.root_volume.size_gib')
    if args.root_volume_type:
      update_mask.append('config.root_volume.volume_type')
    # Check None explicitly because iops and kms_key_arn can take values that
    # evaluates to False e.g. 0, "".
    if args.root_volume_iops is not None:
      update_mask.append('config.root_volume.iops')
    if args.root_volume_kms_key_arn is not None:
      update_mask.append('config.root_volume.kms_key_arn')

    if args.clear_proxy_config is not None:
      update_mask.append('config.proxy_config')
    else:
      proxy_config = self._AddAwsProxyConfig(config)
      if args.proxy_secret_arn:
        proxy_config.secretArn = args.proxy_secret_arn
        update_mask.append('config.proxy_config.secret_arn')
      if args.proxy_secret_version_id:
        proxy_config.secretVersion = args.proxy_secret_version_id
        update_mask.append('config.proxy_config.secret_version')
    req.updateMask = ','.join(update_mask)

    return self.service.Patch(req)

  def HasNodePools(self, cluster_ref):
    """Checks if the cluster has a node pool.

    Args:
      cluster_ref: gkemulticloud.GoogleCloudGkemulticloudV1AwsCluster object.

    Returns:
      True if the cluster has a node pool. Otherwise, False.
    """
    req = self.messages.GkemulticloudProjectsLocationsAwsClustersAwsNodePoolsListRequest(
        parent=cluster_ref.RelativeName(),
        pageSize=1)
    res = self.service.List(req)
    if res.awsNodePools:
      return True
    return False
