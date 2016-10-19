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

"""Flags and helpers for the compute forwarding-rules commands."""

import textwrap

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import flags
from googlecloudsdk.core import properties


FORWARDING_RULES_OVERVIEW = """\
        Forwarding rules match and direct certain types of traffic to a load
        balancer which is controlled by a target pool, a target instance,
        or a target HTTP proxy. Target pools and target instances perform load
        balancing at the layer 3 of the OSI networking model
        (http://en.wikipedia.org/wiki/Network_layer). Target
        HTTP proxies perform load balancing at layer 7.

        Forwarding rules can be either regional or global. They are
        regional if they point to a target pool or a target instance
        and global if they point to a target HTTP proxy.

        For more information on load balancing, see
        https://cloud.google.com/compute/docs/load-balancing-and-autoscaling/.
        """


def AddCommonFlags(parser):
  """Adds common flags for mutating forwarding rules."""
  scope = parser.add_mutually_exclusive_group()

  flags.AddRegionFlag(
      scope,
      resource_type='forwarding rule',
      operation_type='operate on')

  global_flag = scope.add_argument(
      '--global',
      action='store_true',
      help='If provided, it is assumed the forwarding rules are global.')
  global_flag.detailed_help = """\
      If provided, assume the forwarding rules are global. A forwarding rule
      is global if it references a target HTTP proxy.
      """


def AddUpdateArgs(parser, include_beta):
  """Adds common flags for mutating forwarding rule targets."""

  target = parser.add_mutually_exclusive_group(required=True)

  target_instance = target.add_argument(
      '--target-instance',
      help='The target instance that will receive the traffic.')
  target_instance.detailed_help = textwrap.dedent("""\
      The name of the target instance that will receive the traffic. The
      target instance must be in a zone that's in the forwarding rule's
      region. Global forwarding rules may not direct traffic to target
      instances.
      """) + flags.ZONE_PROPERTY_EXPLANATION

  target_pool = target.add_argument(
      '--target-pool',
      help='The target pool that will receive the traffic.')
  target_pool.detailed_help = """\
      The target pool that will receive the traffic. The target pool
      must be in the same region as the forwarding rule. Global
      forwarding rules may not direct traffic to target pools.
      """

  target.add_argument(
      '--target-http-proxy',
      help='The target HTTP proxy that will receive the traffic.')

  target.add_argument(
      '--target-https-proxy',
      help='The target HTTPS proxy that will receive the traffic.')

  target.add_argument(
      '--target-ssl-proxy',
      help='The target SSL proxy that will receive the traffic.')

  # There are no beta target right now. Move alpha targets to here when they
  # turn to beta.
  if include_beta:
    target.add_argument(
        '--backend-service',
        help='The target backend service that will receive the traffic.')

    parser.add_argument(
        '--load-balancing-scheme',
        choices={
            'EXTERNAL': 'Used for HTTP or HTTPS for External Load Balancing.',
            'INTERNAL': 'Used for Internal Network Load Balancing.',
        },
        type=lambda x: x.upper(),
        default='EXTERNAL',
        help='This signifies what the forwarding rule will be used for.')

    parser.add_argument(
        '--subnet',
        help='(Only for Internal Load Balancing) '
             'The subnetwork that this forwarding rule applies to. '
             'If the network configured for this forwarding rule is in '
             'auto subnet mode, the subnetwork is optional. However, if '
             'the network is in custom subnet mode, a subnetwork must be '
             'specified.')

    parser.add_argument(
        '--network',
        help='(Only for Internal Load Balancing) '
             'The network that this forwarding rule applies to. If this field '
             'is not specified, the default network will be used. In the '
             'absence of the default network, this field must be specified.')

  target.add_argument(
      '--target-vpn-gateway',
      help='The target VPN gateway that will receive forwarded traffic.')

  parser.add_argument(
      '--target-instance-zone',
      help='The zone of the target instance.',
      action=actions.StoreProperty(properties.VALUES.compute.zone))

  parser.add_argument(
      'name',
      help='The name of the forwarding rule.')


def AddAddress(parser):
  """Adds IP address flag."""

  address = parser.add_argument(
      '--address',
      help='The external IP address that the forwarding rule will serve.')
  address.detailed_help = """\
      The external IP address that the forwarding rule will
      serve. All traffic sent to this IP address is directed to the
      target pointed to by the forwarding rule. If the address is
      reserved, it must either (1) reside in the global scope if the
      forwarding rule is being configured to point to a target HTTP
      proxy or (2) reside in the same region as the forwarding rule
      if the forwarding rule is being configured to point to a
      target pool or target instance. If this flag is omitted, an
      ephemeral IP address is assigned.
      """


def AddIPProtocols(parser, include_alpha=False):
  """Adds IP protocols flag, with values available in the given version."""

  protocols = ['AH', 'ESP']
  if include_alpha:
    # ICMP is only supported in Alpha.
    protocols.append('ICMP')
  protocols.extend(['SCTP', 'TCP', 'UDP'])

  parser.add_argument(
      '--ip-protocol',
      choices=protocols,
      type=lambda x: x.upper(),
      help='The IP protocol that the rule will serve. The default is TCP.')


def AddDescription(parser):
  """Adds description flag."""

  parser.add_argument(
      '--description',
      help='An optional textual description for the forwarding rule.')


def AddPortsAndPortRange(parser):
  """Adds ports and port range flags."""

  ports_scope = parser.add_mutually_exclusive_group()
  ports = ports_scope.add_argument(
      '--ports',
      metavar='[PORT | PORT-PORT]',
      help=('If specified, only packets addressed to the ports or '
            'port ranges will be forwarded.'),
      type=arg_parsers.ArgList(
          min_length=1, element_type=arg_parsers.Range.Parse),
      default=[])
  ports.detailed_help = """\
          If specified, only packets addressed to ports in the specified
          list will be forwarded. If not specified for regional forwarding
          rules, all ports are matched. This flag is required for global
          forwarding rules and accepts a single continuous set of ports.

          Individual ports and ranges can be specified,
          for example (`--ports 8000-8004` or `--ports 80`).
          """

  port_range = ports_scope.add_argument(
      '--port-range',
      type=arg_parsers.Range.Parse,
      help='DEPRECATED, use --ports. If specified, only packets addressed to '
           'the port or ports in the specified range will be forwarded.',
      metavar='[PORT | PORT-PORT]')
  port_range.detailed_help = """\
      DEPRECATED, use --ports. If specified, only packets addressed to ports in
      the specified range will be forwarded. If not specified for regional
      forwarding rules, all ports are matched. This flag is required for global
      forwarding rules.

      Either an individual port (`--port-range 80`) or a range of ports
      (`--port-range 3000-3100`) may be specified.
      """
