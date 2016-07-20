# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Facilities for fetching and displaying table rows and field names."""

from apitools.base.py import exceptions
from apitools.base.py import list_pager

from googlecloudsdk.api_lib.bigquery import bigquery

_REQUESTED_PAGE_SIZE = None  # Use server default.


class SchemaAndRows(object):
  """A pair consisting of iterables over field schemas and rows.

  The schema field is an iterable over TableFieldSchema messages.
  The rows field is an iterable over TableRow messages.
  """

  def __init__(self, schema, rows):
    self.schema = schema
    self.rows = rows

  def PrepareForDisplay(self):
    """Prepare for display by resource printer. Convert each row to a map.

    Yields:
      A map representing a row.
    """
    try:
      for tr in self.rows:
        row = [cell.v for cell in tr.f]
        r_map = {}
        for i, field_schema in enumerate(self.schema):
          r_map[field_schema.name] = row[i].string_value if row[i] else None
        yield r_map
    except exceptions.HttpError as server_error:
      raise bigquery.Error.ForHttpError(server_error)

  def GetDefaultFormat(self):
    """Return the default format string for the schema.

    Returns:
      The default format string for the schema.
    """
    names = [x.name for x in self.schema]
    return 'table(' + ','.join(names) + ')'


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
  except exceptions.HttpError as server_error:
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
  except exceptions.HttpError as server_error:
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
