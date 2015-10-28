# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics variant sets create.
"""

from googlecloudsdk.api_lib import genomics as lib
from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class Create(base.Command):
  """Creates a variant set belonging to a specified dataset.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--dataset-id',
        type=int, help='The ID of the dataset the variant set will belong to.',
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

    variantset = genomics_messages.VariantSet(
        datasetId=str(args.dataset_id),
    )

    return apitools_client.variantsets.Create(variantset)

  def Display(self, args_unused, variantset):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      variantset: The value returned from the Run() method.
    """
    log.Print('Created variant set id: {0}, belonging to dataset id: {1}'
              .format(variantset.id, variantset.datasetId))
    log.CreatedResource(variantset.id)
