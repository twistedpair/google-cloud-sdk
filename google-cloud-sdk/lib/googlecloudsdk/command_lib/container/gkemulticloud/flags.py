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
"""Helpers for flags in commands working with GKE Multi-cloud."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions


def AddRegion(parser, hidden=False):
  parser.add_argument(
      '--region',
      help='Anthos GKE Multi-cloud region.',
      required=True,
      hidden=hidden,
  )


def AddClusterIpv4Cidr(parser):
  """Add the --cluster-ipv4-cidr flag."""
  parser.add_argument(
      '--cluster-ipv4-cidr',
      required=True,
      help=('IP address range for the pods in this cluster in CIDR '
            'notation (e.g. 10.0.0.0/8). Can be any RFC 1918 IP range.'))


def AddServiceIpv4Cidr(parser):
  """Add the --service-ipv4-cidr flag."""
  parser.add_argument(
      '--service-ipv4-cidr',
      required=True,
      help=('IP address range for the services IPs in CIDR notation '
            '(e.g. 10.0.0.0/8). Can be any RFC 1918 IP range.'))


def AddSubnetId(parser):
  parser.add_argument(
      '--subnet-id',
      required=True,
      type=arg_parsers.ArgList(),
      metavar='SUBNET_ID',
      help='Subnet ID of an existing VNET to use for the control plane.')


def AddOutputFile(parser, help_action):
  """Add an output file argument.

  Args:
    parser: The argparse.parser to add the output file argument to.
    help_action: str, describes the action of what will be stored.
  """
  parser.add_argument(
      '--output-file', help='Path to the output file {}.'.format(help_action))


def AddValidateOnly(parser, help_action):
  """Add the --validate-only argument.

  Args:
    parser: The argparse.parser to add the argument to.
    help_action: str, describes the action that will be validated.
  """
  parser.add_argument(
      '--validate-only',
      action='store_true',
      help='Validate the {}, but don\'t actually perform it.'.format(
          help_action))


def GetValidateOnly(args):
  return args.validate_only


def AddClusterVersion(parser):
  parser.add_argument(
      '--cluster-version',
      required=True,
      help='The Kubernetes version to use for the cluster.')


def GetClusterVersion(args):
  return args.cluster_version


def AddNodeVersion(parser):
  parser.add_argument(
      '--node-version',
      required=True,
      help='Kubernetes version to use for the node pool.')


def GetNodeVersion(args):
  return args.node_version


def AddAutoscaling(parser):
  """Add node pool autoscaling flags.

  Args:
    parser: The argparse.parser to add the arguments to.
  """

  group = parser.add_argument_group('Node pool autoscaling')
  group.add_argument(
      '--enable-autoscaling',
      action='store_true',
      help='Enables autoscaling for a node pool.')
  group.add_argument(
      '--min-nodes',
      required=True,
      type=int,
      help='Minimum number of nodes in the node pool.')
  group.add_argument(
      '--max-nodes',
      required=True,
      type=int,
      help='Maximum number of nodes in the node pool.')


def GetAutoscalingEnabled(args):
  return args.enable_autoscaling


def GetAutoscalingParams(args):
  min_nodes = 0
  max_nodes = 0
  if args.enable_autoscaling:
    min_nodes = args.min_nodes
    max_nodes = args.max_nodes

  return (min_nodes, max_nodes)


def AddNumberOfNodes(parser):
  parser.add_argument(
      '--num-nodes',
      type=int,
      help='Number of nodes to create in the node pool.')


def GetNumberOfNodes(args):
  return args.num_nodes


def CheckNumberOfNodesAndAutoscaling(args):
  """Verifies the arguments for specifying node counts are correct.

  Args:
    args: The argparse.parser to check the arguments.

  Raises:
    parser_errors.ArgumentException
  """

  if args.enable_autoscaling:
    if args.num_nodes:
      raise exceptions.ConflictingArgumentsException(
          'num-nodes', 'Cannot be specified when autoscaling is enabled.')
    if not args.min_nodes:
      raise exceptions.RequiredArgumentException(
          'min-nodes', 'Required when autoscaling is enabled.')
    if not args.max_nodes:
      raise exceptions.RequiredArgumentException(
          'max-nodes', 'Required when autoscaling is enabled.')
  else:
    if not args.num_nodes:
      raise exceptions.OneOfArgumentsRequiredException(
          ['num-nodes', 'enable-autoscaling'],
          'Either number of nodes must be specified, or autoscaling enabled.')


def AddMaxPodsPerNode(parser):
  parser.add_argument(
      '--max-pods-per-node', type=int, help='Maximum number of pods per node.')


def AddSubnetID(parser, help_text, hidden=False):
  """Add the --subnet-id argument.

  Args:
    parser: The argparse.parser to add the argument to.
    help_text: str, describes additional help text for the subnet ID.
    hidden: bool, whether to hide the argument.
  """

  parser.add_argument(
      '--subnet-id',
      required=True,
      hidden=hidden,
      help='Subnet ID of an existing VNET to use for {}. '.format(help_text))


def GetSubnetID(args):
  return args.subnet_id


def AddVMSize(parser):
  parser.add_argument(
      '--vm-size',
      required=True,
      help='Azure Virtual Machine Size (e.g. Standard_DS1_v).')


def GetVMSize(args):
  return args.vm_size


def AddSSHPublicKey(parser):
  parser.add_argument(
      '--ssh-public-key',
      required=True,
      help='SSH public key to use for authentication.')


def GetSSHPublicKey(args):
  return args.ssh_public_key


def AddRootVolumeSize(parser, required=True):
  parser.add_argument(
      '--root-volume-size',
      required=required,
      type=int,
      help='Size of the root volume in GiB.')


def GetRootVolumeSize(args):
  return args.root_volume_size


def AddMainVolumeSize(parser):
  parser.add_argument(
      '--main-volume-size',
      required=True,
      type=int,
      help='Size of the main volume in GiB.')


def GetMainVolumeSize(args):
  return args.main_volume_size


def AddTags(parser):
  parser.add_argument(
      '--tags',
      type=arg_parsers.ArgDict(min_length=1),
      metavar='TAG',
      help="""\
Applies the given tags (comma separated) on the Azure resources. Example:

  $ {command} my-instance --tags=tag1=one,tag2=two
""")


def GetTags(args):
  return getattr(args, 'tags', None) or {}


def AddEnableEncryptionAtHost(parser, noun):
  parser.add_argument(
      '--enable-encryption-at-host',
      action='store_true',
      help='Enables encryption at the host in the {}'.format(noun))


def GetEnableEncryptionAtHost(args):
  return args.enable_encryption_at_host


def AddCluster(parser, help_action):
  parser.add_argument(
      '--cluster',
      required=True,
      help='Name of the cluster to {} node pools with.'.format(help_action))
