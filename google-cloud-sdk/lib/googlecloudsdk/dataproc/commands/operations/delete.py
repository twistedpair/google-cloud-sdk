# Copyright 2015 Google Inc. All Rights Reserved.

"""Delete operation command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io

from googlecloudsdk.dataproc.lib import util


class Delete(base.Command):
  """Delete the record of an inactive operation."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To delete the record of an operation, run:

            $ {command} operation_id
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('operation', help='The ID of the operation to delete.')

  @util.HandleHttpError
  def Run(self, args):
    client = self.context['dataproc_client']
    messages = self.context['dataproc_messages']

    request = messages.DataprocOperationsDeleteRequest(
        name=args.operation)

    if not console_io.PromptContinue(
        message="The operation '{0}' will be deleted.".format(args.operation)):
      raise exceptions.ToolException('Deletion aborted by user.')

    client.operations.Delete(request)

    # TODO(user) Check that operation was deleted.

    log.DeletedResource(args.operation)
