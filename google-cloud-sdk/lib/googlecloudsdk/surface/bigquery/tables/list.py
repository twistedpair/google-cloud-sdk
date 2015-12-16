# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery tables list.
"""

from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.api_lib.bigquery import message_conversions
from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.surface import bigquery as commands
from googlecloudsdk.third_party.apitools.base.py import exceptions
from googlecloudsdk.third_party.apitools.base.py import list_pager


class TablesList(base.Command):
  """Lists the name of each table or view in a specified dataset.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'dataset_name',
        help='The dataset whose tables and views are to be listed.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespeace, All the arguments that were provided to this
        command invocation.

    Returns:
      An iterator over TableList.TablesValueListEntry messages.
    """
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    resource = resource_parser.Parse(
        args.dataset_name, collection='bigquery.datasets')
    reference = message_conversions.DatasetResourceToReference(
        bigquery_messages, resource)
    request = bigquery_messages.BigqueryTablesListRequest(
        projectId=reference.projectId,
        datasetId=reference.datasetId)
    return list_pager.YieldFromList(
        apitools_client.tables,
        request,
        batch_size=None,  # Use server default.
        field='tables')

  def Display(self, args, tables):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      tables: An iterator over TableList.TablesValueListEntry messages.
    """
    try:
      list_printer.PrintResourceList('bigquery.tables.list', tables)
    except exceptions.HttpError as server_error:
      raise bigquery.Error.ForHttpError(server_error)
