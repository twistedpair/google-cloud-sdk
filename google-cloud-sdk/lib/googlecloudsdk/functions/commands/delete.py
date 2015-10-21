# Copyright 2015 Google Inc. All Rights Reserved.

"""'functions delete' command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io

from googlecloudsdk.functions.lib import exceptions
from googlecloudsdk.functions.lib import operations
from googlecloudsdk.functions.lib import util


class Delete(base.Command):
  """Deletes a given function."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'name', help='The name of the function to delete.',
        type=util.ValidateFunctionNameOrRaise)

  @util.CatchHTTPErrorRaiseHTTPException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      None

    Raises:
      FunctionsError: If the user doesn't confirm on prompt.
    """
    client = self.context['functions_client']
    messages = self.context['functions_messages']
    project = properties.VALUES.core.project.Get(required=True)
    name = 'projects/{0}/regions/{1}/functions/{2}'.format(
        project, args.region, args.name)

    prompt_message = 'Resource [{0}] will be deleted.'.format(name)
    if not console_io.PromptContinue(message=prompt_message):
      raise exceptions.FunctionsError('Deletion aborted by user.')
    # TODO(user): Use resources.py here after b/21908671 is fixed.
    op = client.projects_regions_functions.Delete(
        messages.CloudfunctionsProjectsRegionsFunctionsDeleteRequest(
            name=name))
    operations.Wait(op, messages, client)
    log.DeletedResource(name)
