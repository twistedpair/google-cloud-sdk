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


"""Common flags for some of the AlloyDB commands.

Flags are specified with functions that take in a single argument, the parser,
and add the newly constructed flag to that parser.

Example:

def AddFlagName(parser):
  parser.add_argument(
    '--flag-name',
    ... // Other flag details.
  )
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


def AddAssignIp(parser):
  """Adds an --assign-ip flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--assign-ip',
      required=False,
      help='Assign a public IP address to the instance. This is a public, '
      'externally available IPv4 address that you can use to connect to your '
      'instance when properly authorized. Use `--assign-ip` to enable a public '
      'IP and `--no-assign-ip` to disable it.',
      action=arg_parsers.StoreTrueFalseAction)


def AddAvailabilityType(parser):
  """Adds an '--availability-type' flag to the parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--availability-type',
      required=False,
      choices={
          'REGIONAL': 'Provides high availability and is recommended for '
                      'production instances; instance automatically fails over '
                      'to another zone within your selected region.',
          'ZONAL': 'Provides no failover capability. This is the default.'
      },
      help='Specifies level of availability.')


def AddCluster(parser, positional=True):
  """Adds a positional cluster argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    positional: whether or not --cluster is positional.
  """
  if positional:
    parser.add_argument(
        'cluster',
        type=str,
        help='AlloyDB cluster ID')
  else:
    parser.add_argument(
        '--cluster',
        required=True,
        type=str,
        help='AlloyDB cluster ID')


def AddCPU(parser):
  """Adds a --cpu flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--cpu',
      required=False,
      type=int,
      help=('Whole number value indicating how many cores are desired in '
            'the machine. Both `--cpu` and `--memory` must be specified if a '
            'custom machine type is desired, and the `--tier` flag must be '
            'omitted.'))


def AddDatabaseFlags(parser, update=False):
  """Adds a `--database-flags` flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    update: Whether or not database flags were provided as part of an update.
  """
  help_ = ('Comma-separated list of database flags to set on the '
           'instance. Use an equals sign to separate flag name and value. '
           'Flags without values, like skip_grant_tables, can be written '
           'out without a value after, e.g., `skip_grant_tables=`. Use '
           'on/off for booleans. View the Instance Resource API for allowed '
           'flags. (e.g., `--database-flags max_allowed_packet=55555,'
           'skip_grant_tables=,log_output=1`)')
  if update:
    help_ += (
        '\n\nThe value given for this argument *replaces* the existing list.')
  parser.add_argument(
      '--database-flags',
      type=arg_parsers.ArgDict(min_length=1),
      metavar='FLAG=VALUE',
      required=False,
      help=help_)


def AddInstance(parser):
  """Adds a positional instance argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      'instance',
      type=str,
      help='AlloyDB instance ID')


def AddInstanceType(parser, required=True):
  """Adds an --instance-type flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --instance-type is required.
  """
  parser.add_argument(
      '--instance-type',
      type=str,
      required=required,
      choices={
          'PRIMARY': 'PRIMARY instances support read and write operations.',
          'READ': 'READ instances support read operations only. Each read '
                  'instance consists of one or more homogeneous read replicas. '
                  'READ Instances of size 1 can only have zonal availability. '
                  'READ instances with replica count of 2 or more can have '
                  'regional availability (replicas are present in 2 or more '
                  'zones in a region).'
      },
      help='Specifies instance type.')


def AddOperation(parser):
  """Adds a positional operation argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      'operation',
      type=str,
      help='AlloyDB operation ID')


def AddMemory(parser):
  """Adds a --memory flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--memory',
      required=False,
      type=arg_parsers.BinarySize(),
      help=('Whole number value indicating how much memory is desired in '
            'the machine. A size unit should be provided (eg. 3072MiB or '
            '9GiB) - if no units are specified, GiB is assumed. Both `--cpu` '
            'and `--memory` must be specified if a custom machine type is '
            'desired, and the `--tier` flag must be omitted.'))


def AddNetwork(parser):
  """Adds the `--network` flag to the parser."""
  parser.add_argument(
      '--network',
      required=False,
      type=str,
      help=('Network in the current project that the instance will be part '
            'of. To specify using a network with a shared VPC, use the full '
            'URL of the network. For an example host project, \'testproject\', '
            'and shared network, \'testsharednetwork\', this would be of the '
            'form:'
            '`--network`=`projects/testproject/global/networks/'
            'testsharednetwork`'))


def AddReadPoolSize(parser):
  """Adds a --read-pool-size flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--read-pool-size',
      required=False,
      type=int,
      help='Read pool size.')


def AddRegion(parser, required=True):
  """Adds a --region flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --region is required.
  """
  parser.add_argument(
      '--region',
      required=required,
      type=str,
      help='Regional location (e.g. asia-east1, us-east1). See the full '
            'list of regions at '
            'https://cloud.google.com/sql/docs/instance-locations.')


def AddTier(parser):
  """Adds a '--tier' flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--tier',
      required=False,
      type=str,
      help=(
          'The tier for this instance. The following tiers are available for '
          'AlloyDB instances: n2-highmem-8, n2-highmem-16, and n2-highmem-32.'))


def AddZone(parser):
  """Adds a --zone flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--zone',
      required=False,
      type=str,
      help=('Primary Compute Engine zone '
            '(e.g. us-central1, us-central1, etc.'))


def AddForce(parser):
  """Adds a --force flag to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--force',
      required=False,
      action='store_true',
      help=('Default value is false.'
            '\n\nIf flag is specified, deletes instances (if any) within this '
            'cluster, before deleting the cluster.'
            '\n\nIf flag is not specified, cluster delete will fail if there '
            'are instances present in the cluster.'))
