# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting target HTTPS proxies."""
from googlecloudsdk.shared.compute import base_classes


class Delete(base_classes.GlobalDeleter):
  """Delete target HTTPS proxies."""

  @staticmethod
  def Args(parser):
    base_classes.GlobalDeleter.Args(parser, 'compute.targetHttpsProxies')

  @property
  def service(self):
    return self.compute.targetHttpsProxies

  @property
  def resource_type(self):
    return 'targetHttpsProxies'


Delete.detailed_help = {
    'brief': 'Delete target HTTPS proxies',
    'DESCRIPTION': """\
        *{command}* deletes one or more target HTTPS proxies.
        """,
}
