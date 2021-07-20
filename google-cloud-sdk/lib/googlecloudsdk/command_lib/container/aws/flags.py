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

from googlecloudsdk.calliope import arg_parsers


def AddAwsRegion(parser):
  """Add the --aws-region flag."""
  parser.add_argument(
      "--aws-region", required=True, help="AWS region to deploy the cluster.")


def AddVpcId(parser):
  """Add the --vpc-id flag."""
  parser.add_argument(
      "--vpc-id", required=True, help="VPC associated with the cluster.")


def AddServiceLoadBalancerSubnetIDs(parser):
  parser.add_argument(
      "--service-load-balancer-subnet-ids",
      required=True,
      type=arg_parsers.ArgList(),
      metavar="SUBNET_ID",
      help=("Subnets for the services of type Load Balancer "))


def AddIamInstanceProfile(parser):
  parser.add_argument(
      "--iam-instance-profile",
      required=True,
      help="IAM instance profile associated with the cluster")


def AddInstanceType(parser):
  parser.add_argument("--instance-type", help="AWS EC2 instance type.")


def AddSshEC2KeyPair(parser):
  parser.add_argument(
      "--ssh-ec2-key-pair",
      help="Name of the EC2 key pair to login into control plane nodes.")


def AddDatabaseEncryptionKmsKeyArn(parser):
  parser.add_argument(
      "--database-encryption-kms-key-arn",
      required=True,
      help=("Amazon Resource Name (ARN) of the AWS KMS key to encrypt "
            "cluster secrets."))


def AddRoleArn(parser):
  parser.add_argument(
      "--role-arn",
      required=True,
      help=("Amazon Resource Name (ARN) of the IAM role to assume when "
            "managing AWS resources."))


def AddRoleSessionName(parser):
  parser.add_argument(
      "--role-session-name",
      help="Identifier for the assumed role session.")


def AddSecurityGroupIds(parser, noun):
  parser.add_argument(
      "--security-group-ids",
      type=arg_parsers.ArgList(),
      metavar="SECURITY_GROUP_ID",
      help="IDs of additional security groups to add to {}.".format(noun))
