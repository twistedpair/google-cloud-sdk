# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics callsets update.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.shared import genomics as lib
from googlecloudsdk.shared.genomics import genomics_util


class Update(base.Command):
  """Updates a call set name.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('id',
                        help='The ID of the call set to be updated.')
    parser.add_argument('--name',
                        help='The new name of the call set.',
                        required=True)

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

    request = genomics_messages.GenomicsCallsetsPatchRequest(
        callSet=genomics_messages.CallSet(
            id=args.id,
            name=args.name,
            # Can't construct a callset without the variant id set, but
            # actually setting the variant id would not do anything, so
            # use a dummy value. See b/22818510.
            variantSetIds=['123'],
        ),
        callSetId=args.id,
    )

    return apitools_client.callsets.Patch(request)

  def Display(self, args_unused, call_set):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      call_set: The value returned from the Run() method.
    """
    log.Print('Updated call set {0}, id: {1}'.format(
        call_set.name, call_set.id))
