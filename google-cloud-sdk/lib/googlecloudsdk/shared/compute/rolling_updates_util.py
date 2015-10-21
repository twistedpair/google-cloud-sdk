# Copyright 2014 Google Inc. All Rights Reserved.
"""Common utility functions for Updater."""

import json
import sys

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resource_printer
from googlecloudsdk.core.console import console_io
from googlecloudsdk.shared.compute import time_utils


def WaitForOperation(client, operation_ref, message):
  """Waits until the given operation finishes.

  Wait loop terminates when the operation's status becomes 'DONE'.

  Args:
    client: interface to the Cloud Updater API
    operation_ref: operation to poll
    message: message to be displayed by progress tracker

  Returns:
    True iff the operation finishes with success
  """
  with console_io.ProgressTracker(message, autotick=False) as pt:
    while True:
      operation = client.zoneOperations.Get(operation_ref.Request())
      if operation.error:
        return False
      if operation.status == 'DONE':
        return True
      pt.Tick()
      time_utils.Sleep(2)


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


def SanitizeLimitFlag(limit):
  """Sanitizes and returns a limit flag value.

  Args:
    limit: the limit flag value to sanitize.
  Returns:
    Sanitized limit flag value.
  Raises:
    ToolException: if the provided limit flag value is not a positive integer
  """
  if limit is None:
    limit = sys.maxint
  else:
    if limit > sys.maxint:
      limit = sys.maxint
    elif limit <= 0:
      raise exceptions.ToolException(
          '--limit must be a positive integer; received: {0}'
          .format(limit))
  return limit


def PrettyPrint(resource, print_format='json'):
  """Prints the given resource."""
  resource_printer.Print(
      resources=[resource],
      print_format=print_format,
      out=log.out)


def PrintTable(resources, resource_type):
  """Prints a table of the given resources.

  Args:
    resources: a list of resources to print into a table
    resource_type: the type of the resources to print, e.g. 'replica' or
      'replica-pool'

  Raises:
    ValueError: if an unsupported resource_type is provided
  """
  printer = resource_printer.TablePrinter(out=log.out)

  if not resources:
    return

  if resource_type == 'replica':
    header = ['name', 'status', 'templateVersion']
    printer.AddRow(header)
    for resource in resources:
      row = []
      row.append(resource['name'])
      row.append(resource['status']['state'])
      row.append(resource['status']['templateVersion'])
      printer.AddRow(row)
  elif resource_type == 'replica-pool':
    header = ['name', 'currentNumReplicas']
    printer.AddRow(header)
    for resource in resources:
      row = []
      row.append(resource['name'])
      row.append(str(resource['currentNumReplicas']))
      printer.AddRow(row)
  else:
    raise ValueError('Unsupported resource_type: {0}'.format(resource_type))

  printer.Print()
