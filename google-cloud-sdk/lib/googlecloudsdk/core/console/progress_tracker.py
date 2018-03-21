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
import os
import signal
import sys
import threading
import time

from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.console import console_io


_SPIN_MARKS = [
    '|',
    '/',
    '-',
    '\\',
]


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
    return _NormalProgressTracker(
        message, autotick, detail_message_callback, tick_delay, interruptable,
        aborted_message)


class _NormalProgressTracker(object):
  """A context manager for telling the user about long-running progress."""

  def __init__(self, message, autotick, detail_message_callback, tick_delay,
               interruptable, aborted_message):
    if message is None:
      self._spinner_only = True
      self._message = ''
      self._prefix = ''
      self._suffix = ''
    else:
      self._spinner_only = False
      self._message = message
      self._prefix = message + '...'
      self._suffix = 'done.'
    self._stream = sys.stderr
    self._ticks = 0
    self._done = False
    self._lock = threading.Lock()
    self._detail_message_callback = detail_message_callback
    self._multi_line = False
    self._last_display_message = ''
    self._tick_delay = tick_delay
    self._is_tty = console_io.IsInteractive(error=True)
    self._ticker = None
    self._output_enabled = log.IsUserOutputEnabled()
    # Don't bother autoticking if we aren't going to print anything.
    self.__autotick = autotick and self._output_enabled
    self._interruptable = interruptable
    self._aborted_message = aborted_message
    self._old_signal_handler = None

  @property
  def _autotick(self):
    return self.__autotick

  def _GetPrefix(self):
    if self._detail_message_callback:
      detail_message = self._detail_message_callback()
      if detail_message:
        return self._prefix + ' ' + detail_message + '...'
    return self._prefix

  def __enter__(self):
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
      self._restore_old_handler = False  # only works in the main thread
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

  def Tick(self):
    """Give a visual indication to the user that some progress has been made.

    Output is sent to sys.stderr. Nothing is shown if output is not a TTY.

    Returns:
      Whether progress has completed.
    """
    with self._lock:
      if not self._done:
        if self._is_tty:
          self._ticks += 1
          self._Print(_SPIN_MARKS[self._ticks % len(_SPIN_MARKS)])
        else:
          self._PrintDot()
    return self._done

  def _PrintDot(self):
    """Print dots when not in a tty."""
    if not self._output_enabled:
      return
    self._stream.write('.')

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

    display_message = self._GetPrefix()

    # If we are not in a tty, _Print() is called exactly twice.  The first time
    # it should print the prefix, the last time it should print just the 'done'
    # message since we are not using any escape characters at all.
    if not self._is_tty:
      self._stream.write(message or display_message + '\n')
      return

    console_width = console_attr.ConsoleAttr().GetTermSize()[0] - 1
    if console_width < 0:
      console_width = 0
    # The whole message will fit in the current console width and the previous
    # line was not a multiline display so we can overwrite.
    # If the previous and current messages are same we have multiline display
    # so we only need the portion of text to rewrite on current line.
    if ((len(display_message + message) <= console_width and not
         self._multi_line) or display_message == self._last_display_message):
      self._last_display_message = display_message
      start_place = len(display_message) - (len(display_message)
                                            % console_width)
      if display_message:
        display_message += message
      # If size of the message is a multiple of the console_width, this will
      # cause start place to begin at len(display_message) so we index the
      # message from the end.
      if start_place == 0:
        start_place = -(console_width + len(message))
      current_message = display_message[start_place:]
      # We clear the current display and reprint the last line.
      self._stream.write('\r' + console_width * ' ')
      self._stream.write('\r' + current_message)
    elif not console_width:
      # This can happen if we're on a pseudo-TTY; ignore this to prevent
      # hanging.
      pass
    else:  # If we have to do multiline display or a new message.
      # If we have written something to the console before the new message,
      # cursor will be at the end of the line so we need to go to the next line.
      # If we are printing for the first time, the cursor will already be at
      # a new line.
      self._stream.write('\n' if self._last_display_message else '')
      self._last_display_message = display_message
      display_message += message
      # We may or may not use multiline display
      while display_message:
        current_printing_message = display_message[:console_width]
        display_message = display_message[console_width:]
        # We print a new line if there is more to print in display_message.
        self._stream.write(current_printing_message + ('\n' if display_message
                                                       else ''))
        # If there is still more to print, we will be using multiline display
        # for future printing. We will not  want to erase the last line
        # if a new line is able to fit in the whole console (first if).
        # If self.multi_line was already True, we do not want to make it
        # False
        self._multi_line = (True if display_message or
                            self._multi_line else False)
        self._stream.flush()

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
    if self._restore_old_handler:
      try:
        signal.signal(signal.SIGINT, self._old_signal_handler)
      except ValueError:
        pass  # only works in main thread


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

  def __enter__(self):
    self._stream.write('<START PROGRESS TRACKER>' + self._message + '\n')
    return super(_StubProgressTracker, self).__enter__()

  def __exit__(self, exc_type, exc_val, exc_tb):
    if not exc_val:
      status = 'SUCCESS'
    elif isinstance(exc_val, console_io.OperationCancelledError):
      status = 'INTERRUPTED'
    else:
      status = 'FAILURE'

    self._stream.write(
        '<END PROGRESS TRACKER>' + status + '\n')
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
    self._WriteMark(_SPIN_MARKS[self._ticks % len(_SPIN_MARKS)])
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
