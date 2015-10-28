# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics callsets delete.
"""

from googlecloudsdk.api_lib import genomics as lib
from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.api_lib.genomics.exceptions import GenomicsError
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io


class Delete(base.Command):
  """Deletes a call set.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('id',
                        help='The ID of the call set to be deleted.')

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
    # Look it up first so that we can display the name
    existing_cs = genomics_util.GetCallSet(self.context, args.id)
    prompt_message = (
        'Deleting call set {0} ({1}) will delete all objects in the '
        'call set.').format(existing_cs.id, existing_cs.name)
    if not console_io.PromptContinue(message=prompt_message):
      raise GenomicsError('Deletion aborted by user.')
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]
    call_set = genomics_messages.GenomicsCallsetsDeleteRequest(
        callSetId=args.id,
    )

    apitools_client.callsets.Delete(call_set)
    log.DeletedResource('{0} ({1})'.format(existing_cs.id,
                                           existing_cs.name))
