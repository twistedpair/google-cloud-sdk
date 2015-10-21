# Copyright 2014 Google Inc. All Rights Reserved.

"""The super-group for the logging CLI."""

import argparse

from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.core import resolvers
from googlecloudsdk.core import resources
from googlecloudsdk.third_party.apis.logging import v1beta3


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class Logging(base.Group):
  """Manage Google Cloud Logging."""


  def Filter(self, context, args):
    """Modify the context that will be given to this group's commands when run.

    Args:
      context: The current context.
      args: The argparse namespace given to the corresponding .Run() invocation.

    Returns:
      The updated context.
    """
    url = properties.VALUES.api_endpoint_overrides.logging.Get()

    # All logging collections use projectId, so we can set a default value.
    resources.SetParamDefault(
        api='logging', collection=None, param='projectsId',
        resolver=resolvers.FromProperty(properties.VALUES.core.project))

    client_v1beta3 = v1beta3.LoggingV1beta3(
        url=url,
        http=self.Http(),
        get_credentials=False)

    context['logging_client'] = client_v1beta3
    context['logging_messages'] = v1beta3
    context['logging_resources'] = resources
    return context
