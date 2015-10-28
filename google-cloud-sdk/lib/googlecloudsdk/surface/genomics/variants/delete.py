# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics variants delete.
"""

from googlecloudsdk.api_lib import genomics as lib
from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class Delete(base.Command):
  """Deletes a variant.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('id',
                        type=int,
                        help='The ID of the variant to be deleted.')

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      The ID of the variant that was deleted.
    """
    vid = str(args.id)
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    request = genomics_messages.GenomicsVariantsDeleteRequest(
        variantId=vid,
    )
    apitools_client.variants.Delete(request)
    log.DeletedResource('variant {0}'.format(vid))
    return vid
