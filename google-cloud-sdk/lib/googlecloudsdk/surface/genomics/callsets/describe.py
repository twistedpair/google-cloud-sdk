# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics callsets describe.
"""
from googlecloudsdk.calliope import base
from googlecloudsdk.shared.genomics import genomics_util


class Describe(base.Command):
  """Returns details about a call set.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('id',
                        help='The ID of the call set to be described.')

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      a CallSet message
    """
    return genomics_util.GetCallSet(self.context, str(args.id))

  def Display(self, args_unused, call_set):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      call_set: The Callset message returned from the Run() method.
    """
    self.format(call_set)
