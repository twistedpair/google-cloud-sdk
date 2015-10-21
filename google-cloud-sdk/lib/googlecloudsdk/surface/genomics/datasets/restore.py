# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics datasets restore.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.shared import genomics as lib
from googlecloudsdk.shared.genomics import genomics_util
from googlecloudsdk.shared.genomics.exceptions import GenomicsError


class DatasetsRestore(base.Command):
  """Restores a deleted dataset.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('id',
                        type=int,
                        help='The ID of the deleted dataset to be restored.')

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
    prompt_message = (
        'Restoring dataset {0} will restore all objects in '
        'the dataset.').format(args.id)

    if not console_io.PromptContinue(message=prompt_message):
      raise GenomicsError('Restore aborted by user.')

    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    dataset = genomics_messages.GenomicsDatasetsUndeleteRequest(
        datasetId=str(args.id),
    )

    return apitools_client.datasets.Undelete(dataset)

  def Display(self, args_unused, dataset):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      dataset: The value returned from the Run() method.
    """
    if dataset:
      log.Print('Restored dataset {0}, name: {1}'.format(
          dataset.id, dataset.name))
