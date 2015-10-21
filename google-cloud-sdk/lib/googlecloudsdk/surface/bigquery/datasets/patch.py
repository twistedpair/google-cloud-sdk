# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery datasets patch.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.shared.bigquery import message_conversions
from googlecloudsdk.surface import bigquery as commands


class DatasetsPatch(base.Command):
  """Updates the description of a dataset.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('--description', help='Description of the dataset.')
    parser.add_argument('dataset_name', help='The name of the dataset.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespeace, All the arguments that were provided to this
        command invocation.

    Returns:
      None
    """
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    resource = resource_parser.Parse(
        args.dataset_name, collection='bigquery.datasets')
    reference = message_conversions.DatasetResourceToReference(
        bigquery_messages, resource)
    request = bigquery_messages.BigqueryDatasetsPatchRequest(
        dataset=bigquery_messages.Dataset(
            datasetReference=bigquery_messages.DatasetReference(
                projectId=reference.projectId, datasetId=reference.datasetId),
            description=args.description),
        projectId=reference.projectId,
        datasetId=reference.datasetId)
    apitools_client.datasets.Patch(request)
    log.UpdatedResource(resource)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    pass
