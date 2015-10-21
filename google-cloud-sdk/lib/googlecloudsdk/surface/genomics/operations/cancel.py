# Copyright 2015 Google Inc. All Rights Reserved.
"""Implementation of gcloud genomics operations cancel.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.shared import genomics as lib
from googlecloudsdk.shared.genomics import genomics_util
from googlecloudsdk.shared.genomics.exceptions import GenomicsError


class Cancel(base.Command):
  """Cancels an operation.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('name',
                        type=str,
                        help='The name of the operation to be canceled.')

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    Returns:
      None
    """
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    # Look it up first so that we can display it
    op = apitools_client.operations.Get(
        genomics_messages.GenomicsOperationsGetRequest(name=args.name))
    self.format(op)

    if not console_io.PromptContinue(message='This operation will be canceled'):
      raise GenomicsError('Cancel aborted by user.')

    apitools_client.operations.Cancel(
        genomics_messages.GenomicsOperationsCancelRequest(name=args.name))
    log.status.write('Canceled [{0}].\n'.format(args.name))
