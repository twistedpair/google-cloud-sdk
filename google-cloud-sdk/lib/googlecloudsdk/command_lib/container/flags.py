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


def AddClusterVersionFlag(parser, target, suppressed=False):
  """Adds a --cluster-version flag to the given parser."""
  help_text = argparse.SUPPRESS if suppressed else """\
The Kubernetes version to use for the {target}. Defaults to server-specified.

The default Kubernetes version are available using the following command.

  $ gcloud container get-server-config
""".format(target=target)

  return parser.add_argument('--cluster-version', help=help_text)


def AddClusterAutoscalingFlags(parser, exclusive_group=None, suppressed=False):
  """Adds autoscaling related flags to parser.

  Autoscaling related flags are: --enable-autoscaling
  --min-nodes --max-nodes flags.

  Args:
    parser: A given parser.
    exclusive_group: An optional group of mutually exclusive flag options
        to which an --enable-autoscaling flag is added.
    suppressed: If true, supress help text for added options.
  """

  hide_or = lambda x: argparse.SUPPRESS if suppressed else x

  group = parser.add_argument_group('Cluster autoscaling')
  autoscaling_group = group if exclusive_group is None else exclusive_group
  autoscaling_group.add_argument(
      '--enable-autoscaling',
      help=hide_or("""\
Enables autoscaling for a node pool.

Enables autoscaling in the node pool specified by --node-pool or the
default node pool if --node-pool is not provided."""),
      action='store_true')
  group.add_argument(
      '--max-nodes',
      help=hide_or("""\
Maximum number of nodes in the node pool.

Maximum number of nodes to which the node pool specified by --node-pool
(or default node pool if unspecified) can scale. Ignored unless
--enable-autoscaling is also specified."""),
      type=int)
  group.add_argument(
      '--min-nodes',
      help=hide_or("""\
Minimum number of nodes in the node pool.

Minimum number of nodes to which the node pool specified by --node-pool
(or default node pool if unspecified) can scale. Ignored unless
--enable-autoscaling is also specified."""),
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


def AddNodeLabelsFlag(parser, suppressed=True, for_node_pool=False):
  """Adds a --node-labels flag to the given parser."""
  if suppressed:
    help_text = argparse.SUPPRESS
  else:
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
