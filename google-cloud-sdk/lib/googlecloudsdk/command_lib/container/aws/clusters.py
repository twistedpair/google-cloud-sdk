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
"""Command utilities for clusters commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkemulticloud import util as api_util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties

CLUSTERS_FORMAT = """\
  table(
    name.basename(),
    awsRegion,
    controlPlane.version:label=CONTROL_PLANE_VERSION,
    controlPlane.instanceType,
    state)"""


class Client(object):
  """Client for managing GKE clusters on AWS."""

  def __init__(self, client=None, messages=None, track=base.ReleaseTrack.GA):
    self.client = client or api_util.GetClientInstance(release_track=track)
    self.messages = messages or api_util.GetMessagesModule(release_track=track)
    self.service = self.client.projects_locations_awsClusters
    self.track = track
    self.version = api_util.GetApiVersionForTrack(track).capitalize()

  def _AddAwsCluster(self, req):
    msg = 'GoogleCloudGkemulticloud{}AwsCluster'.format(self.version)
    attr = 'googleCloudGkemulticloud{}AwsCluster'.format(self.version)
    cluster = getattr(self.messages, msg)()
    setattr(req, attr, cluster)
    return cluster

  def _AddAwsNetworking(self, req):
    msg = 'GoogleCloudGkemulticloud{}AwsClusterNetworking'.format(self.version)
    net = getattr(self.messages, msg)()
    req.networking = net
    return net

  def _AddAwsControlPlane(self, req):
    msg = 'GoogleCloudGkemulticloud{}AwsControlPlane'.format(self.version)
    cp = getattr(self.messages, msg)()
    req.controlPlane = cp
    return cp

  def _AddAwsAuthorization(self, req):
    msg = 'GoogleCloudGkemulticloud{}AwsAuthorization'.format(self.version)
    a = getattr(self.messages, msg)()
    req.authorization = a
    return a

  def _CreateAwsClusterUser(self, username):
    msg = 'GoogleCloudGkemulticloud{}AwsClusterUser'.format(self.version)
    return getattr(self.messages, msg)(username=username)

  def _CreateAwsVolumeTemplate(self, size_gib, volume_type, iops, kms_key_arn):
    msg = 'GoogleCloudGkemulticloud{}AwsVolumeTemplate'.format(self.version)
    return getattr(self.messages, msg)(
        sizeGib=size_gib,
        volumeType=volume_type,
        iops=iops,
        kmsKeyArn=kms_key_arn)

  def _CreateAwsDatabaseEncryption(self, database_encryption_key):
    msg = 'GoogleCloudGkemulticloud{}AwsDatabaseEncryption'.format(self.version)
    return getattr(self.messages, msg)(kmsKeyArn=database_encryption_key)

  def _CreateAwsServicesAuthentication(self, role_arn, role_session_name):
    msg = 'GoogleCloudGkemulticloud{}AwsServicesAuthentication'.format(
        self.version)
    return getattr(self.messages, msg)(
        roleArn=role_arn, roleSessionName=role_session_name)

  def _CreateAwsSshConfig(self, key_pair_name):
    msg = 'GoogleCloudGkemulticloud{}AwsSshConfig'.format(self.version)
    return getattr(self.messages, msg)(ec2KeyPair=key_pair_name)

  def Create(self, cluster_ref, args):
    """Create an AWS cluster."""
    validate_only = getattr(args, 'validate_only', False)
    req = self.messages.GkemulticloudProjectsLocationsAwsClustersCreateRequest(
        awsClusterId=cluster_ref.awsClustersId,
        parent=cluster_ref.Parent().RelativeName(),
        validateOnly=validate_only)

    c = self._AddAwsCluster(req)
    c.name = cluster_ref.awsClustersId
    c.awsRegion = args.aws_region

    cp = self._AddAwsControlPlane(c)
    cp.subnetIds.extend(args.subnet_ids)
    cp.iamInstanceProfile = args.iam_instance_profile
    cp.version = args.cluster_version
    cp.instanceType = args.instance_type
    cp.mainVolume = self._CreateAwsVolumeTemplate(args.main_volume_size,
                                                  args.main_volume_type,
                                                  args.main_volume_iops,
                                                  args.main_volume_kms_key_arn)
    cp.rootVolume = self._CreateAwsVolumeTemplate(args.root_volume_size,
                                                  args.root_volume_type,
                                                  args.root_volume_iops,
                                                  args.root_volume_kms_key_arn)
    cp.databaseEncryption = self._CreateAwsDatabaseEncryption(
        args.database_encryption_kms_key_arn)
    cp.awsServicesAuthentication = self._CreateAwsServicesAuthentication(
        args.role_arn, args.role_session_name)
    cp.sshConfig = self._CreateAwsSshConfig(args.ssh_ec2_key_pair)
    if args.security_group_ids:
      cp.securityGroupIds.extend(args.security_group_ids)

    net = self._AddAwsNetworking(c)
    net.vpcId = args.vpc_id
    net.podAddressCidrBlocks.append(args.pod_address_cidr_blocks)
    net.serviceAddressCidrBlocks.append(args.service_address_cidr_blocks)
    net.serviceLoadBalancerSubnetIds.extend(
        args.service_load_balancer_subnet_ids)

    if args.tags:
      tag_type = type(cp).TagsValue.AdditionalProperty
      cp.tags = type(cp).TagsValue(additionalProperties=[
          tag_type(key=k, value=v) for k, v in args.tags.items()
      ])

    a = self._AddAwsAuthorization(c)
    username = properties.VALUES.core.account.Get()
    a.adminUsers.append(self._CreateAwsClusterUser(username))

    return self.service.Create(req)

  def Delete(self, cluster_ref, args):
    """Delete an AWS cluster."""
    validate_only = getattr(args, 'validate_only', False)
    req = self.messages.GkemulticloudProjectsLocationsAwsClustersDeleteRequest(
        name=cluster_ref.RelativeName(), validateOnly=validate_only)

    return self.service.Delete(req)

  def Get(self, cluster_ref):
    """Get an AWS cluster."""
    req = self.messages.GkemulticloudProjectsLocationsAwsClustersGetRequest(
        name=cluster_ref.RelativeName())
    return self.service.Get(req)

  def GenerateAccessToken(self, cluster_ref):
    """Get an access token for an AWS cluster."""
    req = self.messages.GkemulticloudProjectsLocationsAwsClustersGenerateAwsAccessTokenRequest(
        awsCluster=cluster_ref.RelativeName())
    return self.service.GenerateAwsAccessToken(req)

  def GetKubeconfig(self, cluster_ref):
    """Get kubeconfig of an AWS cluster."""
    req = self.messages.GkemulticloudProjectsLocationsAwsClustersGetAwsClusterAdminKubeconfigRequest(
        awsCluster=cluster_ref.RelativeName())
    return self.service.GetAwsClusterAdminKubeconfig(req)

  def List(self, region_ref):
    """List AWS clusters."""
    req = self.messages.GkemulticloudProjectsLocationsAwsClustersListRequest(
        parent=region_ref.RelativeName())
    for cluster in list_pager.YieldFromList(
        service=self.service,
        request=req,
        field='awsClusters',
        batch_size_attribute='pageSize'):
      yield cluster
