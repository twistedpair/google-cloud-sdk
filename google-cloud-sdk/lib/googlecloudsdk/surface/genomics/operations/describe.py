# Copyright 2015 Google Inc. All Rights Reserved.
"""Implementation of gcloud genomics operations describe.
"""

from googlecloudsdk.api_lib import genomics as lib
from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.calliope import base


class Describe(base.Command):
  """Returns details about an operation.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('name',
                        type=str,
                        help='The name of the operation to be described.')

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      a Operation message
    """
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    return apitools_client.operations.Get(
        genomics_messages.GenomicsOperationsGetRequest(name=args.name))

  def Display(self, args_unused, operation):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      operation: The Operation message returned from the Run() method.
    """
    self.format(operation)
