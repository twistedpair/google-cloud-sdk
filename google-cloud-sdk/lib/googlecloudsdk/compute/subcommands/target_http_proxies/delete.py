# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting target HTTP proxies."""
from googlecloudsdk.shared.compute import base_classes


class Delete(base_classes.GlobalDeleter):
  """Delete target HTTP proxies."""

  @staticmethod
  def Args(parser):
    base_classes.GlobalDeleter.Args(parser, 'compute.targetHttpProxies')

  @property
  def service(self):
    return self.compute.targetHttpProxies

  @property
  def resource_type(self):
    return 'targetHttpProxies'


Delete.detailed_help = {
    'brief': 'Delete target HTTP proxies',
    'DESCRIPTION': """\
        *{command}* deletes one or more target HTTP proxies.
        """,
}
