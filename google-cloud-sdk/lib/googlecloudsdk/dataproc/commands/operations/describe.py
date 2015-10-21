# Copyright 2015 Google Inc. All Rights Reserved.

"""Describe operation command."""

from googlecloudsdk.calliope import base

from googlecloudsdk.dataproc.lib import util


class Describe(base.Command):
  """View the details of an operation."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To view the details of an operation, run:

            $ {command} operation_id
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'operation', help='The ID of the operation to describe.')

  @util.HandleHttpError
  def Run(self, args):
    client = self.context['dataproc_client']
    messages = self.context['dataproc_messages']

    request = messages.DataprocOperationsGetRequest(
        name=args.operation)

    operation = client.operations.Get(request)
    return operation

  def Display(self, args, result):
    self.format(result)
