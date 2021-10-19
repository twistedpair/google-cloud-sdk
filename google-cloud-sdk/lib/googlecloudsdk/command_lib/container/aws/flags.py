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
"""Helpers for flags in commands working with GKE Multi-cloud for AWS."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.container.gkemulticloud import util as api_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.util.apis import arg_utils


def AddAwsRegion(parser):
  parser.add_argument(
      '--aws-region', required=True, help='AWS region to deploy the cluster.')


def AddVpcId(parser):
  parser.add_argument(
      '--vpc-id', required=True, help='VPC associated with the cluster.')


def AddServiceLoadBalancerSubnetIDs(parser):
  parser.add_argument(
      '--service-load-balancer-subnet-ids',
      required=True,
      type=arg_parsers.ArgList(),
      metavar='SUBNET_ID',
      help='Subnets for the services of type Load Balancer.')


def AddIamInstanceProfile(parser):
  parser.add_argument(
      '--iam-instance-profile',
      required=True,
      help='IAM instance profile associated with the cluster.')


def AddInstanceType(parser):
  parser.add_argument('--instance-type', help='AWS EC2 instance type.')


def AddSshEC2KeyPair(parser):
  parser.add_argument(
      '--ssh-ec2-key-pair',
      help='Name of the EC2 key pair to log in into control plane nodes.')


def AddRoleArn(parser):
  parser.add_argument(
      '--role-arn',
      required=True,
      help=('Amazon Resource Name (ARN) of the IAM role to assume when '
            'managing AWS resources.'))


def AddRoleSessionName(parser):
  parser.add_argument(
      '--role-session-name', help='Identifier for the assumed role session.')


def AddSecurityGroupIds(parser, noun):
  parser.add_argument(
      '--security-group-ids',
      type=arg_parsers.ArgList(),
      metavar='SECURITY_GROUP_ID',
      help='IDs of additional security groups to add to {}.'.format(noun))


def _VolumeTypeEnumMapper(prefix):
  return arg_utils.ChoiceEnumMapper(
      '--{}-volume-type'.format(prefix),
      api_util.GetMessagesModule().GoogleCloudGkemulticloudV1AwsVolumeTemplate
      .VolumeTypeValueValuesEnum,
      include_filter=lambda volume_type: 'UNSPECIFIED' not in volume_type,
      help_str='Type of the {} volume.'.format(prefix))


def AddRootVolumeType(parser):
  _VolumeTypeEnumMapper('root').choice_arg.AddToParser(parser)


def AddMainVolumeType(parser):
  _VolumeTypeEnumMapper('main').choice_arg.AddToParser(parser)


def GetRootVolumeType(args):
  if args.root_volume_type is not None:
    return _VolumeTypeEnumMapper('root').GetEnumForChoice(args.root_volume_type)


def GetMainVolumeType(args):
  if args.main_volume_type is not None:
    return _VolumeTypeEnumMapper('main').GetEnumForChoice(args.main_volume_type)


def _AddVolumeIops(parser, prefix):
  parser.add_argument(
      '--{}-volume-iops'.format(prefix),
      type=int,
      help=('Number of I/O operations per second (IOPS) to provision '
            'for the {} volume.'.format(prefix)))


def AddRootVolumeIops(parser):
  _AddVolumeIops(parser, 'root')


def AddMainVolumeIops(parser):
  _AddVolumeIops(parser, 'main')


def _AddKmsKeyArn(parser, prefix, target, required=False, hidden=False):
  parser.add_argument(
      '--{}-kms-key-arn'.format(prefix),
      required=required,
      hidden=hidden,
      help='Amazon Resource Name (ARN) of the AWS KMS key to encrypt the {}.'
      .format(target))


def AddRootVolumeKmsKeyArn(parser):
  _AddKmsKeyArn(parser, 'root-volume', 'root control plane volume')


def AddMainVolumeKmsKeyArn(parser):
  _AddKmsKeyArn(parser, 'main-volume', 'main volume')


def AddDatabaseEncryptionKmsKeyArn(parser):
  _AddKmsKeyArn(parser, 'database-encryption', 'cluster secrets', required=True)


def AddConfigEncryptionKmsKeyArn(parser):
  # TODO(b/202339655): Require config encryption after dropping 1.20 and lower.
  _AddKmsKeyArn(parser, 'config-encryption', 'user data', hidden=True)


def AddProxyConfig(parser):
  """Add proxy configuration flags.

  Args:
    parser: The argparse.parser to add the arguments to.
  """

  group = parser.add_argument_group('Proxy config')
  group.add_argument(
      '--proxy-secret-arn',
      required=True,
      help=('ARN of the AWS Secrets Manager secret that contains a proxy '
            'configuration.'))
  group.add_argument(
      '--proxy-secret-version-id',
      required=True,
      help=('Version ID string of the AWS Secrets Manager secret that contains '
            'a proxy configuration.'))
