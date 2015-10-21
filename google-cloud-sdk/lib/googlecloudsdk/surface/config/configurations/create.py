# Copyright 2015 Google Inc. All Rights Reserved.

"""Command to create named configuration."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import named_configs


class Create(base.Command):
  """Creates a new named configuration."""

  detailed_help = {
      'DESCRIPTION': """\
          {description}

          See `gcloud topic configurations` for an overview of named
          configurations.
          """,
      'EXAMPLES': """\
          To create a new named configuration, run:

            $ {command} my_config
          """,
  }

  @staticmethod
  def Args(parser):
    """Adds args for this command."""
    parser.add_argument(
        'configuration_name',
        help='Configuration name to create')

  def Run(self, args):
    named_configs.CreateNamedConfig(args.configuration_name)

    log.CreatedResource(args.configuration_name)
    log.err.Print('To use this configuration, activate it using `gcloud '
                  'config configurations activate`.')
    return args.configuration_name
