# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery tables show-rows.
"""

from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.api_lib.bigquery import schema_and_rows
from googlecloudsdk.calliope import base
from googlecloudsdk.surface import bigquery as commands


class TablesShowRows(base.Command):
  """Displays selected rows in a specified table.

  (This command does not apply to views.)
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--limit',
        type=int,
        default=bigquery.DEFAULT_RESULTS_LIMIT,
        help='The maximum number of rows to display.')
    parser.add_argument(
        '--start-row',
        type=int,
        default=0,
        help='The number of rows to skip before showing table data.')
    parser.add_argument('table', help='The table whose rows are to be shown.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      A SchemaAndRows object.
    """
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    table_reference = resource_parser.Parse(args.table,
                                            collection='bigquery.tables')
    return schema_and_rows.GetTableSchemaAndRows(
        apitools_client, bigquery_messages, table_reference, args.start_row,
        args.limit)

  def Display(self, args, field_schemas_and_rows):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      field_schemas_and_rows: A SchemaAndRows object.
    """
    schema_and_rows.DisplaySchemaAndRows(field_schemas_and_rows)
