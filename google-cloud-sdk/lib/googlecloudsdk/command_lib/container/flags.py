# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Flags and helpers for the container related commands."""

import argparse

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


# TODO(b/28318474): move flags common across commands here.
def AddImageTypeFlag(parser, target):
  """Adds a --image-type flag to the given parser."""
  help_text = """\
The image type to use for the {target}. Defaults to server-specified.

Image Type specifies the base OS that the nodes in the {target} will run on.
If an image type is specified, that will be assigned to the {target} and all
future upgrades will use the specified image type. If it is not specified the
server will pick the default image type.

The default image type and the list of valid image types are available
using the following command.

  $ gcloud container get-server-config
""".format(target=target)

  parser.add_argument('--image-type', help=help_text)


def AddClusterVersionFlag(parser, suppressed=False, help=None):  # pylint: disable=redefined-builtin
  """Adds a --cluster-version flag to the given parser."""
  help_text = argparse.SUPPRESS if suppressed else help or """\
The Kubernetes version to use for the master and nodes. Defaults to
server-specified.

The default Kubernetes version is available using the following command.

  $ gcloud container get-server-config
"""

  return parser.add_argument('--cluster-version', help=help_text)


def AddClusterAutoscalingFlags(parser, update_group=None, hidden=False):
  """Adds autoscaling related flags to parser.

  Autoscaling related flags are: --enable-autoscaling
  --min-nodes --max-nodes flags.

  Args:
    parser: A given parser.
    update_group: An optional group of mutually exclusive flag options
        to which an --enable-autoscaling flag is added.
    hidden: If true, suppress help text for added options.
  """

  group = parser.add_argument_group('Cluster autoscaling')
  autoscaling_group = group if update_group is None else update_group
  autoscaling_group.add_argument(
      '--enable-autoscaling',
      default=None if update_group else False,
      help="""\
Enables autoscaling for a node pool.

Enables autoscaling in the node pool specified by --node-pool or
the default node pool if --node-pool is not provided.""",
      hidden=hidden,
      action='store_true')
  # If we have an update group, add a custom inverted arg.
  if update_group:
    autoscaling_group.add_argument(
        '--disable-autoscaling',
        default=None,
        help="""\
Disables autoscaling for a node pool. This flag is deprecated and will be
removed in a future release. Use --no-enable-autoscaling instead.""",
        hidden=hidden,
        action='store_false',
        dest='enable_autoscaling')
  group.add_argument(
      '--max-nodes',
      help="""\
Maximum number of nodes in the node pool.

Maximum number of nodes to which the node pool specified by --node-pool
(or default node pool if unspecified) can scale. Ignored unless
--enable-autoscaling is also specified.""",
      hidden=hidden,
      type=int)
  group.add_argument(
      '--min-nodes',
      help="""\
Minimum number of nodes in the node pool.

Minimum number of nodes to which the node pool specified by --node-pool
(or default node pool if unspecified) can scale. Ignored unless
--enable-autoscaling is also specified.""",
      hidden=hidden,
      type=int)


def AddLocalSSDFlag(parser, suppressed=False):
  """Adds a --local-ssd-count flag to the given parser."""
  help_text = argparse.SUPPRESS if suppressed else """\
The number of local SSD disks to provision on each node.

Local SSDs have a fixed 375 GB capacity per device. The number of disks that
can be attached to an instance is limited by the maximum number of disks
available on a machine, which differs by compute zone. See
https://cloud.google.com/compute/docs/disks/local-ssd for more information."""
  parser.add_argument(
      '--local-ssd-count',
      help=help_text,
      type=int,
      default=0)


def AddAcceleratorArgs(parser):
  """Adds Accelerator-related args."""
  parser.add_argument(
      '--accelerator',
      type=arg_parsers.ArgDict(spec={
          'type': str,
          'count': int,
      }, required_keys=['type'], max_length=2),
      metavar='type=TYPE,[count=COUNT]',
      help="""\
      Attaches accelerators (e.g. GPUs) to all nodes.

      *type*::: (Required) The specific type (e.g. nvidia-tesla-k80 for nVidia Tesla K80)
      of accelerator to attach to the instances. Use 'gcloud compute
      accelerator-types list' to learn about all available accelerator types.

      *count*::: (Optional) The number of pieces of the accelerator to attach to the
      instances. The default value is 1.
      """)


def AddZoneFlag(parser):
  # TODO(b/33343238): Remove the short form of the zone flag.
  # TODO(b/18105938): Add zone prompting
  """Adds the --zone flag to the parser."""
  parser.add_argument(
      '--zone', '-z',
      help='The compute zone (e.g. us-central1-a) for the cluster',
      action=actions.StoreProperty(properties.VALUES.compute.zone))


def AddZoneAndRegionFlags(parser, region_hidden=False):
  """Adds the --zone and --region flags to the parser."""
  group = parser.add_mutually_exclusive_group()
  group.add_argument(
      '--zone', '-z',
      help='The compute zone (e.g. us-central1-a) for the cluster',
      action=actions.StoreProperty(properties.VALUES.compute.zone))
  group.add_argument(
      '--region',
      help='The compute region (e.g. us-central1) for the cluster. '
           'For the given cluster, only one of flags --zone and --region can '
           'be specified.',
      hidden=region_hidden)


def AddAsyncFlag(parser):
  """Adds the --async flags to the given parser."""
  parser.add_argument(
      '--async',
      action='store_true',
      default=None,
      help='Don\'t wait for the operation to complete.')


def GetAsyncValueFromAsyncAndWaitFlags(async, wait):
  # TODO(b/28523509): Remove this function after July 2017.
  """Derives --async value from --async and --wait flags for gcloud container.

  Args:
    async: The --async flag value
    wait: The --wait flag value.

  Returns:
    boolean representing derived async value
  """
  async_was_set = async is not None
  wait_was_set = wait is not None

  if wait_was_set:
    log.warning('\nThe --wait flag is deprecated and will be removed in a '
                'future release. Use --async or --no-async instead.\n')

  if not async_was_set and not wait_was_set:
    return False  # Waiting is the 'default' value for cloud sdk
  elif async_was_set and not wait_was_set:
    return async
  elif not async_was_set and wait_was_set:
    return not wait
  else:  # async_was_set and wait_was_set
    if (async and wait) or (not async and not wait):
      raise exceptions.InvalidArgumentException('--async',
                                                'You cannot set both the '
                                                '--async and --wait flags.')
    elif async and not wait:
      return True
    else:  # not async or wait
      return False


def AddClustersWaitAndAsyncFlags(parser):
  # TODO(b/28523509): Remove this function after July 2017.
  """Adds the --wait and --async flags to the given parser."""
  parser.add_argument(
      '--wait',
      action='store_true',
      default=None,
      # The default value is wait=True but the logic is done in
      # GetAsyncValueFromAsyncAndWaitFlags as there are wait and async flags
      help='DEPRECATED, use --no-async. Poll the operation for completion '
           'after issuing a create request.')
  parser.add_argument(
      '--async',
      action='store_true',
      default=None,
      # The default value is async=False but the logic is done in
      # GetAsyncValueFromAsyncAndWaitFlags as there are wait and async flags
      help='Don\'t wait for the operation to complete.')


def AddEnableKubernetesAlphaFlag(parser, suppressed=False):
  """Adds a --enable-kubernetes-alpha flag to parser."""
  help_text = argparse.SUPPRESS if suppressed else """\
Enable Kubernetes alpha features on this cluster. Selecting this
option will result in the cluster having all Kubernetes alpha API groups and
features turned on. Cluster upgrades (both manual and automatic) will be
disabled and the cluster will be automatically deleted after 30 days.

Alpha clusters are not covered by the Container Engine SLA and should not be
used for production workloads."""
  parser.add_argument(
      '--enable-kubernetes-alpha',
      action='store_true',
      help=help_text)


def AddNodeLabelsFlag(parser, for_node_pool=False):
  """Adds a --node-labels flag to the given parser."""
  if for_node_pool:
    help_text = """\
Applies the given kubernetes labels on all nodes in the new node-pool. Example:

  $ {command} node-pool-1 --cluster=example-cluster --node-labels=label1=value1,label2=value2
"""
  else:
    help_text = """\
Applies the given kubernetes labels on all nodes in the new node-pool. Example:

  $ {command} example-cluster --node-labels=label-a=value1,label-2=value2
"""
  help_text += """
New nodes, including ones created by resize or recreate, will have these labels
on the kubernetes API node object and can be used in nodeSelectors.
See http://kubernetes.io/docs/user-guide/node-selection/ for examples."""

  parser.add_argument(
      '--node-labels',
      metavar='NODE_LABEL',
      type=arg_parsers.ArgDict(),
      help=help_text)


def AddPreemptibleFlag(parser, for_node_pool=False, suppressed=False):
  """Adds a --preemptible flag to parser."""
  if suppressed:
    help_text = argparse.SUPPRESS
  else:
    if for_node_pool:
      help_text = """\
Create nodes using preemptible VM instances in the new nodepool.

  $ {command} node-pool-1 --cluster=example-cluster --preemptible
"""
    else:
      help_text = """\
Create nodes using preemptible VM instances in the new cluster.

  $ {command} example-cluster --preemptible
"""
    help_text += """
New nodes, including ones created by resize or recreate, will use preemptible
VM instances. See https://cloud.google.com/container-engine/docs/preemptible-vm
for more information on how to use Preemptible VMs with Container Engine."""

  parser.add_argument(
      '--preemptible',
      action='store_true',
      help=help_text)


def AddNodePoolNameArg(parser, help_text):
  """Adds a name flag to the given parser.

  Args:
    parser: A given parser.
    help_text: The help text describing the operation being performed.
  """
  parser.add_argument(
      'name',
      metavar='NAME',
      help=help_text)


def AddNodePoolClusterFlag(parser, help_text):
  """Adds a --cluster flag to the parser.

  Args:
    parser: A given parser.
    help_text: The help text describing usage of the --cluster flag being set.
  """
  parser.add_argument(
      '--cluster',
      help=help_text,
      action=actions.StoreProperty(properties.VALUES.container.cluster))


# TODO(b/33344111): Add test coverage. This flag was added preemptively, but it
# currently has inadequate testing.
def AddEnableAutoRepairFlag(parser, for_node_pool=False, suppressed=False):
  """Adds a --enable-autorepair flag to parser."""
  if suppressed:
    help_text = argparse.SUPPRESS
  else:
    if for_node_pool:
      help_text = """\
Sets autorepair feature for a node-pool.

  $ {command} node-pool-1 --cluster=example-cluster --enable-autorepair
"""
    else:
      help_text = """\
Sets autorepair feature for a cluster's default node-pool(s).

  $ {command} example-cluster --enable-autorepair
"""
    help_text += """
See https://cloud.google.com/container-engine/docs/node-auto-repair for \
more info."""

  parser.add_argument(
      '--enable-autorepair',
      action='store_true',
      default=None,
      help=help_text)


def AddEnableAutoUpgradeFlag(parser, for_node_pool=False, suppressed=False):
  """Adds a --enable-autoupgrade flag to parser."""
  if suppressed:
    help_text = argparse.SUPPRESS
  else:
    if for_node_pool:
      help_text = """\
Sets autoupgrade feature for a node-pool.

  $ {command} node-pool-1 --cluster=example-cluster --enable-autoupgrade
"""
    else:
      help_text = """\
Sets autoupgrade feature for a cluster's default node-pool(s).

  $ {command} example-cluster --enable-autoupgrade
"""
    help_text += """
See https://cloud.google.com/container-engine/docs/node-managament for more \
info."""

  parser.add_argument(
      '--enable-autoupgrade',
      action='store_true',
      default=None,
      help=help_text)


def AddTagsFlag(parser, help_text):
  """Adds a --tags to the given parser."""
  parser.add_argument(
      '--tags',
      metavar='TAG',
      type=arg_parsers.ArgList(min_length=1),
      help=help_text)


def AddServiceAccountFlag(parser, suppressed=False):
  """Adds a --service-account to the given parser."""
  help_text = argparse.SUPPRESS if suppressed else """\
The Google Cloud Platform Service Account to be used by the node VMs. \
If no Service Account is specified, the "default" service account is used.
"""

  parser.add_argument(
      '--service-account',
      help=help_text)


def AddMasterAuthorizedNetworksFlags(parser, update_group=None, hidden=False):
  """Adds Master Authorized Networks related flags to parser.

  Master Authorized Networks related flags are:
  --enable-master-authorized-networks --master-authorized-networks.

  Args:
    parser: A given parser.
    update_group: An optional group of mutually exclusive flag options
        to which an --enable-master-authorized-networks flag is added.
    hidden: If true, suppress help text for added options.
  """
  group = parser.add_argument_group('Master Authorized Networks')
  authorized_networks_group = group if update_group is None else update_group
  authorized_networks_group.add_argument(
      '--enable-master-authorized-networks',
      default=None if update_group else False,
      help='Allow only Authorized Networks and GCE Public IPs to connect to '
      'Kubernetes master through HTTPS. By default public internet (0.0.0.0/0)'
      ' is allowed to connect to Kubernetes master through HTTPS.',
      hidden=hidden,
      action='store_true')
  group.add_argument(
      '--master-authorized-networks',
      type=arg_parsers.ArgList(min_length=1),
      metavar='NETWORK',
      help='The list of external networks that are allowed to connect to '
      'Kubernetes master through HTTPS. Specified in CIDR notation '
      '(e.g. 192.168.100.0/24). Can not be specified unless '
      '--enable-master-authorized-networks is also specified.',
      hidden=hidden)


def AddNetworkPolicyFlags(parser, hidden=False):
  """Adds --enable-network-policy flags to parser."""
  parser.add_argument(
      '--enable-network-policy',
      action='store_true',
      default=None,
      hidden=hidden,
      help='Enable network policy enforcement for this cluster.')


def AddEnableLegacyAuthorizationFlag(parser, hidden=False):
  """Adds a --enable-legacy-authorization flag to parser."""
  help_text = """\
Enables the legacy ABAC authentication for the cluster.
See https://cloud.google.com/container-engine/docs/legacyabac for more \
info."""
  parser.add_argument(
      '--enable-legacy-authorization',
      action='store_true',
      default=None,
      hidden=hidden,
      help=help_text)


def AddStartIpRotationFlag(parser, hidden=False):
  """Adds a --start-ip-rotation flag to parser."""
  help_text = """\
Start the rotation of this cluster to a new IP. For example:

  $ {command} example-cluster --start-ip-rotation

This causes the cluster to serve on two IPs, and will initiate a node upgrade \
to point to the new IP."""
  parser.add_argument(
      '--start-ip-rotation',
      action='store_true',
      default=False,
      hidden=hidden,
      help=help_text)


def AddCompleteIpRotationFlag(parser, hidden=False):
  """Adds a --complete-ip-rotation flag to parser."""
  help_text = """\
Complete the IP rotation for this cluster. For example:

  $ {command} example-cluster --complete-ip-rotation

This causes the cluster to stop serving its old IP, and return to a single IP \
state."""
  parser.add_argument(
      '--complete-ip-rotation',
      action='store_true',
      default=False,
      hidden=hidden,
      help=help_text)


def AddLabelsFlag(parser, suppressed=False):
  """Adds Labels related flags to parser.

  Args:
    parser: A given parser.
    suppressed: Whether or not to suppress help text.
  """

  help_text = argparse.SUPPRESS if suppressed else """\
Labels to apply to the Google Cloud resources in use by the Container Engine
cluster. These are unrelated to Kubernetes labels.
Example:

  $ {command} example-cluster --labels=label_a=value1,label_b=,label_c=value3
"""
  parser.add_argument(
      '--labels',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      help=help_text)


def AddUpdateLabelsFlag(parser, suppressed=False):
  """Adds Update Labels related flags to parser.

  Args:
    parser: A given parser.
    suppressed: Whether or not to suppress help text.
  """

  help_text = argparse.SUPPRESS if suppressed else """\
Labels to apply to the Google Cloud resources in use by the Container Engine
cluster. These are unrelated to Kubernetes labels.
Example:

  $ {command} example-cluster --update-labels=label_a=value1,label_b=value2
"""
  parser.add_argument(
      '--update-labels',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      help=help_text)


def AddRemoveLabelsFlag(parser, suppressed=False):
  """Adds Remove Labels related flags to parser.

  Args:
    parser: A given parser.
    suppressed: Whether or not to suppress help text.
  """

  help_text = argparse.SUPPRESS if suppressed else """\
Labels to remove from the Google Cloud resources in use by the Container Engine
cluster. These are unrelated to Kubernetes labels.
Example:

  $ {command} example-cluster --remove-labels=label_a,label_b
"""
  parser.add_argument(
      '--remove-labels',
      metavar='KEY',
      type=arg_parsers.ArgList(),
      help=help_text)


def AddDiskTypeFlag(parser, suppressed=False):
  """Adds a --disk-type flag to the given parser.

  Args:
    parser: A given parser.
    suppressed: Whether or not to suppress help text.
  """
  help_text = argparse.SUPPRESS if suppressed else """\
Type of the node VM boot disk.
"""
  parser.add_argument(
      '--disk-type',
      help=help_text,
      choices=['pd-standard', 'pd-ssd'])


def AddIPAliasFlags(parser, hidden=False):
  """Adds flags related to IP aliases to the parser.

  Args:
    parser: A given parser.
    hidden: Whether or not to hide the help text.
  """

  parser.add_argument(
      '--enable-ip-alias',
      action='store_true',
      default=None,
      hidden=hidden,
      help="""\
Enable use of alias IPs (https://cloud.google.com/compute/docs/alias-ip/)
for pod IPs. This will create two new subnetworks, one for the
instance and pod IPs, and another to reserve space for the services
range.

Can not be specified unless '--enable-kubernetes-alpha' is also specified.
""")

  parser.add_argument(
      '--services-ipv4-cidr',
      metavar='CIDR',
      hidden=hidden,
      help="""\
Set the IP range for the services IPs.

Can be specified as a netmask size (e.g. '/20') or as in CIDR notion
(e.g. '10.100.0.0/20'). If given as a netmask size, the IP range will
be choosen automatically from the available space in the network.

If unspecified, the services CIDR range will use automatic defaults.

Can not be specified unless '--enable-ip-alias' is also specified.
""")

  parser.add_argument(
      '--create-subnetwork',
      metavar='KEY=VALUE',
      hidden=hidden,
      type=arg_parsers.ArgDict(),
      help="""\
Create a new subnetwork for the cluster. The name and range of the
subnetwork can be customized via optional 'name' and 'range' key-value
pairs.

'name' specifies the name of the subnetwork to be created.

'range' specifies the IP range for the new subnetwork. This can either
be a netmask size (e.g. '/20') or a CIDR range (e.g. '10.0.0.0/20').
If a netmask size is specified, the IP is automatically taken from
the free space in the cluster's network.

Examples:

Create a new subnetwork named "my-subnet" with netmask of size 21.

      $ {command} --create-subnetwork name=my-subnet,range=/21

Create a new subnetwork with a default name with the primary range of
10.100.0.0/16.

      $ {command} --create-subnetwork range=10.100.0.0/16

Create a new subnetwork with the name "my-subnet" with a default range.

      $ {command} --create-subnetwork name=my-subnet

Can not be specified unless '--enable-ip-alias' is also specified. Can
not be used in conjunction with the '--subnetwork' option.
""")


def AddTagOrDigestPositional(parser, verb, repeated=True, tags_only=False,
                             arg_name=None, metavar=None):
  digest_str = '*.gcr.io/project_id/image_path@sha256:<digest> or'
  if tags_only:
    digest_str = ''

  if not arg_name:
    arg_name = 'image_names' if repeated else 'image_name'
    metavar = metavar or 'IMAGE_NAME'

  parser.add_argument(
      arg_name,
      metavar=metavar or arg_name.upper(),
      nargs='+' if repeated else None,
      help=('The fully qualified name(s) of image(s) to {verb}. '
            'The name(s) should be formatted as {digest_str} '
            '*.gcr.io/project_id/image_path[:<tag>].'.format(
                verb=verb, digest_str=digest_str)))


def AddImagePositional(parser, verb):
  parser.add_argument(
      'image_name',
      help=('The fully qualified image name of the image to {verb}. The name '
            'format should be *.gcr.io/project_id/image_path. '.format(
                verb=verb)))
