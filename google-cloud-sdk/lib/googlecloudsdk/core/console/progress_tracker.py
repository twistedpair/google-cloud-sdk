# -*- coding: utf-8 -*- #
# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Progress Tracker for Cloud SDK."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import os
import signal
import sys
import threading
import time

from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.console import multiline

import six


def ProgressTracker(
    message=None, autotick=True, detail_message_callback=None, tick_delay=1,
    interruptable=True,
    aborted_message=console_io.OperationCancelledError.DEFAULT_MESSAGE):
  """A context manager for telling the user about long-running progress.

  Args:
    message: str, The message to show next to the spinner.
    autotick: bool, True to have the spinner tick on its own. Otherwise, you
      need to call Tick() explicitly to move the spinner.
    detail_message_callback: func, A no argument function that will be called
      and the result appended to message each time it needs to be printed.
    tick_delay: float, The amount of time to wait between ticks, in second.
    interruptable: boolean, True if the user can ctrl-c the operation. If so,
      it will stop and will report as aborted. If False, a message will be
      displayed saying that it cannot be cancelled.
    aborted_message: str, A custom message to put in the exception when it is
      cancelled by the user.

  Returns:
    The progress tracker.
  """
  style = properties.VALUES.core.interactive_ux_style.Get()
  if style == properties.VALUES.core.InteractiveUXStyles.OFF.name:
    return _NoOpProgressTracker(interruptable, aborted_message)
  elif style == properties.VALUES.core.InteractiveUXStyles.TESTING.name:
    return _StubProgressTracker(message, interruptable, aborted_message)
  else:
    is_tty = console_io.IsInteractive(error=True)
    tracker_cls = (_NormalProgressTracker if is_tty
                   else _NonInteractiveProgressTracker)
    return tracker_cls(
        message, autotick, detail_message_callback, tick_delay, interruptable,
        aborted_message)


class _BaseProgressTracker(six.with_metaclass(abc.ABCMeta, object)):
  """A context manager for telling the user about long-running progress."""

  def __init__(self, message, autotick, detail_message_callback, tick_delay,
               interruptable, aborted_message):
    self._stream = sys.stderr
    if message is None:
      self._spinner_only = True
      self._message = ''
      self._prefix = ''
    else:
      self._spinner_only = False
      self._message = message
      self._prefix = message + '...'
    self._detail_message_callback = detail_message_callback
    self._ticks = 0
    self._done = False
    self._lock = threading.Lock()
    self._tick_delay = tick_delay
    self._ticker = None
    self._output_enabled = log.IsUserOutputEnabled()
    # Don't bother autoticking if we aren't going to print anything.
    self.__autotick = autotick and self._output_enabled
    self._interruptable = interruptable
    self._aborted_message = aborted_message
    self._old_signal_handler = None
    self._symbols = console_attr.GetConsoleAttr().GetProgressTrackerSymbols()

  @property
  def _autotick(self):
    return self.__autotick

  def _GetPrefix(self):
    if self._detail_message_callback:
      detail_message = self._detail_message_callback()
      if detail_message:
        return self._prefix + ' ' + detail_message + '...'
    return self._prefix

  def _SetUpSignalHandler(self):
    """Sets up a signal handler for handling SIGINT."""
    def _CtrlCHandler(unused_signal, unused_frame):
      if self._interruptable:
        raise console_io.OperationCancelledError(self._aborted_message)
      else:
        with self._lock:
          sys.stderr.write('\n\nThis operation cannot be cancelled.\n\n')
    try:
      self._old_signal_handler = signal.signal(signal.SIGINT, _CtrlCHandler)
      self._restore_old_handler = True
    except ValueError:
      # Only works in the main thread. Gcloud does not run in the main thread
      # in gcloud interactive.
      self._restore_old_handler = False

  def _TearDownSignalHandler(self):
    if self._restore_old_handler:
      try:
        signal.signal(signal.SIGINT, self._old_signal_handler)
      except ValueError:
        pass  # only works in main thread

  def __enter__(self):
    # Setup signal handlers
    self._SetUpSignalHandler()

    log.file_only_logger.info(self._GetPrefix())
    self._Print()
    if self._autotick:
      def Ticker():
        while True:
          _SleepSecs(self._tick_delay)
          if self.Tick():
            return
      self._ticker = threading.Thread(target=Ticker)
      self._ticker.start()
    return self

  def __exit__(self, unused_ex_type, exc_value, unused_traceback):
    with self._lock:
      self._done = True
      # If an exception was raised during progress tracking, exit silently here
      # and let the appropriate exception handler tell the user what happened.
      if exc_value:
        # This is to prevent the tick character from appearing before 'failed.'
        # (ex. 'message...failed' instead of 'message.../failed.')
        if isinstance(exc_value, console_io.OperationCancelledError):
          self._Print('aborted by ctrl-c.\n')
        else:
          self._Print('failed.\n')
      elif not self._spinner_only:
        self._Print('done.\n')
    if self._ticker:
      self._ticker.join()
    self._TearDownSignalHandler()

  @abc.abstractmethod
  def Tick(self):
    """Give a visual indication to the user that some progress has been made.

    Output is sent to sys.stderr. Nothing is shown if output is not a TTY.

    Returns:
      Whether progress has completed.
    """
    pass

  @abc.abstractmethod
  def _Print(self, message=''):
    """Prints an update containing message to the output stream."""
    pass


class _NormalProgressTracker(_BaseProgressTracker):
  """A context manager for telling the user about long-running progress."""

  def __enter__(self):
    self._SetupOutput()
    return super(_NormalProgressTracker, self).__enter__()

  def _SetupOutput(self):
    def _FormattedCallback():
      if self._detail_message_callback:
        detail_message = self._detail_message_callback()
        if detail_message:
          return ' ' + detail_message + '...'
      return None

    self._console_output = multiline.SimpleSuffixConsoleOutput(self._stream)
    self._console_message = self._console_output.AddMessage(
        self._prefix, detail_message_callback=_FormattedCallback)

  def Tick(self):
    """Give a visual indication to the user that some progress has been made.

    Output is sent to sys.stderr. Nothing is shown if output is not a TTY.

    Returns:
      Whether progress has completed.
    """
    with self._lock:
      if not self._done:
        self._ticks += 1
        self._Print(self._symbols.spin_marks[
            self._ticks % len(self._symbols.spin_marks)])
    return self._done

  def _Print(self, message=''):
    """Reprints the prefix followed by an optional message.

    If there is a multiline message, we print the full message and every
    time the Prefix Message is the same, we only reprint the last line to
    account for a different 'message'. If there is a new message, we print
    on a new line.

    Args:
      message: str, suffix of message
    """
    if self._spinner_only or not self._output_enabled:
      return

    self._console_output.UpdateMessage(self._console_message, message)
    self._console_output.UpdateConsole()


class _NonInteractiveProgressTracker(_BaseProgressTracker):
  """A context manager for telling the user about long-running progress."""

  def Tick(self):
    """Give a visual indication to the user that some progress has been made.

    Output is sent to sys.stderr. Nothing is shown if output is not a TTY.

    Returns:
      Whether progress has completed.
    """
    with self._lock:
      if not self._done:
        self._Print('.')
    return self._done

  def _Print(self, message=''):
    """Reprints the prefix followed by an optional message.

    If there is a multiline message, we print the full message and every
    time the Prefix Message is the same, we only reprint the last line to
    account for a different 'message'. If there is a new message, we print
    on a new line.

    Args:
      message: str, suffix of message
    """
    if self._spinner_only or not self._output_enabled:
      return

    # Since we are not in a tty, print will be called twice outside of normal
    # ticking. The first time during __enter__, where the tracker message should
    # be outputted. The second time is during __exit__, where a status updated
    # contained in message will be outputted.
    display_message = self._GetPrefix()
    self._stream.write(message or display_message + '\n')
    return


class _NoOpProgressTracker(object):
  """A Progress tracker that doesn't do anything."""

  def __init__(self, interruptable, aborted_message):
    self._interruptable = interruptable
    self._aborted_message = aborted_message
    self._done = False

  def __enter__(self):
    def _CtrlCHandler(unused_signal, unused_frame):
      if self._interruptable:
        raise console_io.OperationCancelledError(self._aborted_message)
    self._old_signal_handler = signal.signal(signal.SIGINT, _CtrlCHandler)
    return self

  def Tick(self):
    return self._done

  def __exit__(self, exc_type, exc_val, exc_tb):
    self._done = True
    signal.signal(signal.SIGINT, self._old_signal_handler)


class _StubProgressTracker(_NoOpProgressTracker):
  """A Progress tracker that only prints deterministic start and end points.

  No UX about tracking should be exposed here. This is strictly for being able
  to tell that the tracker ran, not what it actually looks like.
  """

  def __init__(self, message, interruptable, aborted_message):
    super(_StubProgressTracker, self).__init__(interruptable, aborted_message)
    self._message = message or ''
    self._stream = sys.stderr

  def __exit__(self, exc_type, exc_val, exc_tb):
    if not exc_val:
      status = 'SUCCESS'
    elif isinstance(exc_val, console_io.OperationCancelledError):
      status = 'INTERRUPTED'
    else:
      status = 'FAILURE'

    self._stream.write(console_io.JsonUXStub(
        console_io.UXElementType.PROGRESS_TRACKER,
        message=self._message, status=status) + '\n')
    return super(_StubProgressTracker, self).__exit__(exc_type, exc_val, exc_tb)


def _SleepSecs(seconds):
  """Sleep int or float seconds. For mocking sleeps in this module."""
  time.sleep(seconds)


def CompletionProgressTracker(ofile=None, timeout=4.0, tick_delay=0.1,
                              background_ttl=60.0, autotick=True):
  """A context manager for visual feedback during long-running completions.

  A completion that exceeds the timeout is assumed to be refreshing the cache.
  At that point the progress tracker displays '?', forks the cache operation
  into the background, and exits.  This gives the background cache update a
  chance finish.  After background_ttl more seconds the update is forcibly
  exited (forced to call exit rather than killed by signal) to prevent hung
  updates from proliferating in the background.

  Args:
    ofile: The stream to write to.
    timeout: float, The amount of time in second to show the tracker before
      backgrounding it.
    tick_delay: float, The time in second between ticks of the spinner.
    background_ttl: float, The number of seconds to allow the completion to
      run in the background before killing it.
    autotick: bool, True to tick the spinner automatically.

  Returns:
    The completion progress tracker.
  """

  style = properties.VALUES.core.interactive_ux_style.Get()
  if (style == properties.VALUES.core.InteractiveUXStyles.OFF.name or
      style == properties.VALUES.core.InteractiveUXStyles.TESTING.name):
    return _NoOpCompletionProgressTracker()
  else:
    return _NormalCompletionProgressTracker(
        ofile, timeout, tick_delay, background_ttl, autotick)


class _NormalCompletionProgressTracker(object):
  """A context manager for visual feedback during long-running completions.

  A completion that exceeds the timeout is assumed to be refreshing the cache.
  At that point the progress tracker displays '?', forks the cache operation
  into the background, and exits.  This gives the background cache update a
  chance finish.  After background_ttl more seconds the update is forcibly
  exited (forced to call exit rather than killed by signal) to prevent hung
  updates from proliferating in the background.
  """

  _COMPLETION_FD = 9

  def __init__(self, ofile, timeout, tick_delay, background_ttl, autotick):
    self._ofile = ofile or self._GetStream()
    self._timeout = timeout
    self._tick_delay = tick_delay
    self.__autotick = autotick
    self._background_ttl = background_ttl
    self._ticks = 0
    self._symbols = console_attr.GetConsoleAttr().GetProgressTrackerSymbols()

  def __enter__(self):
    if self._autotick:
      self._old_handler = signal.signal(signal.SIGVTALRM, self._Spin)
      self._old_itimer = signal.setitimer(
          signal.ITIMER_VIRTUAL, self._tick_delay, self._tick_delay)
    return self

  def __exit__(self, unused_type=None, unused_value=True,
               unused_traceback=None):
    if self._autotick:
      signal.setitimer(signal.ITIMER_VIRTUAL, *self._old_itimer)
      signal.signal(signal.SIGVTALRM, self._old_handler)
    if not self._TimedOut():
      self._WriteMark(' ')

  def _TimedOut(self):
    """True if the tracker has timed out."""
    return self._timeout < 0

  def _Spin(self, unused_sig=None, unused_frame=None):
    """Rotates the spinner one tick and checks for timeout."""
    self._ticks += 1
    self._WriteMark(self._symbols.spin_marks[
        self._ticks % len(self._symbols.spin_marks)])
    self._timeout -= self._tick_delay
    if not self._TimedOut():
      return
    # Timed out.
    self._WriteMark('?')
    # Exit the parent process.
    if os.fork():
      os._exit(1)  # pylint: disable=protected-access
    # Allow the child to run in the background for up to self._background_ttl
    # more seconds before being forcefully exited.
    signal.signal(signal.SIGVTALRM, self._ExitBackground)  # pytype: disable=wrong-arg-types
    signal.setitimer(
        signal.ITIMER_VIRTUAL, self._background_ttl, self._background_ttl)
    # Suppress the explicit completion status channel.  stdout and stderr have
    # already been suppressed.
    self._ofile = None

  def _WriteMark(self, mark):
    """Writes one mark to self._ofile."""
    if self._ofile:
      self._ofile.write(mark + '\b')
      self._ofile.flush()

  @staticmethod
  def _ExitBackground():
    """Unconditionally exits the background completer process after timeout."""
    os._exit(1)  # pylint: disable=protected-access

  @property
  def _autotick(self):
    return self.__autotick

  @staticmethod
  def _GetStream():
    """Returns the completer output stream."""
    return os.fdopen(
        os.dup(_NormalCompletionProgressTracker._COMPLETION_FD), 'w')


class _NoOpCompletionProgressTracker(object):
  """A Progress tracker that prints nothing."""

  def __init__(self):
    pass

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    pass
