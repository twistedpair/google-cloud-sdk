# Copyright 2015 Google Inc. All Rights Reserved.

"""Get Server Config."""
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


class GetServerConfig(base.Command):
  """Get Container Engine server config."""

  def Run(self, args):
    adapter = self.context['api_adapter']

    project_id = properties.VALUES.core.project.Get(required=True)
    zone = properties.VALUES.compute.zone.Get(required=True)

    log.status.Print('Fetching server config for {zone}'.format(zone=zone))
    return adapter.GetServerConfig(project_id, zone)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    self.format(result)
