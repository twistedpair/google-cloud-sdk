# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for creating forwarding rules."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import forwarding_rules_utils as utils
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.third_party.apis.compute.v1 import compute_v1_messages


def _SupportedProtocols(messages):
  return sorted(
      messages.ForwardingRule.IPProtocolValueValuesEnum.to_dict().keys())


def _Args(parser):
  """Argument parsing."""
  utils.ForwardingRulesTargetMutator.Args(parser)

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

      Either an individual port (`--port-range 80`) or a range of ports
      (`--port-range 3000-3100`) may be specified.
      """


class Create(base_classes.ListOutputMixin,
             utils.ForwardingRulesTargetMutator):
  """Create a forwarding rule to direct network traffic to a load balancer."""

  @staticmethod
  def Args(parser):
    _Args(parser)

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


Create.detailed_help = {
    'DESCRIPTION': ("""\
        *{{command}}* is used to create a forwarding rule. {overview}

        When creating a forwarding rule, exactly one of  ``--target-instance'',
        ``--target-pool'', ``--target-http-proxy'', ``-target-https-proxy'',
        and ``--target-vpn-gateway'' must be specified.
        """.format(overview=utils.FORWARDING_RULES_OVERVIEW)),
}
