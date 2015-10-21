# Copyright 2015 Google Inc. All Rights Reserved.

"""Command to activate named configuration."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import named_configs


class Activate(base.Command):
  """Activates an existing named configuration."""

  detailed_help = {
      'DESCRIPTION': """\
          {description}

          See `gcloud topic configurations` for an overview of named
          configurations.
          """,
      'EXAMPLES': """\
          To activate an existing named configuration, run:

            $ {command} my_config

          To list all properties in the activated configuration, run:

            $ gcloud config list --all
          """,
  }

  @staticmethod
  def Args(parser):
    """Adds args for this command."""
    parser.add_argument(
        'configuration_name',
        help='Configuration name to activate')

  def Run(self, args):
    named_configs.ActivateNamedConfig(args.configuration_name)
    log.status.write('Activated [{0}].\n'.format(args.configuration_name))
    return args.configuration_name

