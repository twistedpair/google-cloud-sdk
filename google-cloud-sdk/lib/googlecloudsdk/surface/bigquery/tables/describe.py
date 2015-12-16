# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery tables describe.
"""

from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.api_lib.bigquery import message_conversions
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.surface import bigquery as commands
from googlecloudsdk.third_party.apitools.base.py import exceptions


class TablesDescribe(base.Command):
  """Displays metadata about a table or view.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'table_or_view', help='The table or view to be described.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      A Table message.
    """
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    resource = resource_parser.Parse(
        args.table_or_view, collection='bigquery.tables')
    reference = message_conversions.TableResourceToReference(
        bigquery_messages, resource)
    request = bigquery_messages.BigqueryTablesGetRequest(
        projectId=reference.projectId,
        datasetId=reference.datasetId,
        tableId=reference.tableId)
    try:
      return apitools_client.tables.Get(request)
    except exceptions.HttpError as server_error:
      raise bigquery.Error.ForHttpError(server_error)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    log.out.Print(result)
