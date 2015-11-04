# Copyright 2015 Google Inc. All Rights Reserved.

"""Facilities for fetching and displaying table rows and field names."""

from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.core.console import console_io
from googlecloudsdk.third_party.apitools.base import py as apitools_base
from googlecloudsdk.third_party.apitools.base.py import list_pager


_REQUESTED_PAGE_SIZE = None  # Use server default.


class SchemaAndRows(object):
  """A pair consisting of iterables over field schemas and rows.

  The schema field is an iterable over TableFieldSchema messages.
  The rows field is an iterable over TableRow messages.
  """

  def __init__(self, schema, rows):
    self.schema = schema
    self.rows = rows


def GetJobSchemaAndRows(
    apitools_client, bigquery_messages, job_reference, start_row,
    max_rows):
  """Fetch selected rows and a schema from the output of a query job.

  Args:
    apitools_client: The client used to fetch from the query-job output.
    bigquery_messages: The messages module used in API calls.
    job_reference: A JobReference message identifying the query job.
    start_row: The 0-based index of the first selected row.
    max_rows: The maximum number of selected rows.

  Returns:
    A SchemaAndRows object corresponding to the schema and the selected rows.
  """
  request_for_schema = bigquery_messages.BigqueryJobsGetQueryResultsRequest(
      projectId=job_reference.projectId,
      jobId=job_reference.jobId,
      maxResults=1)
  try:
    schema = apitools_client.jobs.GetQueryResults(request_for_schema).schema
  except apitools_base.HttpError as server_error:
    raise bigquery.Error.ForHttpError(server_error)
  request_for_rows = bigquery_messages.BigqueryJobsGetQueryResultsRequest(
      projectId=job_reference.projectId,
      jobId=job_reference.jobId,
      startIndex=start_row)
  return _GetSchemaAndRows(
      apitools_client.jobs, 'GetQueryResults', schema, request_for_rows,
      max_rows)


def GetTableSchemaAndRows(
    apitools_client, bigquery_messages, table_reference, start_row,
    max_rows):
  """Fetch selected rows and a schema from a table.

  Args:
    apitools_client: The client used to fetch from the query-job output.
    bigquery_messages: The messages module used in API calls.
    table_reference: A TableReference message identifying the table.
    start_row: The 0-based index of the first selected row.
    max_rows: The maximum number of selected rows.

  Returns:
    A SchemaAndRows object corresponding to the schema and the selected rows.
  """
  request_for_schema = bigquery_messages.BigqueryTablesGetRequest(
      projectId=table_reference.projectId,
      datasetId=table_reference.datasetId,
      tableId=table_reference.tableId)
  try:
    schema = apitools_client.tables.Get(request_for_schema).schema
  except apitools_base.HttpError as server_error:
    raise bigquery.Error.ForHttpError(server_error)
  request_for_rows = bigquery_messages.BigqueryTabledataListRequest(
      projectId=table_reference.projectId,
      datasetId=table_reference.datasetId,
      tableId=table_reference.tableId,
      startIndex=start_row)
  return _GetSchemaAndRows(
      apitools_client.tabledata, 'List', schema, request_for_rows, max_rows)


def _GetSchemaAndRows(service, method, schema, request_for_rows, max_rows):
  """Fetch selected rows and schema from a query-job result or a table.

  Args:
    service: a service of the API client, either JobsService or TableDataService
    method: the name of the method called to retrieve multiple items, either
      'GetQueryResults' for JobsService or 'List' for TableDataService
    schema: a TableSchema corresponding to the rows
    request_for_rows: the request object passed to the method
    max_rows: the number of rows to return, if there are that many rows
  Returns:
    a SchemaAndRows object
  """
  rows = list_pager.YieldFromList(
      service,
      request_for_rows,
      limit=max_rows,
      batch_size=_REQUESTED_PAGE_SIZE,
      method=method,
      field='rows',
      next_token_attribute='pageToken')

  return SchemaAndRows(schema.fields, rows)


def DisplaySchemaAndRows(schema_and_rows):
  """Display a SchemaAndRows object as a gcloud table.

  The heading for each column is a field name.

  Args:
    schema_and_rows: The SchemaAndRows object.
  """
  # Convert the iterable over TableRow objects into a list of lists, where
  # each inner list corresponds to a row, and contains JsonValue objects
  # for the values in the row. This is the point at which we invoke the
  # generator created by the call on list_pager.YieldFromList from
  # GetJobSchemaAndRows, so this is where we catch any exception from the API
  # call made by that generator.
  try:
    rows = [[cell.v for cell in tr.f] for tr in schema_and_rows.rows]
  except apitools_base.HttpError as server_error:
    raise bigquery.Error.ForHttpError(server_error)

  def CreateColumnFetcher(col_num):
    def ColumnFetcher(row):
      return row[col_num].string_value if row[col_num] else 'null'
    return ColumnFetcher
  col_fetchers = [(field_schema.name.upper(), CreateColumnFetcher(i))
                  for i, field_schema in enumerate(schema_and_rows.schema)]
  # The variable col_fetchers is a list of pairs. The first component of each
  # pair is the name of a field, and the second component of each pair is a
  # function to which a row is passed. Each row passed to such a function is a
  # list of JsonValue objects, and each of these JsonValue objects has its
  # string_value field set.

  console_io.PrintExtendedList(rows, col_fetchers)
