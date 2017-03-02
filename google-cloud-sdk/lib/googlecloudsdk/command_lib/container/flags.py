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

The default Kubernetes version are available using the following command.

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
Disables autoscaling for a node pool.

Disables autoscaling in the node pool specified by --node-pool or
the default node pool if --node-pool is not provided.""",
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


def AddZoneFlag(parser):
  # TODO(b/33343238): Remove the short form of the zone flag.
  # TODO(b/18105938): Add zone prompting
  """Adds the --zone flag to the parser."""
  parser.add_argument(
      '--zone', '-z',
      help='The compute zone (e.g. us-central1-a) for the cluster',
      action=actions.StoreProperty(properties.VALUES.compute.zone))


def GetAsyncValueFromAsyncAndWaitFlags(async, wait):
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
See https://cloud.google.com/container-engine/docs/node-managament for \
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

