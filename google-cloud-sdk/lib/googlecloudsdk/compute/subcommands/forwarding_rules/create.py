# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for creating forwarding rules."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import forwarding_rules_utils as utils
from googlecloudsdk.third_party.apis.compute.v1 import compute_v1_messages


def _SupportedProtocols(messages):
  return sorted(
      messages.ForwardingRule.IPProtocolValueValuesEnum.to_dict().keys())

# TODO(user): VPN-Alpha Add --target-vpn-gateway to the help text below.
_DESCRIPTION = """\
        *{command}* is used to create a forwarding rule. Forwarding
        rules match and direct certain types of traffic to a load
        balancer which is controlled by a target pool, a target instance,
        or a target HTTP proxy. Target pools and target instances perform load
        balancing at the layer 3 of the OSI networking model
        (link:http://en.wikipedia.org/wiki/Network_layer[]). Target
        HTTP proxies perform load balancing at layer 7.

        Forwarding rules can be either regional or global. They are
        regional if they point to a target pool or a target instance
        and global if they point to a target HTTP proxy.

        For more information on load balancing, see
        link:https://cloud.google.com/compute/docs/load-balancing-and-autoscaling/[].
"""


def _Args(parser, beta_features):
  """Argument parsing."""
  utils.ForwardingRulesTargetMutator.Args(
      parser, include_beta_targets=beta_features)

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

  ip_protocol = parser.add_argument(
      '--ip-protocol',
      choices=_SupportedProtocols(compute_v1_messages),
      type=lambda x: x.upper(),
      help='The IP protocol that the rule will serve.')
  ip_protocol.detailed_help = """\
      The IP protocol that the rule will serve. If left empty, TCP
      is used. Supported protocols are: {0}.
      """.format(', '.join(_SupportedProtocols(compute_v1_messages)))

  parser.add_argument(
      '--description',
      help='An optional textual description for the forwarding rule.')

  port_range = parser.add_argument(
      '--port-range',
      help=('If specified, only packets addressed to the port or '
            'ports in the specified range will be forwarded.'),
      metavar='[PORT | PORT-PORT]')
  port_range.detailed_help = """\
      If specified, only packets addressed to ports in the specified
      range will be forwarded. If not specified for regional forwarding
      rules, all ports are matched. This flag is required for global
      forwarding rules.
      """


@base.ReleaseTracks(base.ReleaseTrack.GA)
class CreateGA(base_classes.ListOutputMixin,
               utils.ForwardingRulesTargetMutator):
  """Create a forwarding rule to direct network traffic to a load balancer."""

  @staticmethod
  def Args(parser):
    _Args(parser, beta_features=False)

  @property
  def method(self):
    return 'Insert'

  def ConstructProtocol(self, args):
    if args.ip_protocol:
      return self.messages.ForwardingRule.IPProtocolValueValuesEnum(
          args.ip_protocol)
    else:
      return

  def CreateGlobalRequests(self, args):
    """Create a globally scoped request."""
    if not args.port_range:
      raise exceptions.ToolException(
          '[--port-range] is required for global forwarding rules.')

    target_ref = self.GetGlobalTarget(args)
    forwarding_rule_ref = self.CreateGlobalReference(
        args.name, resource_type='globalForwardingRules')
    protocol = self.ConstructProtocol(args)

    request = self.messages.ComputeGlobalForwardingRulesInsertRequest(
        forwardingRule=self.messages.ForwardingRule(
            description=args.description,
            name=forwarding_rule_ref.Name(),
            IPAddress=args.address,
            IPProtocol=protocol,
            portRange=args.port_range,
            target=target_ref.SelfLink(),
        ),
        project=self.project)

    return [request]

  def CreateRegionalRequests(self, args):
    """Create a regionally scoped request."""
    target_ref, target_region = self.GetRegionalTarget(args)
    forwarding_rule_ref = self.CreateRegionalReference(
        args.name, args.region or target_region)
    protocol = self.ConstructProtocol(args)

    request = self.messages.ComputeForwardingRulesInsertRequest(
        forwardingRule=self.messages.ForwardingRule(
            description=args.description,
            name=forwarding_rule_ref.Name(),
            IPAddress=args.address,
            IPProtocol=protocol,
            portRange=args.port_range,
            target=target_ref.SelfLink(),
        ),
        project=self.project,
        region=forwarding_rule_ref.region)

    return [request]


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class CreateAlphaBeta(CreateGA):
  """Create a forwarding rule to direct network traffic to a load balancer."""

  @staticmethod
  def Args(parser):
    _Args(parser, beta_features=True)

CreateGA.detailed_help = {
    'brief': ('Create a forwarding rule to direct network traffic to a load '
              'balancer'),
    'DESCRIPTION': (_DESCRIPTION + """\
        When creating a forwarding rule, exactly one of  ``--target-instance'',
        ``--target-pool'', ``--target-http-proxy'',
        and ``--target-vpn-gateway'' must be specified.
        """),
}

CreateAlphaBeta.detailed_help = {
    'brief': ('Create a forwarding rule to direct network traffic to a load '
              'balancer'),
    'DESCRIPTION': (_DESCRIPTION + """\
        When creating a forwarding rule, exactly one of  ``--target-instance'',
        ``--target-pool'', ``--target-http-proxy'', ``-target-https-proxy'',
        and ``--target-vpn-gateway'' must be specified.
        """),
}
