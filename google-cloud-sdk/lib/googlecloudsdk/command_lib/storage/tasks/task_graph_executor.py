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

from googlecloudsdk.command_lib.storage.tasks import task_buffer
from googlecloudsdk.command_lib.storage.tasks import task_graph as task_graph_module

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


def _thread_worker(task_queue, task_output_queue):
  """A consumer thread run in a child process.

  Args:
    task_queue (multiprocessing.Queue): Holds task_graph.TaskWrapper instances.
    task_output_queue (multiprocessing.Queue): Sends information about completed
      tasks back to the main process.
  """
  while True:
    task_wrapper = task_queue.get()

    # The task queue can be empty before a workload is complete if the last task
    # in the queue spawns additional tasks. This could lead to early shutdowns
    # if we rely on multiprocessing.Queue.empty() as an indicator of when
    # consumer threads are able to halt.
    if task_wrapper == _SHUTDOWN:
      break

    additional_task_iterators = task_wrapper.task.execute()
    task_output_queue.put((task_wrapper, additional_task_iterators))


def _process_worker(task_queue, task_output_queue, thread_count):
  """Starts a consumer thread pool.

  Args:
    task_queue (multiprocessing.Queue): Holds task_graph.TaskWrapper instances.
    task_output_queue (multiprocessing.Queue): Sends information about completed
      tasks back to the main process.
    thread_count (int): The number of threads to use.
  """
  # TODO(b/171299704): Add logic from gcloud_main.py to initialize GCE and
  # DevShell credentials in processes started with spawn.
  threads = []
  for _ in range(thread_count):
    thread = threading.Thread(
        target=_thread_worker, args=(task_queue, task_output_queue))
    thread.start()
    threads.append(thread)

  for thread in threads:
    thread.join()


class TaskGraphExecutor:
  """Executes an iterable of command_lib.storage.tasks.task.Task instances."""

  def __init__(self,
               task_iterator,
               process_count=multiprocessing.cpu_count(),
               thread_count=4):
    """Initializes a TaskGraphExecutor instance.

    No threads or processes are started by the constructor.

    Args:
      task_iterator (Iterable[command_lib.storage.tasks.task.Task]): Task
        instances to execute.
      process_count (int): The number of processes to start.
      thread_count (int): The number of threads to start per process.
    """

    self._task_iterator = task_iterator
    self._process_count = process_count
    self._thread_count = thread_count

    self._worker_count = self._process_count * self._thread_count

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

    # True if no tasks remain in self._task_iterator.
    self._task_iterator_exhausted = False

  def _get_tasks_from_iterator(self):
    """Adds tasks from self._task_iterator to the executor.

    This involves adding tasks to self._task_graph, marking them as submitted,
    and adding them to self._executable_tasks.
    """
    for task in self._task_iterator:
      task_wrapper = self._task_graph.add(task)
      task_wrapper.is_submitted = True
      # Tasks from task_iterator should have a lower priority than tasks that
      # are spawned by other tasks. This helps keep memory usage under control
      # when a workload's task graph has a large branching factor.
      self._executable_tasks.put(task_wrapper, prioritize=False)
    self._task_iterator_exhausted = True

  def _add_executable_tasks_to_queue(self):
    """Sends executable tasks to consumer threads in child processes."""
    # TODO(b/172676913): Ensure the executor exits gracefully on interrupts.
    while True:
      task_wrapper = self._executable_tasks.get()
      if task_wrapper == _SHUTDOWN:
        break
      self._task_queue.put(task_wrapper)

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

  def _handle_task_output(self):
    """Updates a dependency graph based on information from executed tasks."""
    while True:
      if self._task_iterator_exhausted and self._task_graph.is_empty():
        # We can safely send the _SHUTDOWN signal here since no potential
        # sources of new tasks remain.
        self._executable_tasks.put(_SHUTDOWN)
        for _ in range(self._worker_count):
          self._task_queue.put(_SHUTDOWN)
        break

      executed_task_wrapper, additional_task_iterators = (
          self._task_output_queue.get())
      submittable_tasks = self._update_graph_state_from_executed_task(
          executed_task_wrapper, additional_task_iterators)

      for task_wrapper in submittable_tasks:
        task_wrapper.is_submitted = True
        self._executable_tasks.put(task_wrapper)

  def run(self):
    """Executes tasks from a task iterator in parallel."""
    processes = []
    for _ in range(self._process_count):
      process = multiprocessing.Process(
          target=_process_worker,
          # _process_worker is not included in this class because several class
          # attributes are not synced across processes (notably the task buffer
          # and task graph). Passing _process_worker `self` would allow it to
          # unsafely access these attributes.
          args=(self._task_queue, self._task_output_queue, self._thread_count))
      process.start()
      processes.append(process)

    threading.Thread(target=self._get_tasks_from_iterator).start()
    threading.Thread(target=self._add_executable_tasks_to_queue).start()
    threading.Thread(target=self._handle_task_output).start()

    for process in processes:
      process.join()
