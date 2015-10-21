# Copyright 2015 Google Inc. All Rights Reserved.

"""Cancel operation command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io

from googlecloudsdk.dataproc.lib import util


class Cancel(base.Command):
  """Cancel an active operation."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To cancel an operation, run:

            $ {command} operation_id
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('operation', help='The ID of the operation to cancel.')

  @util.HandleHttpError
  def Run(self, args):
    client = self.context['dataproc_client']
    messages = self.context['dataproc_messages']

    request = messages.DataprocOperationsCancelRequest(
        cancelOperationRequest=messages.CancelOperationRequest(),
        name=args.operation)

    if not console_io.PromptContinue(
        message="The operation '{0}' will be cancelled.".format(
            args.operation)):
      raise exceptions.ToolException('Cancellation aborted by user.')

    client.operations.Cancel(request)
    # TODO(user) Check that operation was cancelled.

    log.status.write('Cancelled [{0}].\n'.format(args.operation))
