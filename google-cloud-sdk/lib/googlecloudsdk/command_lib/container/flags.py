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
from googlecloudsdk.core import properties


# TODO(b/28318474): move flags common across commands here.
def AddImageTypeFlag(parser, target, suppressed):
  """Adds a --image-type flag to the given parser."""
  help_text = argparse.SUPPRESS if suppressed else """\
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


def AddClusterAutoscalingFlags(parser, exclusive_group=None):
  """Adds autoscaling related flags to parser.

  Autoscaling related flags are: --enable-autoscaling
  --min-nodes --max-nodes flags.

  Args:
    parser: A given parser.
    exclusive_group: An optional group of mutually exclusive flag options
        to which an --enable-autoscaling flag is added.
  """
  # TODO(user): Add a help texts here.

  group = parser.add_argument_group('Cluster autoscaling')
  autoscaling_group = group if exclusive_group is None else exclusive_group
  autoscaling_group.add_argument(
      '--enable-autoscaling',
      help=argparse.SUPPRESS,
      action='store_true')
  group.add_argument(
      '--max-nodes',
      help=argparse.SUPPRESS,
      type=int)
  group.add_argument(
      '--min-nodes',
      help=argparse.SUPPRESS,
      type=int)


def AddZoneFlag(parser):
  """Adds the --zone flag to the parser."""
  parser.add_argument(
      '--zone', '-z',
      help='The compute zone (e.g. us-central1-a) for the cluster',
      action=actions.StoreProperty(properties.VALUES.compute.zone))
