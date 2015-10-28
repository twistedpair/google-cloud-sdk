# Copyright 2015 Google Inc. All Rights Reserved.

"""The main command group for Google Cloud Functions."""

import argparse

from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apis.cloudfunctions import v1beta1


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Functions(base.Group):
  """Manages Google Cloud Functions."""

  @staticmethod
  def Args(parser):
    """Add command flags that are global to this group.

    Per command flags should be added in the Args() method of that specific
    command.

    Args:
      parser: argparse.ArgumentParser, This is a standard argparser parser with
        which you can register arguments.  See the public argparse documentation
        for its capabilities.
    """
    parser.add_argument(
        '--region',
        default='us-central1',
        help='The compute region (e.g. us-central1) to use')

  def Filter(self, context, args):
    """Modify the context that will be given to this group's commands when run.

    Args:
      context: The current context.
      args: The argparse namespace given to the corresponding .Run() invocation.

    Returns:
      The updated context.
    """
    url = properties.VALUES.api_endpoint_overrides.functions.Get()
    client_v1beta1 = v1beta1.CloudfunctionsV1beta1(
        url=url,
        http=self.Http(),
        get_credentials=False)

    context['functions_client'] = client_v1beta1
    context['functions_messages'] = v1beta1
    return context
