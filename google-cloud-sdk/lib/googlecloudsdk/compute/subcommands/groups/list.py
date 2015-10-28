# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for listing groups."""
from googlecloudsdk.api_lib.compute import base_classes


class List(base_classes.GlobalLister):
  """List Google Compute Engine groups."""

  @property
  def service(self):
    return self.clouduseraccounts.groups

  @property
  def resource_type(self):
    return 'groups'

  @property
  def messages(self):
    return self.clouduseraccounts.MESSAGES_MODULE


List.detailed_help = base_classes.GetGlobalListerHelp('groups')
