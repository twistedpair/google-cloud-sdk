# Copyright 2014 Google Inc. All Rights Reserved.

"""Deployment Manager manifests sub-group."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions


class Manifests(base.Group):
  """Commands for Deployment Manager manifests.

  Commands to list and examine manifests within a deployment.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To view all details about a manifest, run:

            $ {command} describe manifest-name --deployment my-deployment

          To see the list of all manifests in a deployment, run:

            $ {command} list --deployment my-deployment
          """,
  }

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('--deployment', help='Deployment name')

  def Filter(self, unused_tool_context, args):
    if not args.deployment:
      raise exceptions.ToolException('argument --deployment is required')
