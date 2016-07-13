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

"""General console printing utilities used by the Cloud SDK."""

import os
import re
import sys
import textwrap
import threading
import time

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.console import console_pager
from googlecloudsdk.core.util import files
from googlecloudsdk.third_party.py27 import py27_subprocess as subprocess

FLOAT_COMPARE_EPSILON = 1e-6


class Error(exceptions.Error):
  """Base exception for the module."""
  pass


class UnattendedPromptError(Error):
  """An exception for when a prompt cannot be answered."""

  def __init__(self):
    super(UnattendedPromptError, self).__init__(
        'This prompt could not be answered because you are not in an '
        'interactive session.  You can re-run the command with the --quiet '
        'flag to accept default answers for all prompts.')


class OperationCancelledError(Error):
  """An exception for when a prompt cannot be answered."""

  def __init__(self):
    super(OperationCancelledError, self).__init__('Operation cancelled.')


TEXTWRAP = textwrap.TextWrapper(replace_whitespace=False,
                                drop_whitespace=False,
                                break_on_hyphens=False)


def _DoWrap(message):
  """Text wrap the given message and correctly handle newlines in the middle.

  Args:
    message: str, The message to wrap.  It may have newlines in the middle of
      it.

  Returns:
    str, The wrapped message.
  """
  return '\n'.join([TEXTWRAP.fill(line) for line in message.splitlines()])


def _RawInput(prompt=None):
  """A simple redirect to the built-in raw_input function.

  If the prompt is given, it is correctly line wrapped.

  Args:
    prompt: str, An optional prompt.

  Returns:
    The input from stdin.
  """
  if prompt:
    sys.stderr.write(_DoWrap(prompt))

  try:
    return raw_input()
  except EOFError:
    return None


def IsInteractive(output=False, error=False, heuristic=False):
  """Determines if the current terminal session is interactive.

  sys.stdin must be a terminal input stream.

  Args:
    output: If True then sys.stdout must also be a terminal output stream.
    error: If True then sys.stderr must also be a terminal output stream.
    heuristic: If True then we also do some additional heuristics to check if
               we are in an interactive context. Checking home path for example.

  Returns:
    True if the current terminal session is interactive.
  """
  if not sys.stdin.isatty():
    return False
  if output and not sys.stdout.isatty():
    return False
  if error and not sys.stderr.isatty():
    return False
  if heuristic:
    # Check the home path. Most startup scripts for example are executed by
    # users that don't have a home path set. Home is OS dependent though, so
    # check everything.
    # *NIX OS usually sets the HOME env variable. It is usually '/home/user',
    # but can also be '/root'. If it's just '/' we are most likely in an init
    # script.
    # Windows usually sets HOMEDRIVE and HOMEPATH. If they don't exist we are
    # probably being run from a task scheduler context. HOMEPATH can be '\'
    # when a user has a network mapped home directory.
    # Cygwin has it all! Both Windows and Linux. Checking both is perfect.
    home = os.getenv('HOME')
    homepath = os.getenv('HOMEPATH')
    if not homepath and (not home or home == '/'):
      return False
  return True


def CanPrompt():
  """Returns true if we can prompt the user for information.

  This combines all checks (IsInteractive(), disable_prompts is False) to
  verify that we can prompt the user for information.

  Returns:
    bool, True if we can prompt the user for information.
  """
  return (IsInteractive(error=True) and
          not properties.VALUES.core.disable_prompts.GetBool())


def PromptContinue(message=None, prompt_string=None, default=True,
                   throw_if_unattended=False, cancel_on_no=False):
  """Prompts the user a yes or no question and asks if they want to continue.

  Args:
    message: str, The prompt to print before the question.
    prompt_string: str, An alternate yes/no prompt to display.  If None, it
      defaults to 'Do you want to continue'.
    default: bool, What the default answer should be.  True for yes, False for
      no.
    throw_if_unattended: bool, If True, this will throw if there was nothing
      to consume on stdin and stdin is not a tty.
    cancel_on_no: bool, If True and the user answers no, throw an exception to
      cancel the entire operation.  Useful if you know you don't want to
      continue doing anything and don't want to have to raise your own
      exception.

  Raises:
    UnattendedPromptError: If there is no input to consume and this is not
      running in an interactive terminal.
    OperationCancelledError: If the user answers no and cancel_on_no is True.

  Returns:
    bool, False if the user said no, True if the user said anything else or if
    prompts are disabled.
  """
  if properties.VALUES.core.disable_prompts.GetBool():
    if not default and cancel_on_no:
      raise OperationCancelledError()
    return default

  if message:
    sys.stderr.write(_DoWrap(message) + '\n\n')

  if not prompt_string:
    prompt_string = 'Do you want to continue'
  if default:
    prompt_string += ' (Y/n)?  '
  else:
    prompt_string += ' (y/N)?  '
  sys.stderr.write(_DoWrap(prompt_string))

  def GetAnswer():
    while True:
      answer = _RawInput()
      # pylint:disable=g-explicit-bool-comparison, We explicitly want to
      # distinguish between empty string and None.
      if answer == '':
        # User just hit enter, return default.
        sys.stderr.write('\n')
        return default
      elif answer is None:
        # This means we hit EOF, no input or user closed the stream.
        if throw_if_unattended and not IsInteractive():
          sys.stderr.write('\n')
          raise UnattendedPromptError()
        else:
          sys.stderr.write('\n')
          return default
      elif answer.lower() in ['y', 'yes']:
        sys.stderr.write('\n')
        return True
      elif answer.lower() in ['n', 'no']:
        sys.stderr.write('\n')
        return False
      else:
        sys.stderr.write("Please enter 'y' or 'n':  ")

  answer = GetAnswer()
  if not answer and cancel_on_no:
    raise OperationCancelledError()
  return answer


def PromptResponse(message):
  """Prompts the user for a string.

  Args:
    message: str, The prompt to print before the question.

  Returns:
    str, The string entered by the user, or None if prompts are disabled.
  """
  if properties.VALUES.core.disable_prompts.GetBool():
    return None
  response = _RawInput(message)
  return response


def PromptWithDefault(message, default=None):
  """Prompts the user for a string, allowing a default.

  Unlike PromptResponse, this also appends a ':  ' to the prompt.  If 'default'
  is specified, the default is also written written into the prompt (e.g.
  if message is "message" and default is "default", the prompt would be
  "message (default): ").

  The default is returned if the user simply presses enter (no input) or an
  EOF is received.

  Args:
    message: str, The prompt to print before the question.
    default: str, The default value (if any).

  Returns:
    str, The string entered by the user, or the default if no value was
    entered or prompts are disabled.
  """
  if properties.VALUES.core.disable_prompts.GetBool():
    return default
  if default:
    message += ' ({default}):  '.format(default=default)
  else:
    message += ':  '
  response = _RawInput(message)
  if not response:
    response = default
  return response


def PromptChoice(options, default=None, message=None, prompt_string=None):
  """Prompt the user to select a choice from a list of items.

  Args:
    options:  [object], A list of objects to print as choices.  Their str()
      method will be used to display them.
    default: int, The default index to return if prompting is disabled or if
      they do not enter a choice.
    message: str, An optional message to print before the choices are displayed.
    prompt_string: str, A string to print when prompting the user to enter a
      choice.  If not given, a default prompt is used.

  Raises:
    ValueError: If no options are given or if the default is not in the range of
      available options.

  Returns:
    The index of the item in the list that was chosen, or the default if prompts
    are disabled.
  """
  if not options:
    raise ValueError('You must provide at least one option.')
  maximum = len(options)
  if default is not None and not 0 <= default < maximum:
    raise ValueError(
        'Default option [{default}] is not a valid index for the options list '
        '[{maximum} options given]'.format(default=default, maximum=maximum))
  if properties.VALUES.core.disable_prompts.GetBool():
    return default

  if message:
    sys.stderr.write(_DoWrap(message) + '\n')
  for i, option in enumerate(options):
    sys.stderr.write(' [{index}] {option}\n'.format(
        index=i + 1, option=str(option)))

  if not prompt_string:
    prompt_string = 'Please enter your numeric choice'
  if default is None:
    suffix_string = ':  '
  else:
    suffix_string = ' ({default}):  '.format(default=default + 1)
  sys.stderr.write(_DoWrap(prompt_string + suffix_string))
  while True:
    answer = _RawInput()
    if answer is None or (answer is '' and default is not None):
      # Return default if we failed to read from stdin
      # Return default if the user hit enter and there is a valid default
      # Prompt again otherwise
      sys.stderr.write('\n')
      return default
    try:
      num_choice = int(answer)
      if num_choice < 1 or num_choice > maximum:
        raise ValueError('Choice must be between 1 and {maximum}'.format(
            maximum=maximum))
      sys.stderr.write('\n')
      return num_choice - 1
    except ValueError:
      sys.stderr.write('Please enter a value between 1 and {maximum}:  '
                       .format(maximum=maximum))


def LazyFormat(s, **kwargs):
  """Converts {key} => value for key, value in kwargs.iteritems().

  After the {key} converstions it converts {{<identifier>}} => {<identifier>}.

  Args:
    s: str, The string to format.
    **kwargs: {str:str}, A dict of strings for named parameters.

  Returns:
    str, The lazily-formatted string.
  """

  for key, value in kwargs.iteritems():
    fmt = '{' + key + '}'
    start = 0
    while True:
      start = s.find(fmt, start)
      if start == -1:
        break
      if (start and s[start - 1] == '{' and
          len(fmt) < len(s[start:]) and s[start + len(fmt)] == '}'):
        # {{key}} => {key}
        s = s[0:start - 1] + fmt + s[start + len(fmt) + 1:]
        start += len(fmt)
      else:
        # {key} => value
        s = s[0:start] + value + s[start + len(fmt):]
        start += len(value)
  # {{unknown}} => {unknown}
  return re.sub(r'{({\w+})}', r'\1', s)


class ProgressTracker(object):
  """A context manager for telling the user about long-running progress."""

  SPIN_MARKS = [
      '|',
      '/',
      '-',
      '\\',
  ]

  def __init__(self, message, autotick=True, detail_message_callback=None,
               tick_delay=1):
    self._message = message
    self._prefix = message + '...'
    self._ticks = 0
    self._autotick = autotick
    self._done = False
    self._lock = threading.Lock()
    self._detail_message_callback = detail_message_callback
    self._last_message_size = 0
    self._tick_delay = tick_delay
    self._is_tty = IsInteractive(output=True, error=True)

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
          time.sleep(self._tick_delay)
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
    if self._is_tty:
      with self._lock:
        if not self._done:
          self._ticks += 1
          self._Print(ProgressTracker.SPIN_MARKS[
              self._ticks % len(ProgressTracker.SPIN_MARKS)])
    return self._done

  def _Print(self, message=''):
    """Reprints the prefix followed by an optional message."""
    display_message = self._GetPrefix()
    if message:
      display_message += message

    # This is to clear the display buffer, otherwise it would display the
    # trailing parts of the previous line
    if self._last_message_size > 0:
      sys.stderr.write('\r' + self._last_message_size * ' ')
    self._last_message_size = len(display_message)

    sys.stderr.write('\r' + display_message)
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


class DelayedProgressTracker(ProgressTracker):
  """A progress tracker that only appears during a long running operation.

  Waits for the given timeout, then displays a progress tacker.
  """

  class TrackerState(object):
    """Enum representing the current state of the progress tracker."""

    class _TrackerStateTuple(object):

      def __init__(self, name):
        self.name = name

    WAITING = _TrackerStateTuple('Waiting')
    STARTED = _TrackerStateTuple('Started')
    FINISHED = _TrackerStateTuple('Finished')

  def __init__(self, message, timeout, autotick=True,
               detail_message_callback=None):
    super(DelayedProgressTracker, self).__init__(
        message, autotick=autotick,
        detail_message_callback=detail_message_callback)
    self._timeout = timeout
    self._state = self.TrackerState.WAITING
    self._state_lock = threading.Lock()

  def _SleepWhileNotFinished(self, timeout, increment=0.1):
    """Sleep for the given time unless the tracker enters the FINISHED state.

    Args:
      timeout: number, the total time for which to sleep
      increment: number, the increment at which to check whether the tracker is
        FINISHED

    Returns:
      bool, True unless the tracker reached the FINISHED state before the total
        sleep time elapsed
    """
    elapsed_time = 0
    while (elapsed_time + FLOAT_COMPARE_EPSILON) <= timeout:
      time.sleep(increment)
      elapsed_time += increment
      if self._state is self.TrackerState.FINISHED:
        return False
    return True

  def __enter__(self):
    def StartTracker():
      if not self._SleepWhileNotFinished(self._timeout):
        # If we aborted sleep early, return. We exited the progress tracker
        # before the delay finished.
        return
      with self._state_lock:
        if self._state is not self.TrackerState.FINISHED:
          self._state = self.TrackerState.STARTED
          super(DelayedProgressTracker, self).__enter__()
    threading.Thread(target=StartTracker).start()
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    with self._state_lock:
      if self._state is self.TrackerState.STARTED:
        super(DelayedProgressTracker, self).__exit__(exc_type, exc_value,
                                                     traceback)
      self._state = self.TrackerState.FINISHED

  def Tick(self):
    with self._state_lock:
      if self._state is self.TrackerState.STARTED:
        return super(DelayedProgressTracker, self).Tick()
      return self._state is self.TrackerState.FINISHED


class ProgressBar(object):
  """A simple progress bar for tracking completion of an action.

  This progress bar works without having to use any control characters.  It
  prints the action that is being done, and then fills a progress bar below it.
  You should not print anything else on the output stream during this time as it
  will cause the progress bar to break on lines.

  Progress bars can be stacked into a group. first=True marks the first bar in
  the group and last=True marks the last bar in the group. The default assumes
  a singleton bar with first=True and last=True.

  This class can also be used in a context manager.
  """

  @staticmethod
  def _DefaultCallback(progress_factor):
    pass

  DEFAULT_CALLBACK = _DefaultCallback

  @staticmethod
  def SplitProgressBar(original_callback, weights):
    """Splits a progress bar into logical sections.

    Wraps the original callback so that each of the subsections can use the full
    range of 0 to 1 to indicate its progress.  The overall progress bar will
    display total progress based on the weights of the tasks.

    Args:
      original_callback: f(float), The original callback for the progress bar.
      weights: [float], The weights of the tasks to create.  These can be any
        numbers you want and the split will be based on their proportions to
        each other.

    Raises:
      ValueError: If the weights don't add up to 1.

    Returns:
      (f(float), ), A tuple of callback functions, in order, for the subtasks.
    """
    if (original_callback is None or
        original_callback == ProgressBar.DEFAULT_CALLBACK):
      return tuple([ProgressBar.DEFAULT_CALLBACK for _ in range(len(weights))])

    def MakeCallback(already_done, weight):
      def Callback(done_fraction):
        original_callback(already_done + (done_fraction * weight))
      return Callback

    total = float(sum(weights))
    callbacks = []
    already_done = 0
    for weight in weights:
      normalized_weight = weight / total
      callbacks.append(MakeCallback(already_done, normalized_weight))
      already_done += normalized_weight

    return tuple(callbacks)

  def __init__(self, label, stream=log.status, total_ticks=60, first=True,
               last=True):
    """Creates a progress bar for the given action.

    Args:
      label: str, The action that is being performed.
      stream: The output stream to write to, stderr by default.
      total_ticks: int, The number of ticks wide to make the progress bar.
      first: bool, True if this is the first bar in a stacked group.
      last: bool, True if this is the last bar in a stacked group.
    """
    self._stream = stream
    self._ticks_written = 0
    self._total_ticks = total_ticks
    self._first = first
    self._last = last
    attr = console_attr.ConsoleAttr()
    self._box = attr.GetBoxLineCharacters()
    self._redraw = (self._box.d_dr != self._box.d_vr or
                    self._box.d_dl != self._box.d_vl)

    max_label_width = self._total_ticks - 4
    if len(label) > max_label_width:
      label = label[:max_label_width - 3] + '...'
    elif len(label) < max_label_width:
      diff = max_label_width - len(label)
      label += ' ' * diff
    left = self._box.d_vr + self._box.d_h
    right = self._box.d_h + self._box.d_vl
    self._label = u'{left} {label} {right}'.format(left=left, label=label,
                                                   right=right)

  def Start(self):
    """Starts the progress bar by writing the top rule and label."""
    if self._first or self._redraw:
      left = self._box.d_dr if self._first else self._box.d_vr
      right = self._box.d_dl if self._first else self._box.d_vl
      rule = u'{left}{middle}{right}\n'.format(
          left=left, middle=self._box.d_h * self._total_ticks, right=right)
      self._stream.write(rule)
    self._stream.write(self._label + '\n')
    self._stream.write(self._box.d_ur)
    self._ticks_written = 0

  def SetProgress(self, progress_factor):
    """Sets the current progress of the task.

    This method has no effect if the progress bar has already progressed past
    the progress you call it with (since the progress bar cannot back up).

    Args:
      progress_factor: float, The current progress as a float between 0 and 1.
    """
    expected_ticks = int(self._total_ticks * progress_factor)
    new_ticks = expected_ticks - self._ticks_written
    # Don't allow us to go over 100%.
    new_ticks = min(new_ticks, self._total_ticks - self._ticks_written)

    if new_ticks > 0:
      self._stream.write(self._box.d_h * new_ticks)
      self._ticks_written += new_ticks
      if expected_ticks == self._total_ticks:
        end = '\n' if self._last or not self._redraw else '\r'
        self._stream.write(self._box.d_ul + end)
      self._stream.flush()

  def Finish(self):
    """Mark the progress as done."""
    self.SetProgress(1)

  def __enter__(self):
    self.Start()
    return self

  def __exit__(self, *args):
    self.Finish()


def More(contents, out=None, prompt=None, check_pager=True):
  """Run a user specified pager or fall back to the internal pager.

  Args:
    contents: The entire contents of the text lines to page.
    out: The output stream, log.out (effectively) if None.
    prompt: The page break prompt.
    check_pager: Checks the PAGER env var and uses it if True.
  """
  if not IsInteractive(output=True):
    if not out:
      out = log.out
    out.write(contents)
    return
  if not out:
    # Rendered help to the log file.
    log.file_only_logger.info(contents)
    # Paging shenanigans to stdout.
    out = sys.stdout
  if check_pager:
    pager = os.environ.get('PAGER', None)
    if pager == '-':
      # Use the fallback Pager.
      pager = None
    elif not pager:
      # Search for a pager that handles ANSI escapes.
      for command in ('less', 'pager'):
        if files.FindExecutableOnPath(command):
          pager = command
          break
    if pager:
      less = os.environ.get('LESS', None)
      if less is None:
        os.environ['LESS'] = '-R'
      p = subprocess.Popen(pager, stdin=subprocess.PIPE, shell=True)
      encoding = console_attr.GetConsoleAttr().GetEncoding()
      p.communicate(input=contents.encode(encoding))
      p.wait()
      if less is None:
        os.environ.pop('LESS')
      return
  # Fall back to the internal pager.
  console_pager.Pager(contents, out, prompt).Run()
