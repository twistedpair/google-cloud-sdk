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
"""Common utility functions for Updater."""

import json

from googlecloudsdk.api_lib.compute import time_utils
from googlecloudsdk.core import apis as core_apis
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.resource import resource_printer


def GetApiClientInstance():
  return core_apis.GetClientInstance('replicapoolupdater', 'v1beta1')


def GetApiMessages():
  return core_apis.GetMessagesModule('replicapoolupdater', 'v1beta1')


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


def PrettyPrint(resource, print_format='json'):
  """Prints the given resource."""
  resource_printer.Print(resources=[resource], print_format=print_format)
