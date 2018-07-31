# -*- coding: utf-8 -*- #
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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
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


def AddUpdateArgs(parser, include_alpha=False):
  """Add args to the parser for subnet update.

  Args:
    parser: The argparse parser.
    include_alpha: Include alpha functionality.
  """
  updated_field = parser.add_mutually_exclusive_group()

  updated_field.add_argument(
      '--enable-private-ip-google-access',
      action=arg_parsers.StoreTrueFalseAction,
      help=('Enable/disable access to Google Cloud APIs from this subnet for '
            'instances without a public ip address.'))

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

  updated_field.add_argument(
      '--enable-flow-logs',
      action=arg_parsers.StoreTrueFalseAction,
      help=('Enable/disable VPC flow logging for this subnet. More information '
            'for VPC flow logs can be found at '
            'https://cloud.google.com/vpc/docs/using-flow-logs.'))

  if include_alpha:
    updated_field.add_argument(
        '--role',
        choices={'ACTIVE': 'The ACTIVE subnet that is currently used.'},
        type=lambda x: x.replace('-', '_').upper(),
        help=('The role is set to ACTIVE to update a BACKUP reserved '
              'address range to\nbe the new ACTIVE address range. Note '
              'that the only supported value for\nthis flag is ACTIVE since '
              'setting an address range to BACKUP is not\nsupported. '
              '\n\nThis field is only valid when updating a reserved IP '
              'address range used\nfor the purpose of Internal HTTP(S) Load '
              'Balancer.'))

    parser.add_argument(
        '--drain-timeout',
        type=arg_parsers.Duration(lower_bound='0s'),
        default='0s',
        help="""\
        The drain timeout specifies the upper bound in seconds on the amount of
        time allowed to drain connections from the current ACTIVE subnetwork to
        the current BACKUP subnetwork. The drain timeout is only applicable when
        the [--set-role-active] flag is being used.
        """)

    aggregation_interval_argument = base.ChoiceArgument(
        '--aggregation-interval',
        choices=[
            'interval-5-sec', 'interval-30-sec', 'interval-1-min',
            'interval-5-min', 'interval-10-min', 'interval-15-min'
        ],
        help_str="""\
        Can only be specified if VPC flow logging for this subnetwork is
        enabled. Toggles the aggregation interval for collecting flow logs.
        Increasing the interval time will reduce the amount of generated flow
        logs for long lasting connections. Default is an interval of 5 seconds
        per connection.
        """)
    aggregation_interval_argument.AddToParser(parser)

    parser.add_argument(
        '--flow-sampling',
        type=arg_parsers.BoundedFloat(lower_bound=0.0, upper_bound=1.0),
        help="""\
        Can only be specified if VPC flow logging for this subnetwork is
        enabled. The value of the field must be in [0, 1]. Set the sampling rate
        of VPC flow logs within the subnetwork where 1.0 means all collected
        logs are reported and 0.0 means no logs are reported. Default is 0.5
        which means half of all collected logs are reported.
        """)

    metadata_argument = base.ChoiceArgument(
        '--metadata',
        choices=['include-all-metadata', 'exclude-all-metadata'],
        help_str="""\
        Can only be specified if VPC flow logging for this subnetwork is
        enabled. Configures whether metadata fields should be added to the
        reported VPC flow logs. Default is to include all metadata.
        """)
    metadata_argument.AddToParser(parser)
