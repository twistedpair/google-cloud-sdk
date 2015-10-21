# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing forwarding rules."""
from googlecloudsdk.shared.compute import base_classes


class List(base_classes.GlobalRegionalLister):
  """List forwarding rules."""

  @property
  def global_service(self):
    return self.compute.globalForwardingRules

  @property
  def regional_service(self):
    return self.compute.forwardingRules

  @property
  def resource_type(self):
    return 'forwardingRules'

  @property
  def allowed_filtering_types(self):
    return ['globalForwardingRules', 'forwardingRules']


List.detailed_help = (
    base_classes.GetGlobalRegionalListerHelp('forwarding rules'))
