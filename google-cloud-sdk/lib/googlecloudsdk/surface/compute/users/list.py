# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for listing users."""
from googlecloudsdk.api_lib.compute import base_classes


class List(base_classes.GlobalLister):
  """List Google Compute Engine users."""

  @property
  def service(self):
    return self.clouduseraccounts.users

  @property
  def resource_type(self):
    return 'users'

  @property
  def messages(self):
    return self.clouduseraccounts.MESSAGES_MODULE

List.detailed_help = base_classes.GetGlobalListerHelp('users')
