# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics callsets create.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.shared import genomics as lib
from googlecloudsdk.shared.genomics import genomics_util


class Create(base.Command):
  """Creates a call set with a specified name.

  A call set is a collection of variant calls, typically for one sample.
  """

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        'name', help='The name of the call set being created.')
    parser.add_argument(
        '--variant-set-id',
        required=True,
        help='Variant set that this call set belongs to.')
    # TODO(tovanadler): Add the info command.

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: argparse.Namespace, All the arguments that were provided to this
        command invocation.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    Returns:
      None
    """
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]
    call_set = genomics_messages.CallSet(
        name=args.name,
        variantSetIds=[args.variant_set_id],
    )

    return apitools_client.callsets.Create(call_set)

  def Display(self, args_unused, call_set):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      call_set: The value returned from the Run() method.
    """
    log.Print('Created call set {0}, id: {1}'.format(
        call_set.name, call_set.id))
    log.CreatedResource('{0} ({1})'.format(call_set.id,
                                           call_set.name))
