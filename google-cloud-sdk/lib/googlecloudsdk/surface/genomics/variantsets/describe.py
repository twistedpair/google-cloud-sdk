# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics variantsets describe.
"""
from googlecloudsdk.calliope import base
from googlecloudsdk.shared import genomics as lib
from googlecloudsdk.shared.genomics import genomics_util


class Describe(base.Command):
  """Gets a variant set by ID.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'id',
        type=int, help='The ID of the variant set to describe.')

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
      a VariantSet whose id matches args.id.
    """
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    get_request = genomics_messages.GenomicsVariantsetsGetRequest(
        variantSetId=str(args.id),
    )

    return apitools_client.variantsets.Get(get_request)

  def Display(self, args_unused, variantset):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      variantset: The value returned from the Run() method.
    """
    genomics_util.PrettyPrint(variantset)
