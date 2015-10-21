# Copyright 2014 Google Inc. All Rights Reserved.

"""The command-group for the Updater service CLI."""

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import cli
from googlecloudsdk.core import properties
from googlecloudsdk.core import resolvers
from googlecloudsdk.core import resources
from googlecloudsdk.core.credentials import store
from googlecloudsdk.third_party.apis.replicapoolupdater import v1beta1 as updater_v1beta1
from googlecloudsdk.third_party.apis.replicapoolupdater.v1beta1 import replicapoolupdater_v1beta1_messages


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Updater(base.Group):
  """Manage updates in a managed instance group."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        '--zone', help='Rolling update zone name.',
        action=actions.StoreProperty(properties.VALUES.compute.zone))

  @exceptions.RaiseToolExceptionInsteadOf(store.Error)
  def Filter(self, context, args):
    """Context() is a filter function that can update the context.

    Args:
      context: The current context.
      args: The argparse namespace that was specified on the CLI or API.

    Returns:
      The updated context.
    """
    if args.zone is None:
      raise exceptions.ToolException('argument --zone is required')

    context['updater_api'] = updater_v1beta1.ReplicapoolupdaterV1beta1(
        get_credentials=False,
        http=cli.Http())
    context['updater_messages'] = replicapoolupdater_v1beta1_messages
    resources.SetParamDefault(
        api='compute', collection='instanceTemplates', param='project',
        resolver=resolvers.FromProperty(properties.VALUES.core.project))
    resources.SetParamDefault(
        api='replicapool', collection=None, param='project',
        resolver=resolvers.FromProperty(properties.VALUES.core.project))
    resources.SetParamDefault(
        api='replicapool', collection=None, param='zone',
        resolver=resolvers.FromProperty(properties.VALUES.compute.zone))
    resources.SetParamDefault(
        api='resourceviews', collection=None, param='projectName',
        resolver=resolvers.FromProperty(properties.VALUES.core.project))
    resources.SetParamDefault(
        api='resourceviews', collection=None, param='zone',
        resolver=resolvers.FromProperty(properties.VALUES.compute.zone))
    resources.SetParamDefault(
        api='replicapoolupdater', collection=None, param='project',
        resolver=resolvers.FromProperty(properties.VALUES.core.project))
    resources.SetParamDefault(
        api='replicapoolupdater', collection=None, param='zone',
        resolver=resolvers.FromProperty(properties.VALUES.compute.zone))
    context['updater_resources'] = resources
    return context
