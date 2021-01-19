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

import multiprocessing
import threading

from googlecloudsdk.command_lib import crash_handling
from googlecloudsdk.command_lib.storage.tasks import task_buffer
from googlecloudsdk.command_lib.storage.tasks import task_graph as task_graph_module
from googlecloudsdk.core import log


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


@crash_handling.CrashManager
def _thread_worker(task_queue, task_output_queue, idle_thread_count):
  """A consumer thread run in a child process.

  Args:
    task_queue (multiprocessing.Queue): Holds task_graph.TaskWrapper instances.
    task_output_queue (multiprocessing.Queue): Sends information about completed
      tasks back to the main process.
    idle_thread_count (multiprocessing.Semaphore): Keeps track of how many
      threads are busy. Useful for spawning new workers if all threads are busy.
  """
  while True:
    task_wrapper = task_queue.get()
    if task_wrapper == _SHUTDOWN:
      break
    idle_thread_count.acquire()

    try:
      additional_task_iterators = task_wrapper.task.execute()
    # pylint: disable=broad-except
    # If any exception is raised, it will prevent the executor from exiting.
    except Exception as exception:
      log.error(exception)
      # TODO(b/174488717): Skip parent tasks when a child task raises an error.
      additional_task_iterators = None
    # pylint: enable=broad-except

    task_output_queue.put((task_wrapper, additional_task_iterators))
    idle_thread_count.release()


@crash_handling.CrashManager
def _process_worker(task_queue, task_output_queue, thread_count,
                    idle_thread_count):
  """Starts a consumer thread pool.

  Args:
    task_queue (multiprocessing.Queue): Holds task_graph.TaskWrapper instances.
    task_output_queue (multiprocessing.Queue): Sends information about completed
      tasks back to the main process.
    thread_count (int): Number of threads the process should spawn.
    idle_thread_count (multiprocessing.Semaphore): Passed on to worker threads.
  """
  threads = []
  # TODO(b/171299704): Add logic from gcloud_main.py to initialize GCE and
  # DevShell credentials in processes started with spawn.
  for _ in range(thread_count):
    thread = threading.Thread(
        target=_thread_worker,
        args=(task_queue, task_output_queue, idle_thread_count))
    thread.start()
    threads.append(thread)

  for thread in threads:
    thread.join()


class TaskGraphExecutor:
  """Executes an iterable of command_lib.storage.tasks.task.Task instances."""

  def __init__(self,
               task_iterator,
               max_process_count=multiprocessing.cpu_count(),
               thread_count=4):
    """Initializes a TaskGraphExecutor instance.

    No threads or processes are started by the constructor.

    Args:
      task_iterator (Iterable[command_lib.storage.tasks.task.Task]): Task
        instances to execute.
      max_process_count (int): The number of processes to start.
      thread_count (int): The number of threads to start per process.
    """
    self._task_iterator = iter(task_iterator)
    self._max_process_count = max_process_count
    self._thread_count = thread_count

    self._processes = []
    self._idle_thread_count = multiprocessing.Semaphore(value=0)

    self._worker_count = self._max_process_count * self._thread_count
    # If a process forks at the same time as _task_iterator generates a value,
    # it will cause obscure hanging.
    self._process_start_lock = multiprocessing.Lock()

    # Sends task_graph.TaskWrapper instances to child processes.
    self._task_queue = multiprocessing.Queue(maxsize=self._worker_count)

    # Sends information about completed tasks to the main process.
    self._task_output_queue = multiprocessing.Queue(maxsize=self._worker_count)

    # Tracks dependencies between tasks in the executor to help ensure that
    # tasks returned by executed tasks are completed in the correct order.
    self._task_graph = task_graph_module.TaskGraph(
        top_level_task_limit=2 * self._worker_count)

    # Holds tasks without any dependencies.
    self._executable_tasks = task_buffer.TaskBuffer()

  def _add_worker_process(self):
    """Creates and triggers worker process."""
    # Increase total thread count by number of threads available per processor.
    for _ in range(self._thread_count):
      self._idle_thread_count.release()

    process = multiprocessing.Process(
        target=_process_worker,
        args=(self._task_queue, self._task_output_queue, self._thread_count,
              self._idle_thread_count))
    self._processes.append(process)
    with self._process_start_lock:
      process.start()

  @crash_handling.CrashManager
  def _get_tasks_from_iterator(self):
    """Adds tasks from self._task_iterator to the executor.

    This involves adding tasks to self._task_graph, marking them as submitted,
    and adding them to self._executable_tasks.
    """

    while True:
      try:
        with self._process_start_lock:
          task = next(self._task_iterator)
      except StopIteration:
        break
      task_wrapper = self._task_graph.add(task)
      if task_wrapper is None:
        # self._task_graph rejected the task.
        continue
      task_wrapper.is_submitted = True
      # Tasks from task_iterator should have a lower priority than tasks that
      # are spawned by other tasks. This helps keep memory usage under control
      # when a workload's task graph has a large branching factor.
      self._executable_tasks.put(task_wrapper, prioritize=False)

  @crash_handling.CrashManager
  def _add_executable_tasks_to_queue(self):
    """Sends executable tasks to consumer threads in child processes."""
    while True:
      task_wrapper = self._executable_tasks.get()
      if task_wrapper == _SHUTDOWN:
        break
      self._task_queue.put(task_wrapper)

      if len(self._processes) < self._max_process_count:
        if self._idle_thread_count.acquire(block=False):
          # Idle worker will take the new task. Restore semaphore count.
          self._idle_thread_count.release()
        else:
          # Create workers because current workers are busy.
          self._add_worker_process()

  def _update_graph_state_from_executed_task(self, executed_task_wrapper,
                                             additional_task_iterators):
    r"""Updates self._task_graph based on the output of an executed task.

    If some googlecloudsdk.command_lib.storage.task.Task instance `a` returns
    the following iterables of tasks: [[b, c], [d, e]], we need to update the
    graph as follows to ensure they are executed appropriately.

           /-- d <-\--/- b
      a <-/         \/
          \         /\
           \-- e <-/--\- c

    After making these updates, `b` and `c` are ready for submission. If a task
    does not return any new tasks, then it will be removed from the graph,
    potentially freeing up tasks that depend on it for execution.

    See go/parallel-processing-in-gcloud-storage#heading=h.y4o7a9hcs89r for a
    more thorough description of the updates this method performs.

    Args:
      executed_task_wrapper (task_graph.TaskWrapper): Contains information about
        how a completed task fits into a dependency graph.
      additional_task_iterators (Optional[Iterable[Iterable[Task]]]): The
        additional tasks returned by the task in executed_task_wrapper.

    Returns:
      An Iterable[task_graph.TaskWrapper] containing tasks that are ready to be
      executed after performing graph updates.
    """
    if additional_task_iterators is None:
      # The executed task did not return new tasks, so the only ones newly ready
      # for execution will be those freed up after removing the executed task.
      return self._task_graph.complete(executed_task_wrapper)

    parent_tasks_for_next_layer = [executed_task_wrapper]

    # Tasks return additional tasks in the order they should be executed in,
    # but adding them to the graph is more easily done in reverse.
    for task_iterator in reversed(additional_task_iterators):
      dependent_task_ids = [
          task_wrapper.id for task_wrapper in parent_tasks_for_next_layer
      ]

      parent_tasks_for_next_layer = [
          self._task_graph.add(task, dependent_task_ids=dependent_task_ids)
          for task in task_iterator
      ]

    return parent_tasks_for_next_layer

  @crash_handling.CrashManager
  def _handle_task_output(self):
    """Updates a dependency graph based on information from executed tasks."""
    while True:
      task_output = self._task_output_queue.get()
      if task_output == _SHUTDOWN:
        break

      executed_task_wrapper, additional_task_iterators = task_output
      submittable_tasks = self._update_graph_state_from_executed_task(
          executed_task_wrapper, additional_task_iterators)

      for task_wrapper in submittable_tasks:
        task_wrapper.is_submitted = True
        self._executable_tasks.put(task_wrapper)

  def run(self):
    """Executes tasks from a task iterator in parallel."""
    self._add_worker_process()

    get_tasks_from_iterator_thread = threading.Thread(
        target=self._get_tasks_from_iterator)
    add_executable_tasks_to_queue_thread = threading.Thread(
        target=self._add_executable_tasks_to_queue)
    handle_task_output_thread = threading.Thread(
        target=self._handle_task_output)

    get_tasks_from_iterator_thread.start()
    add_executable_tasks_to_queue_thread.start()
    handle_task_output_thread.start()

    get_tasks_from_iterator_thread.join()
    self._task_graph.is_empty.wait()

    self._executable_tasks.put(_SHUTDOWN)
    for _ in self._processes:
      for _ in range(self._thread_count):
        self._task_queue.put(_SHUTDOWN)
    self._task_output_queue.put(_SHUTDOWN)

    handle_task_output_thread.join()
    add_executable_tasks_to_queue_thread.join()
    for process in self._processes:
      process.join()

    self._task_queue.close()
    self._task_output_queue.close()
