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

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import flags as compute_flags


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


def ForwardingRuleArgument(required=True):
  return compute_flags.ResourceArgument(
      resource_name='forwarding rule',
      completion_resource_id='compute.forwardingRules',
      required=required,
      regional_collection='compute.forwardingRules',
      global_collection='compute.globalForwardingRules',
      region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION)


def ForwardingRuleArgumentPlural(required=True):
  return compute_flags.ResourceArgument(
      resource_name='forwarding rule',
      completion_resource_id='compute.forwardingRules',
      plural=True,
      required=required,
      regional_collection='compute.forwardingRules',
      global_collection='compute.globalForwardingRules',
      region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION)


BACKEND_SERVICE_ARG = compute_flags.ResourceArgument(
    name='--backend-service',
    required=False,
    resource_name='backend service',
    regional_collection='compute.regionBackendServices',
    global_collection='compute.targetBackendServices',
    short_help='The target backend service that will receive the traffic.',
    region_explanation=('If not specified it will be set the'
                        ' region of the forwarding rule.'))

NETWORK_ARG = compute_flags.ResourceArgument(
    name='--network',
    required=False,
    resource_name='networks',
    global_collection='compute.networks',
    short_help='The network that this forwarding rule applies to.',
    detailed_help="""\
        (Only for Internal Load Balancing) The network that this forwarding
        rule applies to. If this field is not specified, the default network
        will be used. In the absence of the default network, this field must
        be specified.
        """)

SUBNET_ARG = compute_flags.ResourceArgument(
    name='--subnet',
    required=False,
    resource_name='subnetwork',
    regional_collection='compute.subnetworks',
    short_help='The subnet that this forwarding rule applies to.',
    detailed_help="""\
        (Only for Internal Load Balancing) The subnetwork that this forwarding
        rule applies to. If the network configured for this forwarding rule is
        in auto subnet mode, the subnetwork is optional. However, if the
        network is in custom subnet mode, a subnetwork must be specified.
        """,
    region_explanation=('If not specified it will be set the'
                        ' region of the forwarding rule.'))

TARGET_HTTP_PROXY_ARG = compute_flags.ResourceArgument(
    name='--target-http-proxy',
    required=False,
    resource_name='http proxy',
    global_collection='compute.targetHttpProxies',
    short_help='The target HTTP proxy that will receive the traffic.')

TARGET_HTTPS_PROXY_ARG = compute_flags.ResourceArgument(
    name='--target-https-proxy',
    required=False,
    resource_name='https proxy',
    global_collection='compute.targetHttpsProxies',
    short_help='The target HTTPS proxy that will receive the traffic.')

TARGET_INSTANCE_ARG = compute_flags.ResourceArgument(
    name='--target-instance',
    required=False,
    resource_name='target instance',
    zonal_collection='compute.targetInstances',
    short_help='The name of the target instance that will receive the traffic.',
    detailed_help=textwrap.dedent("""\
      The name of the target instance that will receive the traffic. The
      target instance must be in a zone that's in the forwarding rule's
      region. Global forwarding rules may not direct traffic to target
      instances.
      """) + compute_flags.ZONE_PROPERTY_EXPLANATION)

TARGET_POOL_ARG = compute_flags.ResourceArgument(
    name='--target-pool',
    required=False,
    resource_name='target pool',
    regional_collection='compute.targetPools',
    short_help='The target pool that will receive the traffic.',
    detailed_help="""\
      The target pool that will receive the traffic. The target pool
      must be in the same region as the forwarding rule. Global
      forwarding rules may not direct traffic to target pools.
      """,
    region_explanation=('If not specified it will be set the'
                        ' region of the forwarding rule.'))

TARGET_SSL_PROXY_ARG = compute_flags.ResourceArgument(
    name='--target-ssl-proxy',
    required=False,
    resource_name='ssl proxy',
    global_collection='compute.targetSslProxies',
    short_help='The target SSL proxy that will receive the traffic.')

TARGET_TCP_PROXY_ARG = compute_flags.ResourceArgument(
    name='--target-tcp-proxy',
    required=False,
    resource_name='tcp proxy',
    global_collection='compute.targetTcpProxies',
    short_help='The target TCP proxy that will receive the traffic.')

TARGET_VPN_GATEWAY_ARG = compute_flags.ResourceArgument(
    name='--target-vpn-gateway',
    required=False,
    resource_name='VPN gateway',
    regional_collection='compute.targetVpnGateways',
    short_help='The target VPN gateway that will receive forwarded traffic.',
    region_explanation=('If not specified it will be set the'
                        ' region of the forwarding rule.'))


ADDRESS_ARG = compute_flags.ResourceArgument(
    name='--address',
    required=False,
    resource_name='address',
    completion_resource_id='compute.addresses',
    regional_collection='compute.addresses',
    global_collection='compute.globalAddresses',
    region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION,
    short_help='The external IP address that the forwarding rule will serve.',
    detailed_help="""\
      The external IP address that the forwarding rule will serve. All
      traffic sent to this IP address is directed to the target
      pointed to by the forwarding rule. Assigned IP addresses can be
      reserved or unreserved.

      If the address is reserved, it must either (1) reside in the global scope
      if the forwarding rule is being configured to point to an external load
      balancer or (2) reside in the same region as the forwarding rule
      if the forwarding rule is being configured to point to a
      target pool or target instance. If this flag is omitted, an
      ephemeral IP address is assigned.

      Note: An IP address must be specified if the traffic is being forwarded to
      a VPN.
      """)


def AddUpdateArgs(parser, include_beta=False, include_alpha=False):
  """Adds common flags for mutating forwarding rule targets."""
  del include_alpha
  del include_beta
  target = parser.add_mutually_exclusive_group(required=True)

  TARGET_HTTP_PROXY_ARG.AddArgument(parser, mutex_group=target)
  TARGET_HTTPS_PROXY_ARG.AddArgument(parser, mutex_group=target)
  TARGET_INSTANCE_ARG.AddArgument(parser, mutex_group=target)
  TARGET_POOL_ARG.AddArgument(parser, mutex_group=target)
  TARGET_SSL_PROXY_ARG.AddArgument(parser, mutex_group=target)
  TARGET_TCP_PROXY_ARG.AddArgument(parser, mutex_group=target)
  TARGET_VPN_GATEWAY_ARG.AddArgument(parser, mutex_group=target)

  BACKEND_SERVICE_ARG.AddArgument(parser, mutex_group=target)
  NETWORK_ARG.AddArgument(parser)
  SUBNET_ARG.AddArgument(parser)

  parser.add_argument(
      '--load-balancing-scheme',
      choices={
          'EXTERNAL': 'Used for HTTP or HTTPS for External Load Balancing.',
          'INTERNAL': 'Used for Internal Network Load Balancing.',
      },
      type=lambda x: x.upper(),
      default='EXTERNAL',
      help='This signifies what the forwarding rule will be used for.')


def AddIPProtocols(parser):
  """Adds IP protocols flag, with values available in the given version."""

  protocols = ['AH', 'ESP', 'ICMP', 'SCTP', 'TCP', 'UDP']

  parser.add_argument(
      '--ip-protocol',
      choices=protocols,
      type=lambda x: x.upper(),
      help='The IP protocol that the rule will serve. The default is TCP.')


def AddIpVersionGroup(parser):
  """Adds IP versions flag in a mutually exclusive group."""
  parser.add_argument(
      '--ip-version',
      choices=['IPV4', 'IPV6'],
      type=lambda x: x.upper(),
      help="""\
      The version of the IP address to be allocated if no --address is given.
      The default is IPv4.
      """)


def AddAddressesAndIPVersions(parser, required=True):
  """Adds Addresses and IP versions flag."""
  group = parser.add_mutually_exclusive_group(required=required)
  AddIpVersionGroup(group)
  ADDRESS_ARG.AddArgument(parser, mutex_group=group)


def AddDescription(parser):
  """Adds description flag."""

  parser.add_argument(
      '--description',
      help='An optional textual description for the forwarding rule.')


def AddPortsAndPortRange(parser):
  """Adds ports and port range flags."""

  ports_scope = parser.add_mutually_exclusive_group()
  ports_scope.add_argument(
      '--ports',
      metavar='[PORT | START_PORT-END_PORT]',
      type=arg_parsers.ArgList(
          min_length=1, element_type=arg_parsers.Range.Parse),
      default=[],
      help="""\
      If specified, only packets addressed to ports in the specified
      list will be forwarded. If not specified for regional forwarding
      rules, all ports are matched. This flag is required for global
      forwarding rules and accepts a single continuous set of ports.

      Individual ports and ranges can be specified,
      for example (`--ports 8000-8004` or `--ports 80`).
      """)

  ports_scope.add_argument(
      '--port-range',
      type=arg_parsers.Range.Parse,
      metavar='[PORT | START_PORT-END_PORT]',
      help="""\
      DEPRECATED, use --ports. If specified, only packets addressed to ports in
      the specified range will be forwarded. If not specified for regional
      forwarding rules, all ports are matched. This flag is required for global
      forwarding rules.

      Either an individual port (`--port-range 80`) or a range of ports
      (`--port-range 3000-3100`) may be specified.
      """)


def AddNetworkTier(parser, include_alpha, for_update):
  """Adds network tier flag."""

  if include_alpha:
    if for_update:
      parser.add_argument(
          '--network-tier',
          choices=['PREMIUM', 'SELECT'],
          type=lambda x: x.upper(),
          help='Update the network tier of a forwarding rule. Network tier can '
          'only be changed from `PREMIUM` to `SELECT`, and visa versa. It does '
          'not allow to change from `STANDARD` to `PREMIUM`/`SELECT` and visa '
          'versa.')
    else:
      parser.add_argument(
          '--network-tier',
          choices=['PREMIUM', 'SELECT', 'STANDARD'],
          default='PREMIUM',
          type=lambda x: x.upper(),
          help='The network tier to assign to the forwarding rules.')
