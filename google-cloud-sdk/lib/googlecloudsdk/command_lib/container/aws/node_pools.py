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

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkemulticloud import util as api_util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log

NODEPOOLS_FORMAT = """\
  table(
    name.basename(),
    version:label=NODE_VERSION,
    config.instanceType,
    autoscaling.minNodeCount:label=MIN_NODES,
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

  def _CreateAwsProxyConfig(self, secret_arn, secret_version_id):
    msg = 'GoogleCloudGkemulticloud{}AwsProxyConfig'.format(self.version)
    return getattr(self.messages, msg)(
        secretArn=secret_arn, secretVersion=secret_version_id)

  def _CreateAwsConfigEncryption(self, kms_key_arn):
    msg = 'GoogleCloudGkemulticloud{}AwsConfigEncryption'.format(self.version)
    return getattr(self.messages, msg)(kmsKeyArn=kms_key_arn)

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
    try:
      for node_pool in list_pager.YieldFromList(
          service=self.service,
          request=self.messages
          .GkemulticloudProjectsLocationsAwsClustersAwsNodePoolsListRequest(
              parent=cluster_ref.RelativeName()),
          limit=args.limit,
          field='awsNodePools',
          batch_size_attribute='pageSize'):
        yield node_pool
    # TODO(b/203617640): Remove handling of this exception once API has gone GA.
    except apitools_exceptions.HttpNotFoundError as e:
      if 'Method not found' in e.content:
        log.warning(
            'This project may not have been added to the allow list for the Anthos Multi-Cloud API, please reach out to your GCP account team to resolve this'
        )
      raise

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

    req.updateMask = ','.join(update_mask)

    return self.service.Patch(req)
