# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Implements parallel task execution for the storage surface.

See go/parallel-processing-in-gcloud-storage for more information.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib
import functools
import multiprocessing
import re
import signal as signal_lib
import sys
import tempfile
import threading
import traceback
from typing import Dict, Iterator

from googlecloudsdk.api_lib.storage.gcs_json import patch_apitools_messages
from googlecloudsdk.command_lib import crash_handling
from googlecloudsdk.command_lib.storage import encryption_util
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks import task_buffer
from googlecloudsdk.command_lib.storage.tasks import task_graph as task_graph_module
from googlecloudsdk.command_lib.storage.tasks import task_status
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import transport
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.credentials import creds_context_managers
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms
from six.moves import queue


# TODO(b/171296237): Remove this when fixes are submitted in apitools.
patch_apitools_messages.patch()


if sys.version_info.major == 2:
  # multiprocessing.get_context is only available in Python 3. We don't support
  # Python 2, but some of our code still runs at import in Python 2 tests, so
  # we need to provide a value here.
  multiprocessing_context = multiprocessing

else:
  _should_force_spawn = (
      # On MacOS, fork is unsafe: https://bugs.python.org/issue33725. The
      # default start method is spawn on versions >= 3.8, but we need to set it
      # explicitly for older versions.
      platforms.OperatingSystem.Current() is platforms.OperatingSystem.MACOSX or
      # On Linux, fork causes issues when mTLS is enabled: go/ecp-gcloud-storage
      # The default start method on Linux is fork, hence we will set it to spawn
      # when client certificate authentication (mTLS) is enabled.
      (properties.VALUES.context_aware.use_client_certificate.GetBool() and
       platforms.OperatingSystem.Current() is platforms.OperatingSystem.LINUX)
  )

  if _should_force_spawn:
    multiprocessing_context = multiprocessing.get_context(method='spawn')
  else:
    # Uses platform default.
    multiprocessing_context = multiprocessing.get_context()


_TASK_QUEUE_LOCK = threading.Lock()


# TODO(b/203819260): Check if this lock can be removed on Windows, since message
# patches are applied above.
@contextlib.contextmanager
def _task_queue_lock():
  """Context manager which acquires a lock when queue.get is unsafe.

  On Python 3.5 with spawn enabled, a race condition affects unpickling
  objects in queue.get calls. This manifests as an AttributeError intermittently
  thrown by ForkingPickler.loads, e.g.:

  AttributeError: Can't get attribute 'FileDownloadTask' on <module
  'googlecloudsdk.command_lib.storage.tasks.cp.file_download_task' from
  'googlecloudsdk/command_lib/storage/tasks/cp/file_download_task.py'

  Adding a lock around queue.get calls using this context manager resolves the
  issue.

  Yields:
    None, but acquires a lock which is released on exit.
  """
  get_is_unsafe = (
      sys.version_info.major == 3 and sys.version_info.minor <= 5
      and multiprocessing_context.get_start_method() == 'spawn'
  )

  try:
    if get_is_unsafe:
      _TASK_QUEUE_LOCK.acquire()
    yield
  finally:
    if get_is_unsafe:
      _TASK_QUEUE_LOCK.release()


# When threads get this value, they should prepare to exit.
#
# Threads should check for this value with `==` and not `is`, since the pickling
# carried out by multiprocessing.Queue may cause `is` to incorrectly return
# False.
#
# When the executor is shutting down, this value is added to
# TaskGraphExecutor._executable_tasks and is passed to
# TaskGraphExecutor._task_queue.
_SHUTDOWN = 'SHUTDOWN'

_CREATE_WORKER_PROCESS = 'CREATE_WORKER_PROCESS'


def is_task_graph_debugging_enabled() -> bool:
  """Whether task graph debugging is enabled.

  Returns:
      bool: True if task graph debugging is enabled else False.
  """
  return properties.VALUES.storage.enable_task_graph_debugging.GetBool()


def yield_stack_traces() -> Iterator[str]:
  """Retrieve stack traces for all the threads."""
  # pylint:disable=protected-access
  # There does not appear to be another way to collect the stack traces
  # for all running threads.
  for thread_id, stack in sys._current_frames().items():
    yield f'\n# Traceback for thread: {thread_id}'
    for filename, line_number, name, text in traceback.extract_stack(stack):
      yield f'File: "{filename}", line {line_number}, in {name}'
      if text:
        yield f'  {text.strip()}'


def _yield_management_thread_stack_traces(
    name_to_thread: Dict[str, threading.Thread],
    alive_thread_id_to_name: Dict[int, str],
) -> Iterator[str]:
  """Yields the stack traces of the alive management threads."""
  for thread_name, thread in name_to_thread.items():
    if thread.is_alive():
      alive_thread_id_to_name[thread.ident] = thread_name

  all_threads_stack_traces = yield_stack_traces()
  current_thread_id = None

  thread_id_pattern = re.compile(r'^\n# Traceback for thread:(.*)')
  for line in all_threads_stack_traces:
    if thread_id_match := thread_id_pattern.match(line):
      current_thread_id = int(thread_id_match.group(1))
    if (
        current_thread_id in alive_thread_id_to_name
    ):  # printing the stack traces of only the alive management threads.
      if thread_id_match:
        yield (
            '\n# Traceback for'
            f' thread:{alive_thread_id_to_name[current_thread_id]}'
        )
      yield line

  for thread_name, thread in name_to_thread.items():
    if thread.ident not in alive_thread_id_to_name:
      yield (
          f'\n# Thread {thread_name} is not running. Cannot get stack trace at'
          ' the moment.'
      )


def print_management_thread_stacks(
    management_threads_name_to_function: Dict[str, threading.Thread],
):
  """Prints stack traces of the management threads."""
  log.status.Print(
      'Initiating stack trace information of the management threads.'
  )
  alive_thread_id_to_name = {}
  stack_traces = _yield_management_thread_stack_traces(
      management_threads_name_to_function, alive_thread_id_to_name
  )
  for line in stack_traces:
    log.status.Print(line)


def print_worker_thread_stack_traces(stack_trace_file_path):
  """Prints stack traces of the worker threads."""

  try:
    stack_traces = files.ReadFileContents(stack_trace_file_path)
  except IOError as e:
    log.error(f'Error reading stack trace file: {e}')
    log.status.Print('No stack traces could be retrieved.')
    return

  if stack_traces:
    log.status.Print('Printing stack traces for worker threads:')
    # Split contents into lines and print each line.
    for line in stack_traces.splitlines():
      log.status.Print(line.strip())
  else:
    log.status.Print('No stack traces found. No worker threads running.')


def print_queue_size(task_queue, task_status_queue, task_output_queue):
  """Prints the size of the queues."""
  log.status.Print(f'Task Queue size: {task_queue.qsize()}')
  log.status.Print(f'Task Status Queue size: {task_status_queue.qsize()}')
  log.status.Print(f'Task Output Queue size: {task_output_queue.qsize()}')


def task_graph_debugger_worker(
    management_threads_name_to_function: Dict[str, threading.Thread],
    stack_trace_file: str,
    task_graph: task_graph_module.TaskGraph,
    task__buffer: task_buffer.TaskBuffer,
    delay_seconds: int = 3,
):
  """The main worker function for the task graph debugging framework.

  Prints the stack traces of the management threads involved namely
  iterator_to_buffer, buffer_to_queue and task_output_handler.Captures and
  prints the contents of the task graph and task buffer.
  Also prints the stack traces of the worker threads if they are running at the
  particular snapshot taken.

  Args:
    management_threads_name_to_function: A dictionary of management thread name
      to the thread function.
    stack_trace_file: Path to the file containing the stack traces of the worker
      threads.
    task_graph: The task graph object.
    task__buffer: The task buffer object.
    delay_seconds: The time interval between two consecutive snapshots.
  """
  is_task_buffer_empty = False
  is_task_graph_empty = False
  is_some_management_thread_alive = True

  while (
      is_some_management_thread_alive
      or not is_task_buffer_empty
      or not is_task_graph_empty
  ):
    print_management_thread_stacks(management_threads_name_to_function)
    print_worker_thread_stack_traces(stack_trace_file)
    log.status.Print(str(task_graph))
    log.status.Print(str(task__buffer))

    is_task_graph_empty = task_graph.is_empty.is_set()
    is_task_buffer_empty = task__buffer.size() == 0

    is_some_management_thread_alive = False
    for thread in management_threads_name_to_function.values():
      if thread.is_alive():
        is_some_management_thread_alive = True
        break

    # Wait for the delay_seconds to pass before taking the next snapshot
    # if conditions are met.
    event = threading.Event()
    event.wait(delay_seconds)


def start_thread_for_task_graph_debugging(
    management_threads_name_to_function: Dict[str, threading.Thread],
    stack_trace_file: str,
    task_graph: task_graph_module.TaskGraph,
    task__buffer: task_buffer.TaskBuffer,
    delay_seconds: int = 3,
):
  """Starts a thread for task graph debugging."""
  try:
    thread_for_task_graph_debugging = threading.Thread(
        target=task_graph_debugger_worker,
        args=(
            management_threads_name_to_function,
            stack_trace_file,
            task_graph,
            task__buffer,
            delay_seconds,
        ),
    )
    thread_for_task_graph_debugging.start()

  except Exception as e:  # pylint: disable=broad-except
    log.error(f'Error starting thread: {e}')


class _DebugSignalHandler:
  """Signal handler for collecting debug information."""

  def __init__(self):
    """Initializes the debug signal handler."""
    if (
        platforms.OperatingSystem.Current()
        is not platforms.OperatingSystem.WINDOWS
    ):
      self._debug_signal = signal_lib.SIGUSR1

  def _debug_handler(
      self, signal_number: int = None, frame: object = None
  ) -> None:
    """Logs stack traces of running threads.

    Args:
      signal_number: Signal number.
      frame: Frame object.
    """
    del signal_number, frame  # currently unused
    log.debug('Initiating crash debug information data collection.')
    stack_traces = []
    stack_traces.extend(yield_stack_traces())
    for line in stack_traces:
      log.debug(line)

  def install(self):
    """Installs the debug signal handler."""
    if platforms.OperatingSystem.Current() is platforms.OperatingSystem.WINDOWS:
      return  # Not supported for windows systems.
    try:
      self._original_signal_handler = signal_lib.getsignal(self._debug_signal)
      signal_lib.signal(self._debug_signal, self._debug_handler)
    except ValueError:
      pass  # Can be run from the main thread only.

  def terminate(self):
    """Restores the original signal handler.

    This method should be called when the debug signal handler is no longer
    needed.
    """
    if platforms.OperatingSystem.Current() is platforms.OperatingSystem.WINDOWS:
      return  # Not supported for windows systems.
    try:
      if hasattr(self, '_original_signal_handler'):
        signal_lib.signal(self._debug_signal, self._original_signal_handler)
    except ValueError:
      pass  # Can be run from the main thread only.


class SharedProcessContext:
  """Context manager used to collect and set global state."""

  def __init__(self):
    """Collects global state in the main process."""
    if multiprocessing_context.get_start_method() == 'fork':
      return

    self._environment_variables = execution_utils.GetToolEnv()
    self._creds_context_manager = (
        creds_context_managers.CredentialProvidersManager())
    self._key_store = encryption_util._key_store
    self._invocation_id = transport.INVOCATION_ID

  def __enter__(self):
    """Sets global state in child processes."""
    if multiprocessing_context.get_start_method() == 'fork':
      return

    self._environment_context_manager = execution_utils.ReplaceEnv(
        **self._environment_variables)

    self._environment_context_manager.__enter__()
    self._creds_context_manager.__enter__()
    encryption_util._key_store = self._key_store
    transport.INVOCATION_ID = self._invocation_id

    # Passing None causes log settings to be refreshed based on property values.
    log.SetUserOutputEnabled(None)
    log.SetVerbosity(None)

  def __exit__(self, exc_type, exc_value, exc_traceback):
    """Cleans up global state in child processes."""
    if multiprocessing_context.get_start_method() == 'fork':
      return

    self._environment_context_manager.__exit__(
        exc_type, exc_value, exc_traceback)
    self._creds_context_manager.__exit__(exc_type, exc_value, exc_traceback)


@crash_handling.CrashManager
def _thread_worker(task_queue, task_output_queue, task_status_queue,
                   idle_thread_count):
  """A consumer thread run in a child process.

  Args:
    task_queue (multiprocessing.Queue): Holds task_graph.TaskWrapper instances.
    task_output_queue (multiprocessing.Queue): Sends information about completed
      tasks back to the main process.
    task_status_queue (multiprocessing.Queue|None): Used by task to report it
      progress to a central location.
    idle_thread_count (multiprocessing.Semaphore): Keeps track of how many
      threads are busy. Useful for spawning new workers if all threads are busy.
  """
  while True:
    with _task_queue_lock():
      task_wrapper = task_queue.get()
    if task_wrapper == _SHUTDOWN:
      break
    idle_thread_count.acquire()

    task_execution_error = None
    try:
      task_output = task_wrapper.task.execute(
          task_status_queue=task_status_queue)
    # pylint: disable=broad-except
    # If any exception is raised, it will prevent the executor from exiting.
    except Exception as exception:
      task_execution_error = exception
      log.error(exception)
      log.debug(exception, exc_info=sys.exc_info())

      if isinstance(exception, errors.FatalError):
        task_output = task.Output(
            additional_task_iterators=None,
            messages=[task.Message(topic=task.Topic.FATAL_ERROR, payload={})])
      elif task_wrapper.task.change_exit_code:
        task_output = task.Output(
            additional_task_iterators=None,
            messages=[
                task.Message(topic=task.Topic.CHANGE_EXIT_CODE, payload={})
            ])
      else:
        task_output = None
    # pylint: enable=broad-except
    finally:
      task_wrapper.task.exit_handler(task_execution_error, task_status_queue)

    task_output_queue.put((task_wrapper, task_output))
    idle_thread_count.release()


def write_stack_traces_to_file(
    stack_traces: Iterator[str], stack_trace_file_path: str
):
  """Writes stack traces to a file."""
  if not stack_trace_file_path:
    return

  try:
    stripped_stack_entries = []
    for entry in stack_traces:
      stripped_entry = entry.strip()
      if stripped_entry:
        stripped_stack_entries.append(stripped_entry)

    content = '\n'.join(stripped_stack_entries)
    files.WriteFileContents(stack_trace_file_path, content)

  except Exception as e:  # pylint: disable=broad-except
    log.error(f'An error occurred while writing stack trace file: {e}')


@crash_handling.CrashManager
def _process_worker(
    task_queue,
    task_output_queue,
    task_status_queue,
    thread_count,
    idle_thread_count,
    shared_process_context,
    stack_trace_file_path
):
  """Starts a consumer thread pool.

  Args:
    task_queue (multiprocessing.Queue): Holds task_graph.TaskWrapper instances.
    task_output_queue (multiprocessing.Queue): Sends information about completed
      tasks back to the main process.
    task_status_queue (multiprocessing.Queue|None): Used by task to report it
      progress to a central location.
    thread_count (int): Number of threads the process should spawn.
    idle_thread_count (multiprocessing.Semaphore): Passed on to worker threads.
    shared_process_context (SharedProcessContext): Holds values from global
      state that need to be replicated in child processes.
    stack_trace_file_path (str): File path to write stack traces to.
  """
  threads = []
  with shared_process_context:
    for _ in range(thread_count):
      thread = threading.Thread(
          target=_thread_worker,
          args=(
              task_queue,
              task_output_queue,
              task_status_queue,
              idle_thread_count,
          ),
      )
      thread.start()
      threads.append(thread)

    # TODO: b/354829547 - Update the function to catch the updated stack traces
    # of the already running worker threads while a new worker process
    # is not created.

    if is_task_graph_debugging_enabled():
      stack_trace = yield_stack_traces()
      write_stack_traces_to_file(stack_trace, stack_trace_file_path)

    for thread in threads:
      thread.join()


@crash_handling.CrashManager
def _process_factory(
    task_queue,
    task_output_queue,
    task_status_queue,
    thread_count,
    idle_thread_count,
    signal_queue,
    shared_process_context,
    stack_trace_file_path
):
  """Create worker processes.

  This factory must run in a separate process to avoid deadlock issue,
  see go/gcloud-storage-deadlock-issue/. Although we are adding one
  extra process by doing this, it will remain idle once all the child worker
  processes are created. Thus, it does not add noticable burden on the system.

  Args:
    task_queue (multiprocessing.Queue): Holds task_graph.TaskWrapper instances.
    task_output_queue (multiprocessing.Queue): Sends information about completed
      tasks back to the main process.
    task_status_queue (multiprocessing.Queue|None): Used by task to report it
      progress to a central location.
    thread_count (int): Number of threads the process should spawn.
    idle_thread_count (multiprocessing.Semaphore): Passed on to worker threads.
    signal_queue (multiprocessing.Queue): Queue used by parent process to
      signal when a new child worker process must be created.
    shared_process_context (SharedProcessContext): Holds values from global
      state that need to be replicated in child processes.
    stack_trace_file_path (str): File path to write stack traces to.
  """
  processes = []
  while True:
    # We receive one signal message for each process to be created.
    signal = signal_queue.get()
    if signal == _SHUTDOWN:
      for _ in processes:
        for _ in range(thread_count):
          task_queue.put(_SHUTDOWN)
      break
    elif signal == _CREATE_WORKER_PROCESS:
      for _ in range(thread_count):
        idle_thread_count.release()

      process = multiprocessing_context.Process(
          target=_process_worker,
          args=(
              task_queue,
              task_output_queue,
              task_status_queue,
              thread_count,
              idle_thread_count,
              shared_process_context,
              stack_trace_file_path,
          ),
      )
      processes.append(process)
      log.debug('Adding 1 process with {} threads.'
                ' Total processes: {}. Total threads: {}.'.format(
                    thread_count, len(processes),
                    len(processes) * thread_count))
      process.start()
    else:
      raise errors.Error('Received invalid signal for worker '
                         'process creation: {}'.format(signal))

  for process in processes:
    process.join()


def _store_exception(target_function):
  """Decorator for storing exceptions raised from the thread targets.

  Args:
    target_function (function): Thread target to decorate.

  Returns:
    Decorator function.
  """
  @functools.wraps(target_function)
  def wrapper(self, *args, **kwargs):
    try:
      target_function(self, *args, **kwargs)
      # pylint:disable=broad-except
    except Exception as e:
      # pylint:enable=broad-except
      if not isinstance(self, TaskGraphExecutor):
        # Storing of exception is only allowed for TaskGraphExecutor.
        raise
      with self.thread_exception_lock:
        if self.thread_exception is None:
          log.debug('Storing error to raise later: %s', e)
          self.thread_exception = e
        else:
          # This indicates that the exception has been already stored for
          # another thread. We will simply log the traceback in this
          # case, since raising the error is not going to be handled by the
          # main thread anyway.
          log.error(e)
          log.debug(e, exc_info=sys.exc_info())
  return wrapper


class TaskGraphExecutor:
  """Executes an iterable of command_lib.storage.tasks.task.Task instances."""

  def __init__(
      self,
      task_iterator,
      max_process_count=multiprocessing.cpu_count(),
      thread_count=4,
      task_status_queue=None,
      progress_manager_args=None,
  ):
    """Initializes a TaskGraphExecutor instance.

    No threads or processes are started by the constructor.

    Args:
      task_iterator (Iterable[command_lib.storage.tasks.task.Task]): Task
        instances to execute.
      max_process_count (int): The number of processes to start.
      thread_count (int): The number of threads to start per process.
      task_status_queue (multiprocessing.Queue|None): Used by task to report its
        progress to a central location.
      progress_manager_args (task_status.ProgressManagerArgs|None):
        Determines what type of progress indicator to display.
    """

    self._task_iterator = iter(task_iterator)
    self._max_process_count = max_process_count
    self._thread_count = thread_count
    self._task_status_queue = task_status_queue
    self._progress_manager_args = progress_manager_args

    self._process_count = 0
    self._idle_thread_count = multiprocessing_context.Semaphore(value=0)

    self._worker_count = self._max_process_count * self._thread_count

    # Sends task_graph.TaskWrapper instances to child processes.
    # Size must be 1. go/lazy-process-spawning-addendum.
    self._task_queue = multiprocessing_context.Queue(maxsize=1)

    # Sends information about completed tasks to the main process.
    self._task_output_queue = multiprocessing_context.Queue(
        maxsize=self._worker_count)

    # Queue for informing worker_process_creator to create a new process.
    self._signal_queue = multiprocessing_context.Queue(
        maxsize=self._worker_count + 1)

    # Tracks dependencies between tasks in the executor to help ensure that
    # tasks returned by executed tasks are completed in the correct order.
    self._task_graph = task_graph_module.TaskGraph(
        top_level_task_limit=2 * self._worker_count)

    # Holds tasks without any dependencies.
    self._executable_tasks = task_buffer.TaskBuffer()

    # For storing exceptions.
    self.thread_exception = None
    self.thread_exception_lock = threading.Lock()

    self._accepting_new_tasks = True
    self._exit_code = 0
    self._debug_handler = _DebugSignalHandler()

    self.stack_trace_file_path = None
    if is_task_graph_debugging_enabled():
      try:
        with tempfile.NamedTemporaryFile(
            prefix='stack_trace', suffix='.txt', delete=False
        ) as f:
          self.stack_trace_file_path = f.name
      except IOError as e:
        log.error('Error creating stack trace file: %s', e)

    self._management_threads_name_to_function = {}

  def _add_worker_process(self):
    """Signal the worker process spawner to create a new process."""
    self._signal_queue.put(_CREATE_WORKER_PROCESS)
    self._process_count += 1

  @_store_exception
  def _get_tasks_from_iterator(self):
    """Adds tasks from self._task_iterator to the executor.

    This involves adding tasks to self._task_graph, marking them as submitted,
    and adding them to self._executable_tasks.
    """

    while self._accepting_new_tasks:
      try:
        task_object = next(self._task_iterator)
      except StopIteration:
        break
      task_wrapper = self._task_graph.add(task_object)
      if task_wrapper is None:
        # self._task_graph rejected the task.
        continue
      task_wrapper.is_submitted = True
      # Tasks from task_iterator should have a lower priority than tasks that
      # are spawned by other tasks. This helps keep memory usage under control
      # when a workload's task graph has a large branching factor.
      self._executable_tasks.put(task_wrapper, prioritize=False)

  @_store_exception
  def _add_executable_tasks_to_queue(self):
    """Sends executable tasks to consumer threads in child processes."""
    task_wrapper = None
    while True:
      if task_wrapper is None:
        task_wrapper = self._executable_tasks.get()
        if task_wrapper == _SHUTDOWN:
          break

      reached_process_limit = self._process_count >= self._max_process_count

      try:
        self._task_queue.put(task_wrapper, block=reached_process_limit)
        task_wrapper = None
      except queue.Full:
        if self._idle_thread_count.acquire(block=False):
          # Idle worker will take a task. Restore semaphore count.
          self._idle_thread_count.release()
        else:
          self._add_worker_process()

  @_store_exception
  def _handle_task_output(self):
    """Updates a dependency graph based on information from executed tasks."""
    while True:
      output = self._task_output_queue.get()
      if output == _SHUTDOWN:
        break

      executed_task_wrapper, task_output = output
      if task_output and task_output.messages:
        for message in task_output.messages:
          if message.topic in (task.Topic.CHANGE_EXIT_CODE,
                               task.Topic.FATAL_ERROR):
            self._exit_code = 1
            if message.topic == task.Topic.FATAL_ERROR:
              self._accepting_new_tasks = False

      submittable_tasks = self._task_graph.update_from_executed_task(
          executed_task_wrapper, task_output)

      for task_wrapper in submittable_tasks:
        task_wrapper.is_submitted = True
        self._executable_tasks.put(task_wrapper)

  def _clean_worker_process_spawner(self, worker_process_spawner):
    """Common method which carries out the required steps to clean up worker processes.

    Args:
      worker_process_spawner (Process): The worker parent process that we need
        to clean up.
    """
    # Shutdown all the workers.
    if worker_process_spawner.is_alive():
      self._signal_queue.put(_SHUTDOWN)
      worker_process_spawner.join()

    # Restore the debug signal handler.
    self._debug_handler.terminate()

  def run(self):
    """Executes tasks from a task iterator in parallel.

    Returns:
      An integer indicating the exit code. Zero indicates no fatal errors were
        raised.
    """
    shared_process_context = SharedProcessContext()
    self._debug_handler.install()
    worker_process_spawner = multiprocessing_context.Process(
        target=_process_factory,
        args=(
            self._task_queue,
            self._task_output_queue,
            self._task_status_queue,
            self._thread_count,
            self._idle_thread_count,
            self._signal_queue,
            shared_process_context,
            self.stack_trace_file_path
        ),
    )

    worker_process_cleaned_up = False
    try:
      worker_process_spawner.start()
      # It is now safe to start the progress_manager thread, since new processes
      # are started by a child process.
      with task_status.progress_manager(
          self._task_status_queue, self._progress_manager_args
      ):
        try:
          self._add_worker_process()

          get_tasks_from_iterator_thread = threading.Thread(
              target=self._get_tasks_from_iterator
          )
          add_executable_tasks_to_queue_thread = threading.Thread(
              target=self._add_executable_tasks_to_queue
          )
          handle_task_output_thread = threading.Thread(
              target=self._handle_task_output
          )

          get_tasks_from_iterator_thread.start()
          add_executable_tasks_to_queue_thread.start()
          handle_task_output_thread.start()

          if is_task_graph_debugging_enabled():
            self._management_threads_name_to_function[
                'get_tasks_from_iterator'
            ] = get_tasks_from_iterator_thread

            self._management_threads_name_to_function[
                'add_executable_tasks_to_queue'
            ] = add_executable_tasks_to_queue_thread

            self._management_threads_name_to_function['handle_task_output'] = (
                handle_task_output_thread
            )

            start_thread_for_task_graph_debugging(
                self._management_threads_name_to_function,
                self.stack_trace_file_path,
                self._task_graph,
                self._executable_tasks,
            )

          get_tasks_from_iterator_thread.join()
          try:
            self._task_graph.is_empty.wait()
          except console_io.OperationCancelledError:
            # If user hits ctrl-c, there will be no thread to pop tasks from the
            # graph. Python garbage collection will remove unstarted tasks in
            # the graph if we skip this endless wait.
            pass

          self._executable_tasks.put(_SHUTDOWN)
          self._task_output_queue.put(_SHUTDOWN)

          handle_task_output_thread.join()
          add_executable_tasks_to_queue_thread.join()
        finally:
          # By calling the clean in the finally block, we ensure that the
          # progress manager exit is called first.
          # We also handle the scenario where an exception may be thrown by the
          # progress manager it self.
          self._clean_worker_process_spawner(worker_process_spawner)
          worker_process_cleaned_up = True
    except Exception as e:  # pylint: disable=broad-exception-caught
      # In case we get an exception occurs while spinning up the worker process
      # spawner or during start of progress manager context, we need to
      # do a clean up, hence we use the following method which carries out
      # the neccesary steps.
      # Note that the clean up only occurs if an exception occurs. There is
      # another finally block within the progress manager context which will
      # execute if there is any exception or in case of compleition of internal
      # logic. If that is invoked, there is a small chance of this block being
      # invoked as well, but for that, we have the worker process clean-up flag.
      if not worker_process_cleaned_up:
        self._clean_worker_process_spawner(worker_process_spawner)

      # Raise it back as we still want main process to exit
      raise e

    # Queue close calls need to be outside the worker process spawner context
    # manager since the task queue need to be open for the shutdown logic.
    self._task_queue.close()
    self._task_output_queue.close()

    with self.thread_exception_lock:
      if self.thread_exception:
        raise self.thread_exception  # pylint: disable=raising-bad-type

    return self._exit_code
