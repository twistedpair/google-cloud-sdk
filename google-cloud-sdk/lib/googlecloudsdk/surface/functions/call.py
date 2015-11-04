# Copyright 2015 Google Inc. All Rights Reserved.

"""'functions call' command."""

from googlecloudsdk.api_lib.functions import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties


class Call(base.Command):
  """Call function synchronously for testing."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'name', help='Name of the function to be called.',
        type=util.ValidateFunctionNameOrRaise)
    parser.add_argument(
        '--data', default='',
        help='Data passed to the function (JSON string)')

  @util.CatchHTTPErrorRaiseHTTPException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Function call results (error or result with execution id)
    """
    project = properties.VALUES.core.project.Get(required=True)
    # TODO(b/25364251): Use resource parser.
    name = 'projects/{0}/regions/{1}/functions/{2}'.format(
        project, args.region, args.name)
    client = self.context['functions_client']
    messages = self.context['functions_messages']
    return client.projects_regions_functions.Call(
        messages.CloudfunctionsProjectsRegionsFunctionsCallRequest(
            data=args.data, name=name))
