# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics datasets update.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.shared import genomics as lib
from googlecloudsdk.shared.genomics import genomics_util


class Update(base.Command):
  """Updates a dataset name.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('id',
                        type=int,
                        help='The ID of the dataset to be updated.')
    parser.add_argument('--name',
                        help='The new name of the dataset.',
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

    request = genomics_messages.GenomicsDatasetsPatchRequest(
        dataset=genomics_messages.Dataset(
            name=args.name,
        ),
        datasetId=str(args.id),
    )

    return apitools_client.datasets.Patch(request)

  def Display(self, args, dataset):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      dataset: The value returned from the Run() method.
    """
    if dataset:
      log.Print('Updated dataset {0}, name: {1}'.format(
          dataset.id, dataset.name))
