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

from googlecloudsdk.api_lib.compute import constants as compute_constants
from googlecloudsdk.api_lib.container import api_adapter
from googlecloudsdk.api_lib.container import util
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.container import constants
from googlecloudsdk.core import properties


def AddBasicAuthFlags(parser,
                      username_default='admin',
                      enable_basic_auth_default=True):
  """Adds basic auth flags to the given parser.

  Basic auth flags are: --username, --enable-basic-auth, and --password.

  Args:
    parser: A given parser.
    username_default: The default username to use for this parser (create is
        'admin', update is None).
    enable_basic_auth_default: The default value for --enable-basic-auth (create
        is True, update is None).
  """
  basic_auth_group = parser.add_group(help='Basic auth')
  username_group = basic_auth_group.add_group(
      mutex=True, help='Username options')
  username_help_text = """\
The user name to use for basic auth for the cluster. Use `--password` to specify
a password; if not, the server will randomly generate one."""
  username_group.add_argument(
      '--username', '-u', help=username_help_text, default=username_default)

  enable_basic_auth_help_text = """\
Enable basic (username/password) auth for the cluster.  `--enable-basic-auth` is
an alias for `--username=admin`; `--no-enable-basic-auth` is an alias for
`--username=""`. Use `--password` to specify a password; if not, the server will
randomly generate one."""
  username_group.add_argument(
      '--enable-basic-auth',
      help=enable_basic_auth_help_text,
      action='store_true',
      default=enable_basic_auth_default)

  basic_auth_group.add_argument(
      '--password',
      help='The password to use for cluster auth. Defaults to a '
      'server-specified randomly-generated string.')


def MungeBasicAuthFlags(args):
  """Munges flags associated with basic auth.

  If --enable-basic-auth is specified, converts it --username value, and checks
  that --password is only specified if it makes sense.

  Args:
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.

  Raises:
    util.Error, if flags conflict.
  """
  if args.IsSpecified('enable_basic_auth'):
    if not args.enable_basic_auth:
      args.username = ''
    else:
      # Even though this is the default for `clusters create`, we still need to
      # set it for `clusters update`.
      args.username = 'admin'
  if not args.username and args.IsSpecified('password'):
    raise util.Error(constants.USERNAME_PASSWORD_ERROR_MSG)


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


def AddAutoprovisioningFlags(parser, update_group=None, hidden=False):
  """Adds node autoprovisioning related flags to parser.

  Autoprovisioning related flags are: --enable-autoprovisioning
  --min-cpu --max-cpu --min-memory --max-memory flags.

  Args:
    parser: A given parser.
    update_group: An optional group of mutually exclusive flag options
        to which an --enable-autoprovisioning flag is added.
    hidden: If true, suppress help text for added options.
  """

  group = parser.add_argument_group('Node autoprovisioning')
  autoprovisioning_group = group if update_group is None else update_group
  autoprovisioning_group.add_argument(
      '--enable-autoprovisioning',
      default=None,
      help="""\
Enables  node autoprovisioning for a cluster.

Cluster Autoscaler will be able to create new node pools.""",
      hidden=hidden,
      action='store_true')
  group.add_argument(
      '--max-cpu',
      help="""\
Maximum number of cores in the cluster.

Maximum number of cores to which the cluster can scale.""",
      hidden=hidden,
      type=int)
  group.add_argument(
      '--min-cpu',
      help="""\
Minimum number of cores in the cluster.

Minimum number of cores to which the cluster can scale.""",
      hidden=hidden,
      type=int)
  group.add_argument(
      '--max-memory',
      help="""\
Maximum memory in the cluster.

Maximum number of gigabytes of memory to which the cluster can scale.""",
      hidden=hidden,
      type=int)
  group.add_argument(
      '--min-memory',
      help="""\
Minimum memory in the cluster.

Minimum number of gigabytes of memory to which the cluster can scale.""",
      hidden=hidden,
      type=int)


def AddEnableBinAuthzFlag(parser, hidden=True):
  """Adds a --enable-binauthz flag to parser."""
  help_text = """Enable Binary Authorization for this cluster."""
  parser.add_argument(
      '--enable-binauthz',
      action='store_true',
      default=None,
      help=help_text,
      hidden=hidden,)


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


def AddNodeTaintsFlag(parser, for_node_pool=False, hidden=False):
  """Adds a --node-taints flag to the given parser."""
  if for_node_pool:
    help_text = """\
Applies the given kubernetes taints on all nodes in the new node-pool, which can be used with tolerations for pod scheduling. Example:

  $ {command} node-pool-1 --cluster=example-cluster --node-taints=key1=val1:NoSchedule,key2=val2:PreferNoSchedule
"""
  else:
    help_text = """\
Applies the given kubernetes taints on all nodes in default node-pool(s) in new cluster, which can be used with tolerations for pod scheduling. Example:

  $ {command} example-cluster --node-taints=key1=val1:NoSchedule,key2=val2:PreferNoSchedule
"""
  help_text += """
Please see https://cloud.google.com/container-engine/docs/node-taints for more details.
"""

  parser.add_argument(
      '--node-taints',
      metavar='NODE_TAINT',
      type=arg_parsers.ArgDict(),
      help=help_text,
      hidden=hidden)


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
      help='Allow only Authorized Networks (specified by the '
      '`--master-authorized-networks` flag) and Google Compute Engine Public '
      'IPs to connect to Kubernetes master through HTTPS. By default public  '
      'internet (0.0.0.0/0) is allowed to connect to Kubernetes master through '
      'HTTPS.',
      hidden=hidden,
      action='store_true')
  group.add_argument(
      '--master-authorized-networks',
      type=arg_parsers.ArgList(min_length=1, max_length=10),
      metavar='NETWORK',
      help='The list of external networks (up to 10) that are allowed to '
      'connect to Kubernetes master through HTTPS. Specified in CIDR notation '
      '(e.g. 1.2.3.4/30). Can not be specified unless '
      '`--enable-master-authorized-networks` is also specified.',
      hidden=hidden)


def AddNetworkPolicyFlags(parser, hidden=False):
  """Adds --enable-network-policy flags to parser."""
  parser.add_argument(
      '--enable-network-policy',
      action='store_true',
      default=None,
      hidden=hidden,
      help='Enable network policy enforcement for this cluster. If you are '
      'enabling network policy on an existing cluster the network policy '
      'addon must first be enabled on the master by using '
      '--update-addons=NetworkPolicy=ENABLED flag.')


def AddEnableSharedNetworkFlag(parser, hidden=False):
  """Adds a --enable-shared-network flag to parser."""
  help_text = """\
Temporary flag allowing the cluster to be created with a shared network and
subnetwork. This requires using alias IPs with a pre-existing subnetwork and
secondary ranges. At a later release, this flag will not be necessary.

The following flags must also be provided: '--enable-kubernetes-alpha',
'--enable-ip-alias', '--subnetwork', '--services-secondary-range-name', and
'--cluster-secondary-range-name'.

The flag '--create-subnetwork' cannot be specified.
"""
  parser.add_argument(
      '--enable-shared-network',
      action='store_true',
      default=None,
      hidden=hidden,
      help=help_text)


def AddEnableLegacyAuthorizationFlag(parser, hidden=False):
  """Adds a --enable-legacy-authorization flag to parser."""
  help_text = """\
Enables the legacy ABAC authentication for the cluster.
User rights are granted through the use of policies which combine attributes
together. For a detailed look at these properties and related formats, see
https://kubernetes.io/docs/admin/authorization/abac/. To use RBAC permissions
instead, create or update your cluster with the option
`--no-enable-legacy-authorization`.
"""
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


def AddMaintenanceWindowFlag(parser, hidden=False, add_unset_text=False):
  """Adds a --maintenance-window flag to parser."""
  help_text = """\
Set a time of day when you prefer maintenance to start on this cluster. \
For example:

  $ {command} example-cluster --maintenance-window=12:43

The time corresponds to the UTC time zone, and must be in HH:MM format.
"""
  unset_text = """\
  To remove an existing maintenance window from the cluster, use \
\'--maintenance-window=None\'
"""
  description = 'Maintenance windows must be passed in using HH:MM format.'
  unset_description = ' They can also be removed by using the word \"None\".'

  if add_unset_text:
    help_text += unset_text
    description += unset_description

  type_ = arg_parsers.RegexpValidator(
      r'^([0-9]|0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$|^None$',
      description)
  parser.add_argument(
      '--maintenance-window',
      default=None,
      hidden=hidden,
      type=type_,
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
""")
  parser.add_argument(
      '--services-ipv4-cidr',
      metavar='CIDR',
      hidden=hidden,
      help="""\
Set the IP range for the services IPs.

Can be specified as a netmask size (e.g. '/20') or as in CIDR notion
(e.g. '10.100.0.0/20'). If given as a netmask size, the IP range will
be chosen automatically from the available space in the network.

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

Create a new subnetwork with a default name and size.

      $ {command} --create-subnetwork ""

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
  parser.add_argument(
      '--cluster-secondary-range-name',
      metavar='NAME',
      hidden=hidden,
      help="""\
Set the secondary range to be used as the source for pod IPs. Alias
ranges will be allocated from this secondary range.  NAME must be the
name of an existing secondary range in the cluster subnetwork.

Must be used in conjunction with '--enable-ip-alias'. Cannot be used
with --create-subnetwork.
""")
  parser.add_argument(
      '--services-secondary-range-name',
      metavar='NAME',
      hidden=hidden,
      help="""\
Set the secondary range to be used for services
(e.g. ClusterIPs). NAME must be the name of an existing secondary
range in the cluster subnetwork.

Must be used in conjunction with '--enable-ip-alias'. Cannot be used
with --create-subnetwork.
""")


def AddMinCpuPlatformFlag(parser, for_node_pool=False, hidden=False):
  """Adds the --min-cpu-platform flag to the parser.

  Args:
    parser: A given parser.
    for_node_pool: True if it's applied a non-default node pool.
    hidden: Whether or not to hide the help text.
  """
  if for_node_pool:
    help_text = """\
When specified, the nodes for the new node pool will be scheduled on host with
specified CPU architecture or a newer one.

Examples:
  $ {command} node-pool-1 --cluster=example-cluster --min-cpu-platform=PLATFORM

"""
  else:
    help_text = """\
When specified, the nodes for the new cluster's default node pool will be
scheduled on host with specified CPU architecture or a newer one.

Examples:
  $ {command} example-cluster --min-cpu-platform=PLATFORM

"""

  help_text += """\
To list available CPU platforms in given zone, run:

  $ gcloud beta compute zones describe ZONE --format="value(availableCpuPlatforms)"

CPU platform selection is available only in selected zones.
"""

  parser.add_argument(
      '--min-cpu-platform',
      metavar='PLATFORM',
      hidden=hidden,
      help=help_text)


def AddWorkloadMetadataFromNodeFlag(parser, hidden=False):
  """Adds the --workload-metadata-from-node flag to the parser.

  Args:
    parser: A given parser.
    hidden: Whether or not to hide the help text.
  """
  help_text = """\
Sets the node metadata option for workload metadata configuration.
"""

  parser.add_argument(
      '--workload-metadata-from-node',
      default=None,
      choices={
          'SECURE': 'Exposes only a secure subset of metadata to workloads. '
                    'Currently, this blocks kube-env and instance identity, '
                    'but exposes all other metadata.',
          'EXPOSED': 'Exposes all metadata to workloads.',
          'UNSPECIFIED': 'Chooses the default.',
      },
      type=lambda x: x.upper(),
      hidden=hidden,
      help=help_text)


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


def AddNodeLocationsFlag(parser):
  parser.add_argument(
      '--node-locations',
      type=arg_parsers.ArgList(min_length=1),
      metavar='ZONE',
      help="""\
The set of zones in which the specified node footprint should be replicated.
All zones must be in the same region as the cluster's primary zone, specified by
the --zone flag. --node-locations must contain the primary zone.
If node-locations is not specified, all nodes will be in the primary zone.

Note that `NUM_NODES` nodes will be created in each zone, such that if you
specify `--num-nodes=4` and choose two locations, 8 nodes will be created.

Multiple locations can be specified, separated by commas. For example:

  $ {command} example-cluster --zone us-central1-a --node-locations us-central1-a,us-central1-b
""")


def AddLoggingServiceFlag(parser, hidden=False):
  """Adds a --logging-service flag to the parser.

  Args:
    parser: A given parser.
    hidden: Whether or not to hide the help text.
  """

  parser.add_argument(
      '--logging-service',
      hidden=hidden,
      help='The logging service to use for the cluster. Options are: '
      '"logging.googleapis.com" (the Google Cloud Logging service), '
      '"none" (logs will not be exported from the cluster)')


def AddScopesFlag(parser, example_target, is_deprecated):
  min_args_length = 1 if is_deprecated else 0
  default = [] if is_deprecated else ['logging-write', 'monitoring']
  parser.add_argument(
      '--scopes',
      type=arg_parsers.ArgList(min_length=min_args_length),
      metavar='SCOPE',
      default=default,
      help="""\
Specifies scopes for the node instances. The project's default
service account is used. Examples:

  $ {{command}} {example_target} --scopes https://www.googleapis.com/auth/devstorage.read_only

  $ {{command}} {example_target} --scopes bigquery,storage-rw,compute-ro

Multiple SCOPEs can specified, separated by commas. The scopes
necessary for the cluster to function properly (compute-rw, storage-ro),
are always added, even if not explicitly specified.

SCOPE can be either the full URI of the scope or an alias.
Available aliases are:

[format="csv",options="header"]
|========
Alias,URI
{aliases}
|========

{scope_deprecation_msg}
""".format(
    aliases=compute_constants.ScopesForHelp(),
    scope_deprecation_msg=compute_constants.DEPRECATED_SCOPES_MESSAGES,
    example_target=example_target))


def AddClusterScopesFlag(parser):
  AddScopesFlag(parser, example_target='example-cluster', is_deprecated=False)


def AddOldClusterScopesFlag(parser):
  AddScopesFlag(parser, example_target='example-cluster', is_deprecated=True)


def AddNodePoolScopesFlag(parser):
  AddScopesFlag(parser, example_target='node-pool-1 --cluster=example-cluster',
                is_deprecated=False)


def AddOldNodePoolScopesFlag(parser):
  AddScopesFlag(parser, example_target='node-pool-1 --cluster=example-cluster',
                is_deprecated=True)


def AddAddonsFlags(
    parser, hide_addons_flag=False, deprecate_disable_addons_flag=True):
  """Adds the --addons and --disable-addons flags to the parser."""
  group = parser.add_mutually_exclusive_group()
  group.add_argument(
      '--addons',
      type=arg_parsers.ArgList(
          choices=api_adapter.ADDONS_OPTIONS),
      metavar='ADDON',
      hidden=hide_addons_flag,
      # TODO(b/65264376): Replace the doc link when a better doc is ready.
      help="""\
Default set of addons includes {0}. Addons
(https://cloud.google.com/container-engine/reference/rest/v1/projects.zones.clusters#AddonsConfig)
are additional Kubernetes cluster components. Addons specified by this flag will
be enabled. The others will be disabled.
""".format(', '.join(api_adapter.DEFAULT_ADDONS)))
  action = None
  if deprecate_disable_addons_flag:
    action = actions.DeprecationAction(
        'disable-addons',
        warn='This flag is deprecated. '
        'Use --addons instead.')
  group.add_argument(
      '--disable-addons',
      type=arg_parsers.ArgList(
          choices=api_adapter.ADDONS_OPTIONS),
      metavar='DISABLE_ADDON',
      action=action,
      help='List of cluster addons to disable. Options are {0}'.format(
          ', '.join(api_adapter.ADDONS_OPTIONS)))
