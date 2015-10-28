# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics variants describe.
"""
from googlecloudsdk.api_lib import genomics as lib
from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.calliope import base


class Describe(base.Command):
  """Returns details about a variant.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('id',
                        type=int,
                        help='The ID of the variant to be described.')

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      a Variant message
    """
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    request = genomics_messages.GenomicsVariantsGetRequest(
        variantId=str(args.id),
    )

    return apitools_client.variants.Get(request)

  def Display(self, args_unused, variant):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      variant: The Variant message returned from the Run() method.
    """
    self.format(variant)
