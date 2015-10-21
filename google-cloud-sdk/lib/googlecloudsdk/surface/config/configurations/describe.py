# Copyright 2015 Google Inc. All Rights Reserved.

"""Command to describe named configuration."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import named_configs
from googlecloudsdk.core import properties


class Describe(base.Command):
  """Describes a named configuration by listing its properties."""

  detailed_help = {
      'DESCRIPTION': """\
          {description}

          See `gcloud topic configurations` for an overview of named
          configurations.
          """,
      'EXAMPLES': """\
          To describe esisting named configuration, run:

            $ {command} my_config

          This is similar in content to:

            $ gcloud config configurations activate my_config

            $ gcloud config list
          """,
  }

  @staticmethod
  def Args(parser):
    """Adds args for this command."""
    parser.add_argument(
        'configuration_name',
        help='Configuration name to descrive')
    parser.add_argument(
        '--all', action='store_true',
        help='Include unset properties in output.')

  def Run(self, args):
    fname = named_configs.GetPathForConfigName(args.configuration_name)

    if not named_configs.IsPathReadable(fname):
      raise named_configs.NamedConfigLoadError(
          'Reading named configuration [{0}] failed because [{1}] cannot '
          'be read.'.format(args.configuration_name, fname))

    return properties.VALUES.AllValues(
        list_unset=args.all,
        properties_file=properties.PropertiesFile([fname]),
        only_file_contents=True)

  def Display(self, _, result):
    if not result:
      log.err.Print('(empty configuration)')
    properties.DisplayProperties(log.out, result)
