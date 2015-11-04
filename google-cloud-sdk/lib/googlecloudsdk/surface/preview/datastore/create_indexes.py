# Copyright 2013 Google Inc. All Rights Reserved.

"""The gcloud datstore create-indexes command."""

from googlecloudsdk.api_lib.app import appengine_client
from googlecloudsdk.api_lib.app import yaml_parsing
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io


class CreateIndexes(base.Command):
  """Create new datastore indexes based on your local index configuration.

  This command creates new datastore indexes based on your local index
  configuration.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To create new indexes based on your local configuration, run:

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
    project = properties.VALUES.core.project.Get(required=True)
    app_config = yaml_parsing.AppConfigSet([args.index_file], project)

    if yaml_parsing.ConfigYamlInfo.INDEX not in app_config.Configs():
      raise exceptions.InvalidArgumentException(
          'index_file', 'You must provide the path to a valid index.yaml file.')

    info = app_config.Configs()[yaml_parsing.ConfigYamlInfo.INDEX]
    printer = console_io.ListPrinter(
        'You are about to update the following configurations:')
    printer.Print(
        ['{0}/{1}  From: [{2}]'.format(project, info.config, info.file)],
        output_stream=log.status)
    console_io.PromptContinue(default=True, throw_if_unattended=False,
                              cancel_on_no=True)

    client = appengine_client.AppengineClient()
    client.UpdateIndexes(info.parsed)
