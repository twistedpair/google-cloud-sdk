# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for updating firewall rules."""
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import firewalls_utils


class UpdateFirewall(base_classes.ReadWriteCommand):
  """Update a firewall rule."""

  @staticmethod
  def Args(parser):
    firewalls_utils.AddCommonArgs(parser, True)

  @property
  def service(self):
    return self.compute.firewalls

  @property
  def resource_type(self):
    return 'firewalls'

  def CreateReference(self, args):
    return self.CreateGlobalReference(args.name, resource_type='firewalls')

  def Run(self, args):
    self.new_allowed = firewalls_utils.ParseAllowed(args.allow, self.messages)
    args_unset = (args.allow is None
                  and args.description is None
                  and args.source_ranges is None
                  and args.source_tags is None
                  and args.target_tags is None)

    if args_unset:
      raise calliope_exceptions.ToolException(
          'At least one property must be modified.')

    return super(UpdateFirewall, self).Run(args)

  def GetGetRequest(self, args):
    """Returns the request for the existing Firewall resource."""
    return (self.service,
            'Get',
            self.messages.ComputeFirewallsGetRequest(
                firewall=self.ref.Name(),
                project=self.project))

  def GetSetRequest(self, args, replacement, existing):
    return (self.service,
            'Update',
            self.messages.ComputeFirewallsUpdateRequest(
                firewall=replacement.name,
                firewallResource=replacement,
                project=self.project))

  def Modify(self, args, existing):
    """Returns a modified Firewall message."""
    if args.allow is None:
      allowed = existing.allowed
    else:
      allowed = self.new_allowed

    if args.description:
      description = args.description
    elif args.description is None:
      description = existing.description
    else:
      description = None

    if args.source_ranges:
      source_ranges = args.source_ranges
    elif args.source_ranges is None:
      source_ranges = existing.sourceRanges
    else:
      source_ranges = []

    if args.source_tags:
      source_tags = args.source_tags
    elif args.source_tags is None:
      source_tags = existing.sourceTags
    else:
      source_tags = []

    if args.target_tags:
      target_tags = args.target_tags
    elif args.target_tags is None:
      target_tags = existing.targetTags
    else:
      target_tags = []

    new_firewall = self.messages.Firewall(
        name=existing.name,
        allowed=allowed,
        description=description,
        network=existing.network,
        sourceRanges=source_ranges,
        sourceTags=source_tags,
        targetTags=target_tags,
    )

    return new_firewall


UpdateFirewall.detailed_help = {
    'brief': 'Update a firewall rule',
    'DESCRIPTION': """\
        *{command}* is used to update firewall rules that allow incoming
        traffic to a network. Only arguments passed in will be updated on the
        firewall rule.  Other attributes will remain unaffected.
        """,
}
