# Copyright 2013 Google Inc. All Rights Reserved.

"""The gcloud datstore cleanup-indexes command."""

from googlecloudsdk.api_lib.app import appengine_client
from googlecloudsdk.api_lib.app import yaml_parsing
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions


class CleanupIndexes(base.Command):
  """Remove unused datastore indexes based on your local index configuration.

  This command removes unused datastore indexes based on your local index
  configuration.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To remove unused indexes based on your local configuration, run:

            $ {command} ~/myapp/index.yaml
          """,
  }

  @staticmethod
  def Args(parser):
    """Get arguments for this command.

    Args:
      parser: argparse.ArgumentParser, the parser for this command.
    """
    parser.add_argument('index_file',
                        help='The path to your index.yaml file.')

  def Run(self, args):
    app_config = yaml_parsing.AppConfigSet([args.index_file])

    if yaml_parsing.ConfigYamlInfo.INDEX not in app_config.Configs():
      raise exceptions.InvalidArgumentException(
          'index_file', 'You must provide the path to a valid index.yaml file.')

    client = appengine_client.AppengineClient()
    info = app_config.Configs()[yaml_parsing.ConfigYamlInfo.INDEX]
    client.CleanupIndexes(info.parsed)
