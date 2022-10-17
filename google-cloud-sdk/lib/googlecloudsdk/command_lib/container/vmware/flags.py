# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Helpers for flags in commands working with Anthos clusters on VMware."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties


def Get(args, flag_name, default=None):
  """Returns the value if it's set, otherwise returns None.

  Args:
    args: An argparser Namespace class instance.
    flag_name: A string type flag name.
    default: The default value to return if not found in the argparser
      namespace.

  Returns:
    The flag value if it is set by the user. If the flag is not added to the
    interface, or it is added by not specified by the user, returns the
    default value.
  """
  default_values = {
      'page_size': 100,
  }
  default_value = default_values.get(flag_name, default)
  return getattr(args, flag_name, default_value)


def LocationAttributeConfig():
  """Gets Google Cloud location resource attribute."""
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='Google Cloud location for the {resource}.',
      fallthroughs=[
          deps.PropertyFallthrough(properties.VALUES.container_vmware.location),
      ])


def GetLocationResourceSpec():
  """Constructs and returns the Resource specification for Location."""

  return concepts.ResourceSpec(
      'gkeonprem.projects.locations',
      resource_name='location',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
  )


def AddLocationResourceArg(parser, verb):
  """Adds a resource argument for Google Cloud location.

  Args:
    parser: The argparse.parser to add the resource arg to.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  concept_parsers.ConceptParser.ForResource(
      '--location',
      GetLocationResourceSpec(),
      'Google Cloud location {}.'.format(verb),
      required=True).AddToParser(parser)


def ClusterAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='cluster',
      help_text='cluster of the {resource}.',
  )


def GetClusterResourceSpec():
  return concepts.ResourceSpec(
      'gkeonprem.projects.locations.vmwareClusters',
      resource_name='cluster',
      vmwareClustersId=ClusterAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def AddClusterResourceArg(parser, verb, positional=True):
  """Adds a resource argument for an Anthos cluster on VMware.

  Args:
    parser: The argparse parser to add the resource arg to.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, whether the argument is positional or not.
  """
  name = 'cluster' if positional else '--cluster'
  concept_parsers.ConceptParser.ForResource(
      name, GetClusterResourceSpec(), 'cluster {}'.format(verb),
      required=True).AddToParser(parser)


def NodePoolAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='node_pool', help_text='node pool of the {resource}.')


def GetNodePoolResourceSpec():
  return concepts.ResourceSpec(
      'gkeonprem.projects.locations.vmwareClusters.vmwareNodePools',
      resource_name='node_pool',
      vmwareNodePoolsId=NodePoolAttributeConfig(),
      vmwareClustersId=ClusterAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def AddNodePoolResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a VMware node pool.

  Args:
    parser: The argparse parser to add the resource arg to.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, whether the argument is positional or not.
  """
  name = 'node_pool' if positional else '--node-pool'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetNodePoolResourceSpec(),
      'node pool {}'.format(verb),
      required=True).AddToParser(parser)


def AdminClusterMembershipAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='admin_cluster_membership',
      help_text='admin cluster membership of the {resource}, in the form of projects/PROJECT/locations/global/memberships/MEMBERSHIP. '
  )


def GetAdminClusterMembershipResourceSpec():
  return concepts.ResourceSpec(
      'gkehub.projects.locations.memberships',
      resource_name='admin_cluster_membership',
      membershipsId=AdminClusterMembershipAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def AddAdminClusterMembershipResourceArg(parser, positional=True):
  """Adds a resource argument for a VMware admin cluster membership.

  Args:
    parser: The argparse parser to add the resource arg to.
    positional: bool, whether the argument is positional or not.
  """
  name = 'admin_cluster_membership' if positional else '--admin-cluster-membership'
  # TODO(b/227667209): Add fallthrough from cluster location when regional
  # membership is implemented.
  concept_parsers.ConceptParser.ForResource(
      name,
      GetAdminClusterMembershipResourceSpec(),
      'membership of the admin cluster. Membership can be the membership ID or the full resource name.',
      required=True,
      flag_name_overrides={
          'location': '--admin-cluster-membership-location',
      }).AddToParser(parser)

  parser.set_defaults(admin_cluster_membership_location='global')


def AddForceUnenroll(parser):
  """Adds a flag for force unenroll operation when there are existing node pools.

  Args:
    parser: The argparse parser to add the flag to.
  """
  parser.add_argument(
      '--force',
      action='store_true',
      help='If set, any child node pools will also be unenrolled. This flag is required if the cluster has any associated node pools.',
  )


def AddForceDeleteCluster(parser):
  """Adds a flag for force delete cluster operation when there are existing node pools.

  Args:
    parser: The argparse parser to add the flag to.
  """
  parser.add_argument(
      '--force',
      action='store_true',
      help='If set, any node pools from the cluster will also be deleted. This flag is required if the cluster has any associated node pools.',
  )


def AddAllowMissingDeleteNodePool(parser):
  """Adds a flag for delete node pool operation to return success and perform no action when there is no matching node pool.

  Args:
    parser: The argparse parser to add the flag to.
  """
  parser.add_argument(
      '--allow-missing',
      action='store_true',
      help='If set, and the Vmware Node Pool is not found, the request will succeed but no action will be taken.',
  )


def AddAllowMissingDeleteCluster(parser):
  """Adds a flag for delete cluster operation to return success and perform no action when there is no matching cluster.

  Args:
    parser: The argparse parser to add the flag to.
  """
  parser.add_argument(
      '--allow-missing',
      action='store_true',
      help='If set, and the Anthos cluster on VMware is not found, the request will succeed but no action will be taken.',
  )


def AddAllowMissingUpdateCluster(parser):
  """Adds a flag to enable allow missing in an update cluster request.

  If set to true, and the cluster is not found, the request will
  create a new cluster with the provided configuration. The user
  must have both create and update permission to call Update with
  allow_missing set to true.

  Args:
    parser: The argparse parser to add the flag to.
  """
  parser.add_argument(
      '--allow-missing',
      action='store_true',
      hidden=True,
      help='If set, and the Anthos cluster on VMware is not found, the update request will try to create a new cluster with the provided configuration.',
  )


def AddValidationOnly(parser, hidden=False):
  """Adds a flag to only validate the request without performing the operation.

  Args:
    parser: The argparse parser to add the flag to.
    hidden: Set to False when validate-only flag is implemented in the API.
  """
  parser.add_argument(
      '--validate-only',
      action='store_true',
      help='If set, only validate the request, but do not actually perform the operation.',
      hidden=hidden,
  )


def AddImageType(parser, required=False):
  """Adds a flag to specify the node pool image type.

  Args:
    parser: The argparse parser to add the flag to.
    required: bool, True to raise an exception if the property is not set.
  """
  parser.add_argument(
      '--image-type',
      required=required,
      help='OS image type to use on node pool instances.',
  )


def AddReplicas(parser):
  """Adds a flag to specify the number of replicas in the node pool.

  Args:
    parser: The argparse parser to add the flag to.
  """
  parser.add_argument(
      '--replicas',
      type=int,
      help='Number of replicas to use on node pool instances.',
  )


def AddEnableLoadBalancer(parser):
  """Adds a flag to enable load balancer in the node pool.

  Args:
    parser: The argparse parser to add the flag to.
  """
  parser.add_argument(
      '--enable-load-balancer',
      action='store_true',
      help='If set, enable the use of load balancer on the node pool instances.',
  )


def AddAutoscaling(parser, required=False):
  """Adds a flag to specify the node pool autoscaling config.

  Args:
    parser: The argparse parser to add the flag to.
    required: bool, True to raise an exception if the property is not set.
  """
  group = parser.add_argument_group('Node pool autoscaling')
  group.add_argument(
      '--min-replicas',
      required=required,
      type=int,
      help='Minimum number of replicas in the node pool.',
  )
  group.add_argument(
      '--max-replicas',
      required=required,
      type=int,
      help='Maximum number of replicas in the node pool.',
  )


def AddVersion(parser):
  """Adds a flag to specify the Anthos cluster on VMware version.

  Args:
    parser: The argparse parser to add the flag to.
  """
  parser.add_argument(
      '--version',
      help='Anthos Cluster on VMware version for the user cluster resource',
  )


def AddServiceAddressCidrBlocks(parser):
  """Adds a flag to specify the IPv4 address ranges used in the services in the cluster.

  Args:
    parser: The argparse parser to add the flag to.
  """
  parser.add_argument(
      '--service-address-cidr-blocks',
      metavar='SERVICE_ADDRESS',
      type=arg_parsers.ArgList(
          min_length=1,
          max_length=1,
      ),
      required=True,
      help='IPv4 address range for all services in the cluster.',
  )


def AddPodAddressCidrBlocks(parser):
  """Adds a flag to specify the IPv4 address ranges used in the pods in the cluster.

  Args:
    parser: The argparse parser to add the flag to.
  """
  parser.add_argument(
      '--pod-address-cidr-blocks',
      metavar='POD_ADDRESS',
      type=arg_parsers.ArgList(
          min_length=1,
          max_length=1,
      ),
      required=True,
      help='IPv4 address range for all pods in the cluster.',
  )


def _AddF5Config(lb_mutex_group):
  """Adds flags for F5 Big IP load balancer.

  Args:
    lb_mutex_group: The mutex group to add the flags to.
  """
  f5_config_group = lb_mutex_group.add_argument_group('F5 Big IP Configuration')
  f5_config_group.add_argument(
      '--f5-config-address',
      type=str,
      required=True,
      help='F5 Big IP load balancer address.',
  )
  f5_config_group.add_argument(
      '--f5-config-partition',
      type=str,
      required=True,
      help='F5 Big IP load balancer partition.',
  )
  f5_config_group.add_argument(
      '--f5-config-snat-pool',
      type=str,
      help='F5 Big IP load balancer pool name if using SNAT.',
  )


def _AddMetalLbConfig(lb_mutex_group):
  """Adds flags for MetalLB load balancer.

  Args:
    lb_mutex_group: The mutex group to add the flags to.
  """
  metal_lb_config_group = lb_mutex_group.add_argument_group(
      'MetalLB Configuration')
  metal_lb_config_group.add_argument(
      '--metal-lb-config-address-pools',
      action='append',
      required=True,
      type=arg_parsers.ArgDict(
          spec={
              'pool': str,
              'addresses': arg_parsers.ArgList(),
              'avoid-buggy-ips': bool,
              'manual-assign': bool,
          },
          required_keys=[
              'pool',
              'addresses',
          ],
      ),
      help='MetalLB typed load balancers configuration.',
  )


def AddLoadBalancerConfig(parser):
  """Adds a command group to set the load balancer config.

  Args:
    parser: The argparse parser to add the flag to.
  """

  lb_config_group = parser.add_argument_group(
      help='Anthos on Vmware cluster load balancer configuration.',
  )
  lb_config_group.add_argument(
      '--control-plane-vip',
      required=True,
      help='VIP for the Kubernetes API of this cluster.',
  )
  lb_config_group.add_argument(
      '--ingress-vip',
      required=True,
      help='VIP for ingress traffic into this cluster.',
  )

  lb_mutex_group = lb_config_group.add_mutually_exclusive_group(
      help='Populate one of the load balancers.',
      required=True,
  )

  _AddMetalLbConfig(lb_mutex_group)
  _AddF5Config(lb_mutex_group)


def AddDescription(parser):
  """Adds a flag to specify the description of the resource.

  Args:
    parser: The argparse parser to add the flag to.
  """
  parser.add_argument(
      '--description', type=str, help='Description for the resource.')


def AddNodePoolDisplayName(parser):
  """Adds a flag to specify the display name of the node pool.

  Args:
    parser: The argparse parser to add the flag to.
  """
  parser.add_argument(
      '--display-name', type=str, help='Display name for the resource.')
