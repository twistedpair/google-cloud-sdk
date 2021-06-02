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
from googlecloudsdk.api_lib.container.aws import util as api_util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.container.gkemulticloud import flags

NODEPOOLS_FORMAT = """\
  table(
    name.basename(),
    instanceType:label=MACHINE_TYPE,
    rootVolume.sizeGib:label=DISK_SIZE_GB,
    version:label=NODE_VERSION,
    state:label=STATUS)"""


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

  def _AddAwsNodePoolAutoscaling(self, np):
    msg = 'GoogleCloudGkemulticloud{}AwsNodePoolAutoscaling'.format(
        self.version)
    autoscaling = getattr(self.messages, msg)()
    np.autoscaling = autoscaling
    return autoscaling

  def _AddAwsNodePoolRootVolume(self, np):
    msg = 'GoogleCloudGkemulticloud{}AwsVolumeTemplate'.format(self.version)
    v = getattr(self.messages, msg)()
    np.rootVolume = v
    return v

  def _AddAwsNodePoolSshConfig(self, np):
    msg = 'GoogleCloudGkemulticloud{}AwsSshConfig'.format(self.version)
    ssh_config = getattr(self.messages, msg)()
    np.sshConfig = ssh_config
    return ssh_config

  def Create(self, node_pool_ref, args):
    """Create an AWS node pool."""
    validate_only = getattr(args, 'validate_only', False)
    req = self.messages.GkemulticloudProjectsLocationsAwsClustersAwsNodePoolsCreateRequest(
        awsNodePoolId=node_pool_ref.awsNodePoolsId,
        parent=node_pool_ref.Parent().RelativeName(),
        validateOnly=validate_only)

    np = self._AddAwsNodePool(req)
    np.name = node_pool_ref.awsNodePoolsId
    np.version = args.node_version
    np.subnetId = args.subnet_id[0]
    np.instanceType = args.instance_type
    np.iamInstanceProfile = args.iam_instance_profile
    np.maxPodsPerNode = args.max_pods_per_node

    flags.CheckNumberOfNodesAndAutoscaling(args)
    if args.enable_autoscaling:
      autoscaling = self._AddAwsNodePoolAutoscaling(np)
      autoscaling.minNodeCount = args.min_nodes
      autoscaling.maxNodeCount = args.max_nodes
    else:
      autoscaling = self._AddAwsNodePoolAutoscaling(np)
      autoscaling.minNodeCount = args.num_nodes
      autoscaling.maxNodeCount = args.num_nodes

    root_volume = self._AddAwsNodePoolRootVolume(np)
    root_volume.sizeGib = args.root_volume_size

    ssh_config = self._AddAwsNodePoolSshConfig(np)
    ssh_config.ec2KeyPair = args.key_pair_name

    if args.tags:
      tag_type = type(np).TagsValue.AdditionalProperty
      np.tags = type(np).TagsValue(additionalProperties=[
          tag_type(key=k, value=v) for k, v in args.tags.items()
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
    for node_pool in list_pager.YieldFromList(
        service=self.service,
        request=self.messages
        .GkemulticloudProjectsLocationsAwsClustersAwsNodePoolsListRequest(
            parent=cluster_ref.RelativeName()),
        limit=args.limit,
        field='awsNodePools',
        batch_size_attribute='pageSize'):
      yield node_pool
