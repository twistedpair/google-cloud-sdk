# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics readgroupsets describe.
"""

from googlecloudsdk.api_lib import genomics as lib
from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.calliope import base


class Describe(base.Command):
  """Returns details about a read group set.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('id',
                        help='The ID of the read group set to be described.')

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      a ReadGroupSet message
    """
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    request = genomics_messages.GenomicsReadgroupsetsGetRequest(
        readGroupSetId=args.id,
    )
    return apitools_client.readgroupsets.Get(request)

  def Display(self, args_unused, read_group_set):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      read_group_set: The read group set message returned from the Run() method.
    """

    self.format(read_group_set)
