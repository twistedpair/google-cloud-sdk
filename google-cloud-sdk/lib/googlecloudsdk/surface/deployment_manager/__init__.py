# Copyright 2014 Google Inc. All Rights Reserved.

"""The command group for the DeploymentManager CLI."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core.credentials import store
from googlecloudsdk.third_party.apis.deploymentmanager import v2 as deploymentmanager_v2
from googlecloudsdk.third_party.apis.deploymentmanager.v2 import deploymentmanager_v2_messages as v2_messages


@base.ReleaseTracks(base.ReleaseTrack.GA)
class DmV2(base.Group):
  """Manage deployments of cloud resources."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    pass

  @exceptions.RaiseToolExceptionInsteadOf(store.Error)
  def Filter(self, context, args):
    """Context() is a filter function that can update the context.

    Args:
      context: The current context.
      args: The argparse namespace that was specified on the CLI or API.

    Returns:
      The updated context.
    Raises:
      ToolException: When no project is specified.
    """

    # Apitools client to make API requests.
    url = '/'.join([properties.VALUES.core.api_host.Get(), 'deploymentmanager'])

    # v2
    context['deploymentmanager-client'] = (
        deploymentmanager_v2.DeploymentmanagerV2(
            get_credentials=False, url='/'.join([url, 'v2']),
            http=self.Http())
    )
    context['deploymentmanager-messages'] = v2_messages

    return context
