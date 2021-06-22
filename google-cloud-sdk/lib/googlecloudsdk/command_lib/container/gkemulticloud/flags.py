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


def AddRegion(parser, hidden=False):
  """Add the --location flag."""
  parser.add_argument(
      '--location',
      help='Anthos GKE Multi-cloud location.',
      required=True,
      hidden=hidden,
  )


def AddPodAddressCidrBlocks(parser):
  """Add the --pod-address-cidr-blocks flag."""
  parser.add_argument(
      '--pod-address-cidr-blocks',
      required=True,
      help=('IP address range for the pods in this cluster in CIDR '
            'notation (e.g. 10.0.0.0/8). Can be any RFC 1918 IP range.'))


def AddServiceAddressCidrBlocks(parser):
  """Add the --service-address-cidr-blocks flag."""
  parser.add_argument(
      '--service-address-cidr-blocks',
      required=True,
      help=('IP address range for the services IPs in CIDR notation '
            '(e.g. 10.0.0.0/8). Can be any RFC 1918 IP range.'))


def AddSubnetID(parser, help_text):
  """Add the --subnet-id flag."""
  parser.add_argument(
      '--subnet-id',
      required=True,
      help='Subnet ID of an existing VNET to use for {}.'.format(help_text))


def GetSubnetID(args):
  return args.subnet_id


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
      help='Kubernetes version to use for the cluster.')


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
      '--min-nodes',
      required=True,
      type=int,
      help='Minimum number of nodes in the node pool.')
  group.add_argument(
      '--max-nodes',
      required=True,
      type=int,
      help='Maximum number of nodes in the node pool.')


def GetAutoscalingParams(args):
  min_nodes = 0
  max_nodes = 0
  min_nodes = args.min_nodes
  max_nodes = args.max_nodes

  return (min_nodes, max_nodes)


def AddMaxPodsPerNode(parser):
  parser.add_argument(
      '--max-pods-per-node', type=int, help='Maximum number of pods per node.')


def GetMaxPodsPerNode(args):
  return args.max_pods_per_node


def AddVMSize(parser):
  parser.add_argument(
      '--vm-size',
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


def AddRootVolumeSize(parser):
  parser.add_argument(
      '--root-volume-size',
      type=arg_parsers.BinarySize(
          suggested_binary_size_scales=['GB', 'GiB', 'TB', 'TiB'],
          default_unit='Gi'),
      help="""
        Size of the root volume. The value must be a whole number
        followed by a size unit of ``GB'' for gigabyte, or ``TB'' for
        terabyte. If no size unit is specified, GB is assumed.
        """)


def GetRootVolumeSize(args):
  size = getattr(args, 'root_volume_size', None)
  if not size:
    return None

  # Volume sizes are currently in GB, argument is in B.
  return int(size) >> 30


def AddMainVolumeSize(parser):
  parser.add_argument(
      '--main-volume-size',
      type=arg_parsers.BinarySize(
          suggested_binary_size_scales=['GB', 'GiB', 'TB', 'TiB'],
          default_unit='Gi'),
      help="""
        Size of the main volume. The value must be a whole number
        followed by a size unit of ``GB'' for gigabyte, or ``TB'' for
        terabyte. If no size unit is specified, GB is assumed.
        """)


def GetMainVolumeSize(args):
  size = getattr(args, 'main_volume_size', None)
  if not size:
    return None

  # Volume sizes are currently in GB, argument is in B.
  return int(size) >> 30


def AddTags(parser, noun):
  help_text = """\
  Applies the given tags (comma separated) on the {0}. Example:

    $ {{command}} EXAMPLE_{1} --tags=tag1=one,tag2=two
  """.format(noun, noun.replace(' ', '_').upper())

  parser.add_argument(
      '--tags',
      type=arg_parsers.ArgDict(min_length=1),
      metavar='TAG',
      help=help_text)


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
