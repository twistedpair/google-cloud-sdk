# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for creating firewall rules."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import firewalls_utils


class Create(base_classes.BaseAsyncCreator):
  """Create a Google Compute Engine firewall rule.

  *{command}* is used to create firewall rules to allow incoming
  traffic to a network.
  """

  @staticmethod
  def Args(parser):
    firewalls_utils.AddCommonArgs(parser, False)

    network = parser.add_argument(
        '--network',
        default='default',
        help='The network to which this rule is attached.')
    network.detailed_help = """\
        The network to which this rule is attached. If omitted, the
        rule is attached to the ``default'' network.
        """

  @property
  def service(self):
    return self.compute.firewalls

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'firewalls'

  def CreateRequests(self, args):
    """Returns a list of requests necessary for adding firewall rules."""
    if not args.source_ranges and not args.source_tags:
      args.source_ranges = ['0.0.0.0/0']

    allowed = firewalls_utils.ParseAllowed(args.allow, self.messages)

    network_ref = self.CreateGlobalReference(
        args.network, resource_type='networks')
    firewall_ref = self.CreateGlobalReference(
        args.name, resource_type='firewalls')

    request = self.messages.ComputeFirewallsInsertRequest(
        firewall=self.messages.Firewall(
            allowed=allowed,
            name=firewall_ref.Name(),
            description=args.description,
            network=network_ref.SelfLink(),
            sourceRanges=args.source_ranges,
            sourceTags=args.source_tags,
            targetTags=args.target_tags),
        project=self.project)
    return [request]
