# Copyright 2015 Google Inc. All Rights Reserved.

"""Wait operations command."""
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.container.lib import util


class Wait(base.Command):
  """Poll an operation for completion."""

  @staticmethod
  def Args(parser):
    """Register flags for this command.

    Args:
      parser: An argparse.ArgumentParser-like object. It is mocked out in order
          to capture some information, but behaves like an ArgumentParser.
    """
    parser.add_argument('operation_id', help='The operation id to poll.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Some value that we want to have printed later.
    """
    adapter = self.context['api_adapter']

    operation_ref = adapter.ParseOperation(args.operation_id)

    try:
      return adapter.WaitForOperation(
          operation_ref,
          'Waiting for {0} to complete'.format(operation_ref.operationId))
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    self.format(result)
