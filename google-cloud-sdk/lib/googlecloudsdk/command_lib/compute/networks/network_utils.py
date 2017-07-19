# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Code that's shared between multiple networks subcommands."""

from googlecloudsdk.calliope import exceptions as exceptions
from googlecloudsdk.calliope import parser_errors


class CancelledException(exceptions.ToolException):
  """Exception raised when a networks command is cancelled by the user."""


_RANGE_NON_LEGACY_MODE_ERROR = (
    '--range can only be used with --subnet-mode=LEGACY.')


_BGP_ROUTING_MODE_CHOICES = {
    'GLOBAL': 'Cloud Routers in this network advertise subnetworks from all '
              'regions to their BGP peers, and program instances in their '
              'region with the best learned BGP routes from all regions. ',
    'REGIONAL': 'Cloud Routers in this network advertise subnetworks from '
                'their local region only to their BGP peers, and program '
                'instances in their region with the best learned BGP routes '
                'from their local region only.',
}


_CREATE_SUBNET_MODE_CHOICES = {
    'AUTO': 'Subnets are created automatically.  This is the recommended '
            'selection.',
    'CUSTOM': 'Create subnets manually.',
    'LEGACY': 'Create an old style network that has a range and cannot have '
              'subnets.'
}


_UPDATE_SUBNET_MODE_CHOICES = {
    'CUSTOM': 'Create subnets manually.',
}


def AddCreateArgs(parser):
  """Adds common arguments for creating a network."""

  parser.add_argument(
      '--description',
      help='An optional, textual description for the network.')

  parser.add_argument(
      '--mode',
      metavar='NETWORK_TYPE',
      choices={
          'auto': (
              'Subnets are created automatically. This is the recommended '
              'selection.'),
          'custom': 'Create subnets manually.',
          'legacy': (
              'Create an old style network that has a range and cannot have '
              'subnets.'),
      },
      required=False,
      help='The network type.')

  parser.add_argument(
      '--range',
      help="""\
      Specifies the IPv4 address range of legacy mode networks. The range
      must be specified in CIDR format:
      [](http://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing)

      This flag only works if mode is
      [legacy](https://cloud.google.com/compute/docs/vpc/legacy).

      Using legacy networks is **not recommended**, given that many newer Google
      Cloud Platform features are not supported on legacy networks. Please be
      advised that legacy networks may not be supported in the future.
      """)


def AddCreateAlphaArgs(parser):
  """Adds alpha-specific arguments for creating a network."""

  parser.add_argument(
      '--description',
      help='An optional, textual description for the network.')

  parser.add_argument(
      '--subnet-mode',
      choices=_CREATE_SUBNET_MODE_CHOICES,
      default='AUTO',
      type=lambda mode: mode.upper(),
      metavar='MODE',
      help="""The subnet mode of the network. If not specified, defaults to
              AUTO.""")

  parser.add_argument(
      '--bgp-routing-mode',
      choices=_BGP_ROUTING_MODE_CHOICES,
      type=lambda mode: mode.upper(),
      metavar='MODE',
      help="""The BGP routing mode for this network. If not specified, defaults
              to REGIONAL.""")

  parser.add_argument(
      '--range',
      help="""\
      Specifies the IPv4 address range of legacy mode networks. The range
      must be specified in CIDR format:
      [](http://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing)

      This flag only works if subnet-mode is LEGACY.
      """)


def AddUpdateAlphaArgs(parser):
  """Adds alpha-specific arguments for updating a network."""

  mode_args = parser.add_mutually_exclusive_group(required=False)

  mode_args.add_argument(
      '--switch-to-custom-subnet-mode',
      action='store_true',
      help="""Switch to custom subnet mode. This action cannot be undone.""")

  mode_args.add_argument(
      '--bgp-routing-mode',
      choices=_BGP_ROUTING_MODE_CHOICES,
      type=lambda mode: mode.upper(),
      metavar='MODE',
      help="""The target BGP routing mode for this network.""")


def CheckRangeLegacyModeOrRaise(args):
  """Checks for range being used with incompatible mode and raises an error."""
  if args.range is not None and args.subnet_mode != 'LEGACY':
    raise parser_errors.ArgumentError(_RANGE_NON_LEGACY_MODE_ERROR)
