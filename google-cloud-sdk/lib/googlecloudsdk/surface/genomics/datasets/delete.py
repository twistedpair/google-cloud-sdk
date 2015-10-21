# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics datasets delete.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.shared import genomics as lib
from googlecloudsdk.shared.genomics import genomics_util
from googlecloudsdk.shared.genomics.exceptions import GenomicsError


class DatasetsDelete(base.Command):
  """Deletes a dataset.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('id',
                        type=int,
                        help='The ID of the dataset to be deleted.')

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
    existing_ds = genomics_util.GetDataset(self.context, args.id)

    prompt_message = (
        'Deleting dataset {0} ({1}) will delete all objects in the dataset. '
        'Deleted datasets can be recovered with the "restore" command '
        'up to one week after the deletion occurs.').format(existing_ds.id,
                                                            existing_ds.name)

    if not console_io.PromptContinue(message=prompt_message):
      raise GenomicsError('Deletion aborted by user.')

    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    dataset = genomics_messages.GenomicsDatasetsDeleteRequest(
        datasetId=str(args.id),
    )

    apitools_client.datasets.Delete(dataset)
    log.DeletedResource('{0} ({1})'.format(existing_ds.id,
                                           existing_ds.name))
