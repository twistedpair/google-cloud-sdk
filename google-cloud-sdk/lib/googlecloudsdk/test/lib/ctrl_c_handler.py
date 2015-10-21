# Copyright 2015 Google Inc. All Rights Reserved.

"""Context manager to help with Control-C handling during critical commands."""

import signal

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log

from googlecloudsdk.test.lib import exit_code


class CancellableTestSection(object):
  """Cancel a test matrix if CTRL-C is typed during a section of code.

  While within this context manager, the CTRL-C signal is caught and a test
  matrix is cancelled. This should only be used with a section of code where
  the test matrix is running.
  """

  def __init__(self, matrix_id, testing_api_helper):
    self._old_sigint_handler = None
    self._old_sigterm_handler = None
    self._matrix_id = matrix_id
    self._testing_api_helper = testing_api_helper

  def __enter__(self):
    self._old_sigint_handler = signal.getsignal(signal.SIGINT)
    self._old_sigterm_handler = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, self._Handler)
    signal.signal(signal.SIGTERM, self._Handler)
    return self

  def __exit__(self, typ, value, traceback):
    signal.signal(signal.SIGINT, self._old_sigint_handler)
    signal.signal(signal.SIGTERM, self._old_sigterm_handler)
    return False

  def _Handler(self, unused_signal, unused_frame):
    log.status.write('\n\nCancelling test [{id}]...\n\n'
                     .format(id=self._matrix_id))
    self._testing_api_helper.CancelTestMatrix(self._matrix_id)
    log.status.write('\nTest matrix has been cancelled.\n')
    raise exceptions.ExitCodeNoError(exit_code=exit_code.MATRIX_CANCELLED)
