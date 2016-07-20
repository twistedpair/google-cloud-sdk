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

"""Bigquery apis layer."""

import itertools
import json
import textwrap
import time

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import list_pager

from googlecloudsdk.api_lib.bigquery import message_conversions
from googlecloudsdk.core import apis as core_apis
from googlecloudsdk.core import exceptions

DEFAULT_RESULTS_LIMIT = 100


def CurrentTimeInSec():
  """Returns current time in fractional seconds."""
  return time.time()


def Wait(secs_to_wait):
  """Blocks for specified number of fractional seconds."""
  time.sleep(secs_to_wait)


class Bigquery(object):
  """Base class for bigquery api wrappers."""
  _client = None
  _resource_parser = None

  @classmethod
  def SetApiEndpoint(cls):
    cls._client = core_apis.GetClientInstance('bigquery', 'v2')
    cls._messages = core_apis.GetMessagesModule('bigquery', 'v2')

  @classmethod
  def SetResourceParser(cls, parser):
    cls._resource_parser = parser

  @classmethod
  def Clear(cls):
    cls._client = None
    cls._resource_parser = None


class Project(Bigquery):
  """Abstracts bigquery project."""

  def __init__(self, project_id):
    self.id = project_id

  # TODO(user): do not expose backend representation.
  def GetCurrentRawJobsListGenerator(self, all_users, max_results):
    """Returns list of jobs using backend representation for this project."""

    # TODO(user): add back state filter support once b/22224569 is resolved.
    # state_enum = messages.BigqueryJobsListRequest.StateFilterValueValuesEnum
    # state_map = {
    #    'done': state_enum.done,
    #    'running': state_enum.running,
    #    'pending': state_enum.pending,
    # }
    # job_state_filter = [state_map[value] for value in state_filter]
    request = self._messages.BigqueryJobsListRequest(
        projectId=self.id,
        allUsers=all_users,
        projection=(self._messages.BigqueryJobsListRequest
                    .ProjectionValueValuesEnum.full))
    return list_pager.YieldFromList(
        self._client.jobs,
        request,
        limit=max_results,
        batch_size=None,  # Use server default.
        field='jobs')


class Job(Bigquery):
  """Abstracts bigquery job."""

  def __init__(self, project, job_id):
    self.project = project
    self.id = job_id
    self._job = None

  @classmethod
  def ResolveFromId(cls, job_id):
    """Resolve a job given its id, uri or collection path."""
    resource = cls._resource_parser.Parse(job_id,
                                          collection='bigquery.jobs')
    return cls(Project(resource.projectId), resource.jobId)

  def _Refresh(self):
    """Sync this object with backend."""
    request = self._messages.BigqueryJobsGetRequest(projectId=self.project.id,
                                                    jobId=self.id)
    try:
      self._job = self._client.jobs.Get(request)
    except apitools_exceptions.HttpError as server_error:
      raise Error.ForHttpError(server_error)

  # TODO(user): do not expose backend representation.
  def GetRaw(self):
    """Return backend representation for this job."""
    if not self._job:
      self._Refresh()
    return self._job

  def GetQueryResults(self, start_row=None, max_rows=None):
    """Issues request to backend to get query results for this job.

    This method uses apitools pager for returned rows. It intercepts first
    result to extract the schema, and converts all api returned rows into
    python tuples.

    Args:
      start_row: int, 0-based index of starting row.
      max_rows: int, maximum number of rows to fetch.
    Raises:
      Error: various bigquery.Error on service errors.
    Returns:
      iterable QueryResults object with schema.
    """
    request = self._messages.BigqueryJobsGetQueryResultsRequest(
        projectId=self.project.id,
        jobId=self.id,
        startIndex=start_row)

    class ServiceQueryWithSchema(object):
      """Mock of client.job which intercepts first response.

      This allows schema to be read picked up from the response.
      """

      def __init__(self, thisclient):
        self.schema = []
        self._client = thisclient

      def WrappedGetQueryResults(self, request, *args, **kwargs):
        # Make actual bigquery API call.
        response = self._client.jobs.GetQueryResults(request, *args, **kwargs)
        if not self.schema:
          self.schema = response.schema.fields
        return response

    service = ServiceQueryWithSchema(self._client)

    # Create paging generator for client.jobs.GetQueryResults()[].rows.
    rows = list_pager.YieldFromList(
        service,
        request,
        limit=max_rows,
        batch_size=None,   # Use server default.,
        method='WrappedGetQueryResults',
        field='rows',
        next_token_attribute='pageToken')

    # Reinterpret results from json to python tuples.
    def Yield():
      try:
        for r in rows:
          # TODO(user): handle various value types.
          yield tuple((cell.v.string_value or
                       cell.v.integer_value)
                      for cell in r.f)
      except apitools_exceptions.HttpError as server_error:
        raise Error.ForHttpError(server_error)
    result_iter = Yield()
    try:
      # Read in first result so that we can get schema in service object.
      head = [result_iter.next()]
    except StopIteration:
      head = []
    schema = [(f.name, f.type) for f in service.schema]
    return QueryResults(schema, itertools.chain(head, result_iter))


class QueryResults(object):
  """Encapsulates query result schema and row iterator."""

  def __init__(self, schema, result_iterator):
    self._schema = schema
    self._result_iterator = result_iterator

  def GetSchema(self):
    """Returns list of tuples [(name, type), ]."""
    return self._schema

  def __iter__(self):
    """Returns iterator over tuples where tuple is same length as schema."""
    return self._result_iterator

  def GetColumnFetchers(self):
    """Returns mapping of field --> func(row) to fetch value at given field."""
    def CreateColumnFetcher(col_num):
      def ColumnFetcher(row):
        return row[col_num] if row[col_num] is not None else 'null'
      return ColumnFetcher
    return [(field[0].upper(), CreateColumnFetcher(i))
            for i, field in enumerate(self._schema)]


class Error(exceptions.Error):
  """Root superclass for exceptions unique to gcloud bigquery."""

  @staticmethod
  def ForHttpError(server_error):
    content_type = server_error.response.get('content-type', '')
    if content_type.startswith('application/json'):
      server_error_dict = json.loads(server_error.content)
      return Error.Create(
          server_error_dict['error']['errors'][0], server_error, [])
    else:
      return InterfaceError(
          'Error reported by server with missing error fields. '
          'Server returned: {0}'.format(server_error))

  @staticmethod
  def Create(error, server_error, error_ls, job_ref=None):
    """Returns a Error for json error embedded in server_error.

    If error_ls contains any errors other than the given one, those
    are also included in the returned message.

    Args:
      error: The primary error to convert.
      server_error: The error returned by the server. (This is only used
        in the case that error is malformed.)
      error_ls: Additional errors to include in the error message.
      job_ref: JobReference, if this is an error associated with a job.

    Returns:
      Error representing error.
    """
    reason = error['reason']
    if job_ref:
      message = 'Error processing {job}: {explanation}'.format(
          job=message_conversions.JobReferenceToResource(job_ref),
          explanation=error['message'])
    else:
      message = error['message']
    # We don't want to repeat the "main" error message.
    new_errors = [err for err in error_ls if err != error]
    if new_errors:
      message += '\nFailure details:\n'
      message += '\n'.join(
          textwrap.fill(
              ': '.join(filter(None, [err['location'], err['message']])),
              initial_indent=' - ',
              subsequent_indent='   ')
          for err in new_errors)
    if not reason or not message:
      return InterfaceError(
          'Error reported by server with missing error fields. '
          'Server returned: {0}'.format(str(server_error)))
    if reason == 'notFound':
      return NotFoundError(message, error, error_ls, job_ref=job_ref)
    if reason == 'duplicate':
      return DuplicateError(message, error, error_ls, job_ref=job_ref)
    if reason == 'backendError':
      return BackendError(
          message, error, error_ls, job_ref=job_ref)
    # We map the less interesting errors to ServiceError. These include
    # accessDenied, termsOfServiceNotAccepted, invalidQuery
    return ServiceError(message, error, error_ls, job_ref=job_ref)


class ServiceError(Error):
  """Base class of Bigquery-specific error responses.

  The BigQuery server received request and returned an error.
  """

  def __init__(self, message, error, error_list, job_ref=None, *args, **kwds):
    """Initializes a ServiceError.

    Args:
      message: A user-facing error message.
      error: The error dictionary, code may inspect the 'reason' key.
      error_list: A list of additional entries, for example a load job
        may contain multiple errors here for each error encountered
        during processing.
      job_ref: Optional JobReference, if this error was encountered
        while processing a job.
      *args: -
      **kwds: -
    """
    super(ServiceError, self).__init__(message, *args, **kwds)
    self.error = error
    self.error_list = error_list
    self.job_ref = job_ref

  def __repr__(self):
    return '{0}: error={1}, error_list={2}, job_ref={3}'.format(
        self.__class__.__name__, self.error, self.error_list, self.job_ref)


class CommunicationError(Error):
  """Error communicating with the server."""
  pass


class InterfaceError(Error):
  """Response from server missing required fields."""
  pass


class NotFoundError(ServiceError):
  """The requested resource or identifier was not found."""
  pass


class DuplicateError(ServiceError):
  """The requested resource or identifier already exists."""
  pass


class BackendError(ServiceError):
  """A backend error typically corresponding to retriable HTTP 503 failures."""
  pass


class ClientError(Error):
  """Invalid use of BigqueryClient."""
  pass


class ClientConfigurationError(ClientError):
  """Invalid configuration of BigqueryClient."""
  pass


class SchemaError(ClientError):
  """Error in locating or parsing the schema."""
  pass


class TimeoutError(ServiceError):
  """A TimeoutError exception that is handled by gcloud as a Error."""
  pass
