# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery tables add-rows.
"""

import sys
from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.api_lib.bigquery import bigquery_json_object_messages
from googlecloudsdk.api_lib.bigquery import message_conversions
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.surface import bigquery as commands
from googlecloudsdk.third_party.apitools.base.py import exceptions


# If the following variable is set to an int value, the add-rows operation will
# be split over multiple server requests, each containg at most that many rows.
_MAX_ROWS_PER_REQUEST = None


class TablesAddRows(base.Command):
  """Adds records specified in a file to a specified existing table.

  The records are specified in the file as newline delimited JSON.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--file',
        help='The file containing the newline-delimited JSON. '
        'Defaults to stdin.')
    parser.add_argument(
        'target_table',
        help='The table into which the rows are to be inserted.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      None
    """
    try:
      if args.file:
        with open(args.file, 'r') as json_file:
          return self._DoAddRows(json_file, args)
      else:
        return self._DoAddRows(sys.stdin, args)
    except IOError as e:
      raise bigquery.ClientError(e)

  def _DoAddRows(self, json_file, args):
    """Add rows from json_file to args.target_table."""
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    resource = resource_parser.Parse(
        args.target_table, collection='bigquery.tables')
    reference = message_conversions.TableResourceToReference(
        bigquery_messages, resource)
    message_builder = bigquery_json_object_messages.MessageBuilder(
        bigquery_messages)

    batch = []
    lineno = 0
    errors_found = False

    for line in json_file:
      lineno += 1
      trimmed_line = line.strip()
      if trimmed_line:
        try:
          parsed_row = message_builder.Build(trimmed_line)
        except bigquery.ClientError as e:
          raise bigquery.Error(
              'Line {num}: {msg}'.format(num=lineno, msg=str(e)), None, [])
        batch.append(parsed_row)
        if _MAX_ROWS_PER_REQUEST and (len(batch) == _MAX_ROWS_PER_REQUEST):
          result = TablesAddRows._InsertTableRows(
              reference, batch, apitools_client, bigquery_messages)
          del batch[:]
          if result.insertErrors:
            errors_found = True
            break

    if lineno == 0:
      log.status.Print('JSON file was empty.')
      return

    if batch and not errors_found:
      result = TablesAddRows._InsertTableRows(
          reference, batch, apitools_client, bigquery_messages)
      errors_found = bool(result.insertErrors)

    if errors_found:
      for entry in result.insertErrors:
        log.err.Print('Record {0} could not be inserted:'.format(entry.index))
        for error in entry.errors:
          log.err.Print('\t{0}: {1}'.format(error.reason, error.message))
      raise bigquery.Error('Rows not added')
    else:
      if not args.quiet:
        log.status.Print('Rows added successfully.')

  @staticmethod
  def _InsertTableRows(
      table_ref, row_dicts, apitools_client, bigquery_messages):
    """Insert rows into a table.

    Args:
      table_ref: table reference into which rows are to be inserted.
      row_dicts: array of JSON dicts each representing a row.
      apitools_client: the client to be used for API calls
      bigquery_messages: the messages module for API calls

    Returns:
      a TableDataInsertAllResponse message
    """
    request_row_list = [
        bigquery_messages.TableDataInsertAllRequest.RowsValueListEntry(
            json=row_dict)
        for row_dict in row_dicts]
    inner_request = bigquery_messages.TableDataInsertAllRequest(
        rows=request_row_list)
    outer_request = bigquery_messages.BigqueryTabledataInsertAllRequest(
        projectId=table_ref.projectId,
        datasetId=table_ref.datasetId,
        tableId=table_ref.tableId,
        tableDataInsertAllRequest=inner_request)
    try:
      return apitools_client.tabledata.InsertAll(outer_request)
    except exceptions.HttpError as server_error:
      raise bigquery.Error.ForHttpError(server_error)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    pass
