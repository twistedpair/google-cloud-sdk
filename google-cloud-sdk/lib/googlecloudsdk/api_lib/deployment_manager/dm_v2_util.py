# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Common helper methods for DeploymentManager V2 Deployments."""

import json
import sys
import time
from googlecloudsdk.api_lib.deployment_manager.exceptions import DeploymentManagerError
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope.exceptions import HttpException
from googlecloudsdk.core import log
from googlecloudsdk.core import resource_printer
from googlecloudsdk.core.console import console_io
from googlecloudsdk.third_party.apitools.base.py import exceptions as apitools_exceptions


def PrettyPrint(resource, print_format='json'):
  """Prints the given resource."""
  resource_printer.Print(
      resources=[resource],
      print_format=print_format,
      out=log.out)


def GetError(error, verbose=False):
  """Returns a ready-to-print string representation from the http response.

  Args:
    error: A string representing the raw json of the Http error response.
    verbose: Whether or not to print verbose messages [default false]

  Returns:
    A ready-to-print string representation of the error.
  """
  data = json.loads(error.content)
  if verbose:
    PrettyPrint(data)
  code = data['error']['code']
  message = data['error']['message']
  return 'ResponseError: code={0}, message={1}'.format(code, message)


def _SanitizeLimitFlag(limit):
  """Sanitizes and returns a limit flag value.

  Args:
    limit: the limit flag value to sanitize.
  Returns:
    Sanitized limit flag value.
  Raises:
    DeploymentManagerError: if the provided limit flag value is not a positive
        integer.
  """
  if limit is None:
    limit = sys.maxint
  else:
    if limit > sys.maxint:
      limit = sys.maxint
    elif limit <= 0:
      raise DeploymentManagerError(
          '--limit must be a positive integer; received: {0}'.format(limit))
  return limit


def WaitForOperation(operation_name, project, context, operation_description,
                     timeout=None):
  """Wait for an operation to complete.

  Polls the operation requested approximately every second, showing a
  progress indicator. Returns when the operation has completed.

  Args:
    operation_name: The name of the operation to wait on, as returned by
        operations.list.
    project: The name of the project that this operation belongs to.
    context: Context object with messages and client to access the
        deploymentmanager service.
    operation_description: A short description of the operation to wait on,
        such as 'create' or 'delete'. Will be displayed to the user.
    timeout: Optional (approximate) timeout in seconds, after which wait
        will return failure.

  Raises:
      HttpException: A http error response was received while executing api
          request. Will be raised if the operation cannot be found.
      DeploymentManagerError: The operation finished with error(s) or exceeded
          the timeout without completing.
  """
  client = context['deploymentmanager-client']
  messages = context['deploymentmanager-messages']
  ticks = 0
  message = ('Waiting for '
             + ('{0} '.format(operation_description)
                if operation_description else '')
             + operation_name)
  with console_io.ProgressTracker(message, autotick=False) as ticker:
    while timeout is None or ticks < timeout:
      ticks += 1

      try:
        operation = client.operations.Get(
            messages.DeploymentmanagerOperationsGetRequest(
                project=project,
                operation=operation_name,
            )
        )
      except apitools_exceptions.HttpError as error:
        raise HttpException(GetError(error))
      ticker.Tick()
      # Operation status will be one of PENDING, RUNNING, DONE
      if operation.status == 'DONE':
        if operation.error:
          raise DeploymentManagerError(
              'Error in Operation ' + operation_name + ': '
              + str(operation.error))
        else:  # Operation succeeded
          return
      time.sleep(1)  # wait one second and try again
    # Timeout exceeded
    raise DeploymentManagerError(
        'Wait for Operation ' + operation_name + ' exceeded timeout.')


def PrintTable(header, resource_list):
  """Print a table of results with the specified columns.

  Prints a table whose columns are the proto fields specified in the
  header list. Any fields which cannot be found are printed as empty.

  Args:
    header: A list of strings which are the field names to include in the
        table. Must match field names in the resource_list items.
    resource_list: A list of resource objects, each corresponding to a row
        in the table to print.
  """
  printer = resource_printer.TablePrinter(out=log.out)
  printer.AddRow(header)
  for resource in resource_list:
    printer.AddRow([resource[column] if column in resource else ''
                    for column in header])
  printer.Print()


def _GetNextPage(list_method, request, resource_field, page_token=None,
                 limit=None):
  """Helper method to get the next set of paginated results.

  Args:
    list_method: The method that will execute the list request.
    request: The list request ready to be executed, possibly missing the page
        token.
    resource_field: The field name of the resources in the list results.
    page_token: The page token string to pass into the request, or None
        if no page token should be included.
    limit: Optional limit on how many resources to request.

  Returns:
    A tuple containing the list of results and the page token in the
    list response, or None if no page token was in the response.
  """
  if page_token:
    request.pageToken = page_token
  if limit:
    request.maxResults = limit
  try:
    response = list_method(request)
    return_token = response.nextPageToken  # may be None
    results = (response.get_assigned_value(resource_field)
               if response.get_assigned_value(resource_field)
               else [])
    return (results, return_token)
  except apitools_exceptions.HttpError as error:
    raise exceptions.HttpException(GetError(error))
