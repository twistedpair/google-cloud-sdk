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

import os
import sys
import threading
import time

from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.console import console_io


_SPIN_MARKS = [
    '|',
    '/',
    '-',
    '\\',
]


# TODO(b/32656232): support ctrl-c handling.
class ProgressTracker(object):
  """A context manager for telling the user about long-running progress."""

  def __init__(self, message, autotick=True, detail_message_callback=None,
               tick_delay=1):
    self._message = message
    self._prefix = message + '...'
    self._ticks = 0
    self._done = False
    self._lock = threading.Lock()
    self._detail_message_callback = detail_message_callback
    self._multi_line = False
    self._last_display_message = ''
    self._tick_delay = tick_delay
    self._is_tty = console_io.IsInteractive(error=True)
    self.__autotick = autotick

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
    log.file_only_logger.info(self._GetPrefix())
    self._Print()
    if self._autotick:
      def Ticker():
        while True:
          _SleepSecs(self._tick_delay)
          if self.Tick():
            return
      threading.Thread(target=Ticker).start()

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
    sys.stderr.write('.')

  def _Print(self, message=''):
    """Reprints the prefix followed by an optional message.

    If there is a multiline message, we print the full message and every
    time the Prefix Message is the same, we only reprint the last line to
    account for a different 'message'. If there is a new message, we print
    on a new line.

    Args:
      message: str, suffix of message
    """
    display_message = self._GetPrefix()

    # If we are not in a tty, _Print() is called exactly twice.  The first time
    # it should print the prefix, the last time it should print just the 'done'
    # message since we are not using any escape characters at all.
    if not self._is_tty:
      sys.stderr.write(message or display_message + '\n')
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
      sys.stderr.write('\r' + console_width * ' ')
      sys.stderr.write('\r' + current_message)
    elif not console_width:
      # This can happen if we're on a pseudo-TTY; ignore this to prevent
      # hanging.
      pass
    else:  # If we have to do multiline display or a new message.
      # If we have written something to the console before the new message,
      # cursor will be at the end of the line so we need to go to the next line.
      # If we are printing for the first time, the cursor will already be at
      # a new line.
      sys.stderr.write('\n' if self._last_display_message else '')
      self._last_display_message = display_message
      display_message += message
      # We may or may not use multiline display
      while display_message:
        current_printing_message = display_message[:console_width]
        display_message = display_message[console_width:]
        # We print a new line if there is more to print in display_message.
        sys.stderr.write(current_printing_message + ('\n' if display_message
                                                     else ''))
        # If there is still more to print, we will be using multiline display
        # for future printing. We will not  want to erase the last line
        # if a new line is able to fit in the whole console (first if).
        # If self.multi_line was already True, we do not want to make it
        # False
        self._multi_line = (True if display_message or
                            self._multi_line else False)
        sys.stderr.flush()

  def __exit__(self, ex_type, unused_value, unused_traceback):
    with self._lock:
      self._done = True
      # If an exception was raised during progress tracking, exit silently here
      # and let the appropriate exception handler tell the user what happened.
      if ex_type:
        # This is to prevent the tick character from appearing before 'failed.'
        # (ex. 'message...failed' instead of 'message.../failed.')
        self._Print('failed.\n')
        return False
      self._Print('done.\n')


class CompletionProgressTracker(object):
  """A context manager for telling the user about long-running completions."""

  _COMPLETION_FD = 9

  def __init__(self, ofile=None, timeout=3.0, tick_delay=0.1, autotick=True):
    if ofile:
      self._ofile = ofile
      self._close_ofile = False
    else:
      self._ofile = self.GetStream()
      self._close_ofile = True
    self._timeout = timeout
    self._tick_delay = tick_delay
    self.__autotick = autotick

    self._child_pid = None
    self._done = False
    self._lock = threading.Lock()
    self._thread = None
    self._ticks = 0

  def __enter__(self):

    if self._autotick:
      self._thread = threading.Thread(target=self._Spinner)
      self._thread.start()
    return self

  def __exit__(self, unused_type=None, unused_value=True,
               unused_traceback=None):
    with self._lock:
      if not self.timed_out:
        # normal exit -- clear the mark and restore the original cursor position
        self._WriteMark(' ')
      if self._close_ofile:
        self._ofile.close()
      self._done = True
      if self.timed_out and os.getpid() == self._child_pid:
        # exit child process
        sys.exit(0)
    if self._thread:
      self._thread.join()

  def _WriteMark(self, mark):
    """Writes one mark to self._ofile."""
    self._ofile.write(mark + '\b')
    self._ofile.flush()

  def _Sleep(self):
    """Sleep for one tick and return True if not timed out."""
    if self._timeout < 0:
      return False
    _SleepSecs(self._tick_delay)
    self._timeout -= self._tick_delay
    return self._timeout >= 0

  def _Spinner(self):
    """Spinner thread."""
    self._Sleep()
    while self._Sleep():
      if self.Tick():
        # done
        return
    # timed out -- write ? and restore the original cursor position (over the ?)
    self._WriteMark('?')
    self._child_pid = os.fork()

  @property
  def _autotick(self):
    return self.__autotick

  @property
  def timed_out(self):
    """True if the tracker has timed out."""
    return self._child_pid is not None

  @staticmethod
  def GetStream():
    return os.fdopen(os.dup(CompletionProgressTracker._COMPLETION_FD), 'w')

  def Tick(self):
    """Give a visual indication to the user that some progress has been made."""
    with self._lock:
      if not self._done:
        self._ticks += 1
        self._WriteMark(_SPIN_MARKS[self._ticks % len(_SPIN_MARKS)])
      return self._done


def _SleepSecs(seconds):
  """Sleep int or float seconds. For mocking sleeps in this module."""
  time.sleep(seconds)
