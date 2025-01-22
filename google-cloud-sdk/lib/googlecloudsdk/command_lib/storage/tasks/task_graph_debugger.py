# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Utilities for debugging task graph."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re
import sys
import threading
import traceback
from typing import Dict, Iterator

from googlecloudsdk.command_lib.storage.tasks import task_buffer
from googlecloudsdk.command_lib.storage.tasks import task_graph as task_graph_module
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files


def is_task_graph_debugging_enabled() -> bool:
  """Whether task graph debugging is enabled.

  Returns:
      bool: True if task graph debugging is enabled else False.
  """
  return properties.VALUES.storage.enable_task_graph_debugging.GetBool()


def get_time_interval_between_snapshots() -> int:
  """Returns the time interval in seconds between two consecutive snapshots."""
  return (
      properties.VALUES.storage.task_graph_debugging_snapshot_duration.GetInt()
  )


def yield_stack_traces() -> Iterator[str]:
  """Retrieve stack traces for all the threads in the current process."""
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


def _is_task_graph_empty(task_graph: task_graph_module.TaskGraph) -> bool:
  """Checks if the task graph is empty."""
  return task_graph.is_empty.is_set()


def _is_task_buffer_empty(task__buffer: task_buffer.TaskBuffer) -> bool:
  """Checks if the task buffer is empty."""
  return task__buffer.size() == 0


def task_graph_debugger_worker(
    management_threads_name_to_function: Dict[str, threading.Thread],
    stack_trace_file: str,
    task_graph: task_graph_module.TaskGraph,
    task__buffer: task_buffer.TaskBuffer,
    delay_seconds: int,
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
  is_task_graph_empty = _is_task_graph_empty(task_graph)
  is_task_buffer_empty = _is_task_buffer_empty(task__buffer)
  # Set it to true to ensure that the debugger worker prints the status
  # atleast once.
  is_some_management_thread_alive = True

  while (
      is_some_management_thread_alive
      or not is_task_graph_empty
      or not is_task_buffer_empty
  ):
    print_management_thread_stacks(management_threads_name_to_function)
    print_worker_thread_stack_traces(stack_trace_file)
    log.status.Print(str(task_graph))
    log.status.Print(str(task__buffer))

    is_task_graph_empty = _is_task_graph_empty(task_graph)
    is_task_buffer_empty = _is_task_buffer_empty(task__buffer)

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
            get_time_interval_between_snapshots(),
        ),
    )
    thread_for_task_graph_debugging.start()

  except Exception as e:  # pylint: disable=broad-except
    log.error(f'Error starting thread: {e}')


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
