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

"""Flags and helpers for the compute subnetworks commands."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute import scope as compute_scope

DEFAULT_LIST_FORMAT = """\
    table(
      name,
      region.basename(),
      network.basename(),
      ipCidrRange:label=RANGE
    )"""


class SubnetworksCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(SubnetworksCompleter, self).__init__(
        collection='compute.subnetworks',
        list_command='beta compute networks subnets list --uri',
        api_version='beta',
        **kwargs)


def SubnetworkArgument(required=True, plural=False):
  return compute_flags.ResourceArgument(
      resource_name='subnetwork',
      completer=SubnetworksCompleter,
      plural=plural,
      required=required,
      regional_collection='compute.subnetworks',
      region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION)


def SubnetworkResolver():
  return compute_flags.ResourceResolver.FromMap(
      'subnetwork', {compute_scope.ScopeEnum.REGION: 'compute.subnetworks'})


def AddUpdateArgs(parser,
                  include_secondary_ranges=False,
                  include_enable_flow_logs=False):
  """Add args to the parser for subnet update.

  Args:
    parser: The argparse parser.
    include_secondary_ranges: Whether to include the --add-secondary-ranges and
      --remove-secondary-ranges flags.
    include_enable_flow_logs: Whether to include the --enable-flow-logs flag.
  """
  updated_field = parser.add_mutually_exclusive_group()

  updated_field.add_argument(
      '--enable-private-ip-google-access',
      action=arg_parsers.StoreTrueFalseAction,
      help=('Enable/disable access to Google Cloud APIs from this subnet for '
            'instances without a public ip address.'))

  if include_secondary_ranges:
    updated_field.add_argument(
        '--add-secondary-ranges',
        type=arg_parsers.ArgDict(min_length=1),
        action='append',
        metavar='PROPERTY=VALUE',
        help="""\
        Adds secondary IP ranges to the subnetwork for use in IP aliasing.

        For example, `--add-secondary-ranges range1=192.168.64.0/24` adds
        a secondary range 192.168.64.0/24 with name range1.

        * `RANGE_NAME` - Name of the secondary range.
        * `RANGE` - `IP range in CIDR format.`
        """)

    updated_field.add_argument(
        '--remove-secondary-ranges',
        type=arg_parsers.ArgList(min_length=1),
        action='append',
        metavar='PROPERTY=VALUE',
        help="""\
        Removes secondary ranges from the subnetwork.

        For example, `--remove-secondary-ranges range2,range3` removes the
        secondary ranges with names range2 and range3.
        """)

  if include_enable_flow_logs:
    updated_field.add_argument(
        '--enable-flow-logs',
        action=arg_parsers.StoreTrueFalseAction,
        help=('Enable/disable flow logging for this subnet.'))
