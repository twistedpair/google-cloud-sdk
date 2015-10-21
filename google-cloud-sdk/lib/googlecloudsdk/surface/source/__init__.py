# Copyright 2015 Google Inc. All Rights Reserved.

"""The main command group for cloud source command group."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.core import resolvers
from googlecloudsdk.core import resources
from googlecloudsdk.core.credentials import store as c_store
from googlecloudsdk.shared.source import source


class Source(base.Group):
  """Cloud git repository commands."""

  def Filter(self, context, args):
    """Initialize context for source commands.

    Args:
      context: The current context.
      args: The argparse namespace that was specified on the CLI or API.

    Returns:
      The updated context.
    """
    resources.SetParamDefault(
        api='source', collection=None, param='projectId',
        resolver=resolvers.FromProperty(properties.VALUES.core.project))

    source.Source.SetResourceParser(resources.REGISTRY)
    source.Source.SetApiEndpoint(
        self.Http(), properties.VALUES.api_endpoint_overrides.source.Get())
