# Copyright 2015 Google Inc. All Rights Reserved.

"""A library used to interact with Operations objects."""

from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import retry

from googlecloudsdk.functions.lib import exceptions
from googlecloudsdk.functions.lib import util

MAX_WAIT_MS = 380000
WAIT_CEILING_MS = 2000
SLEEP_MS = 1000


def _GetOperationStatus(client, get_request, progress_tracker=None):
  """Helper function for getting the status of an operation.

  Args:
    client: The client used to make requests.
    get_request: A GetOperationRequest message.
    progress_tracker: console_io.ProgressTracker, A reference for the progress
        tracker to tick, in case this function is used in a Retryer.

  Returns:
    True if the operation succeeded without error.
    False if the operation is not yet done.

  Raises:
    FunctionsError: If the operation is finished with error.
  """
  if progress_tracker:
    progress_tracker.Tick()
  op = client.operations.Get(get_request)
  if op.done and op.error:
    raise exceptions.FunctionsError(util.GetOperationError(op.error))
  return op.done


def _WaitForOperation(client, get_request, message):
  """Wait for an operation to complete.

  No operation is done instantly. Wait for it to finish following this logic:
  * we wait 1s (jitter is also 1s)
  * we query service
  * if the operation is not finished we loop to first point
  * wait limit is 380s - if we get to that point it means something is wrong
        and we can throw an exception

  Args:
    client:  The client used to make requests.
    get_request: A GetOperatioRequest message.
    message: str, The string to print while polling.

  Returns:
    True if the operation succeeded without error.

  Raises:
    FunctionsError: If the operation takes more than 380s.
  """

  with console_io.ProgressTracker(message, autotick=False) as pt:
    # This is actually linear retryer.
    retryer = retry.Retryer(exponential_sleep_multiplier=1,
                            max_wait_ms=MAX_WAIT_MS,
                            wait_ceiling_ms=WAIT_CEILING_MS)
    try:
      retryer.RetryOnResult(_GetOperationStatus,
                            [client, get_request],
                            {'progress_tracker': pt},
                            should_retry_if=None,
                            sleep_ms=SLEEP_MS)
    except retry.WaitException:
      raise exceptions.FunctionsError(
          'Operation {0} is taking too long'.format(get_request.name))


def Wait(operation, messages, client):
  """Initialize waiting for operation to finish.

  Generate get request based on the operation and wait for an operation
  to complete.

  Args:
    operation: The operation which we are waiting for.
    messages: GCF messages module.
    client: GCF client module.

  Raises:
    FunctionsError: If the operation takes more than 360s.
  """
  request = messages.CloudfunctionsOperationsGetRequest()
  request.name = 'operations/{0}'.format(operation.name)
  _WaitForOperation(client, request, 'Waiting for operation to finish')
