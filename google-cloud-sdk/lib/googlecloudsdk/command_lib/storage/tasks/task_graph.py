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
"""Implements logic for tracking task dependencies in task_graph_executor.

See go/parallel-processing-in-gcloud-storage for more information.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import threading
from typing import List

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.core import log


INITIAL_INDENT_LEVEL = 2
TASK_GRAPH_HEADER = 'Task Graph:'
TASK_WRAPPER_ID = '   - Task ID: {}\n'
TASK_DETAILS = (
    '    - Task: {}\n'
    '    - Dependency Count: {}\n'
    '    - Dependent Task IDs: {}\n'
    '    - Is Submitted: {}\n'
)


class TaskWrapper:
  """Embeds a Task instance in a dependency graph.

  Attributes:
    id (Hashable): A unique identifier for this task wrapper.
    task (googlecloudsdk.command_lib.storage.tasks.task.Task): An instance of a
      task class.
    dependency_count (int): The number of unexecuted dependencies this task has,
      i.e. this node's in-degree in a graph where an edge from A to B indicates
      that A must be executed before B.
    dependent_task_ids (Optional[Iterable[Hashable]]): The id of the tasks that
      require this task to be completed for their own completion. This value
      should be None if no tasks depend on this one.
    is_submitted (bool): True if this task has been submitted for execution.
  """

  def __init__(self, task_id, task, dependent_task_ids):
    self.id = task_id
    self.task = task
    self.dependency_count = 0
    self.dependent_task_ids = dependent_task_ids
    self.is_submitted = False

  def __str__(self):
    """Returns a string representation of the TaskWrapper."""
    return (
        TASK_WRAPPER_ID.format(self.id) +
        TASK_DETAILS.format(
            self.task.__class__.__name__,
            len(self.dependent_task_ids)
            if self.dependent_task_ids else 0,
            self.dependent_task_ids,
            self.is_submitted
        )
    )


class InvalidDependencyError(errors.Error):
  """Raised on attempts to create an invalid dependency.

  Invalid dependencies are self-dependencies and those that involve nodes that
  do not exist.
  """


class TaskGraph:
  """Tracks dependencies between Task instances.

  See googlecloudsdk.command_lib.storage.tasks.task.Task for the definition of
  the Task class.

  The public methods in this class are thread safe.

  Attributes:
    is_empty (threading.Event): is_empty.is_set() is True when the graph has no
      tasks in it.
  """

  def __init__(self, top_level_task_limit):
    """Initializes a TaskGraph instance.

    Args:
      top_level_task_limit (int): A top-level task is a task that no other tasks
        depend on for completion (i.e. dependent_task_ids is None). Adding
        top-level tasks with TaskGraph.add will block until there are fewer than
        this number of top-level tasks in the graph.
    """

    self.is_empty = threading.Event()
    self.is_empty.set()

    # Used to synchronize graph updates. This needs to be an RLock since this
    # lock is acquired by each recursive call to TaskGraph.complete.
    self._lock = threading.RLock()

    # A dict[int, TaskWrapper]. Maps ids to task wrapper instances for tasks
    # currently in the graph.
    self._task_wrappers_in_graph = {}

    # Acquired whenever a top-level task is added to the graph, and released
    # when a top-level task is completed. This helps keep memory usage under
    # control by limiting the graph size.
    self._top_level_task_semaphore = threading.Semaphore(top_level_task_limit)

  def add(self, task, dependent_task_ids=None):
    """Adds a task to the graph.

    Args:
      task (googlecloudsdk.command_lib.storage.tasks.task.Task): The task to be
        added.
      dependent_task_ids (Optional[List[Hashable]]): TaskWrapper.id attributes
        for tasks already in the graph that require the task being added to
        complete before being executed. This argument should be None for
        top-level tasks, which no other tasks depend on.

    Returns:
      A TaskWrapper instance for the task passed into this function, or None if
      task.parallel_processing_key was the same as another task's
      parallel_processing_key.

    Raises:
      InvalidDependencyError if any id in dependent_task_ids is not in the
      graph, or if a the add operation would have created a self-dependency.
    """
    is_top_level_task = dependent_task_ids is None
    if is_top_level_task:
      self._top_level_task_semaphore.acquire()

    with self._lock:
      if task.parallel_processing_key is not None:
        identifier = task.parallel_processing_key
      else:
        identifier = id(task)

      if identifier in self._task_wrappers_in_graph:
        if task.parallel_processing_key is not None:
          log.status.Print(
              'Skipping {} for {}. This can occur if a cp command results in '
              'multiple writes to the same resource.'.format(
                  task.__class__.__name__, task.parallel_processing_key))
        else:
          log.status.Print(
              'Skipping {}. This is probably because due to a bug that '
              'caused it to be submitted for execution more than once.'.format(
                  task.__class__.__name__))

        if is_top_level_task:
          self._top_level_task_semaphore.release()
        return

      task_wrapper = TaskWrapper(identifier, task, dependent_task_ids)

      for task_id in dependent_task_ids or []:
        try:
          self._task_wrappers_in_graph[task_id].dependency_count += 1
        except KeyError:
          raise InvalidDependencyError

      self._task_wrappers_in_graph[task_wrapper.id] = task_wrapper
      self.is_empty.clear()
    return task_wrapper

  def complete(self, task_wrapper):
    """Recursively removes a task and its parents from the graph if possible.

    Tasks can be removed only if they have been submitted for execution and have
    no dependencies. Removing a task can affect dependent tasks in one of two
    ways, if the removal left the dependent tasks with no dependencies:
     - If the dependent task has already been submitted, it can also be removed.
     - If the dependent task has not already been submitted, it can be
       submitted for execution.

    This method removes all tasks that removing task_wrapper allows, and returns
    all tasks that can be submitted after removing task_wrapper.

    Args:
      task_wrapper (TaskWrapper): The task_wrapper instance to remove.

    Returns:
      An Iterable[TaskWrapper] that yields tasks that are submittable after
      completing task_wrapper.
    """
    with self._lock:

      if task_wrapper.dependency_count:
        # This task has dependencies, so it cannot be removed from the graph and
        # cannot be submitted for execution.
        return []

      if not task_wrapper.is_submitted:
        # This task does not have dependencies and has not already been
        # submitted, so it can now be executed.
        return [task_wrapper]

      # At this point, this task does not have dependencies and has already
      # been submitted for execution. This means we can remove it from the
      # graph.
      del self._task_wrappers_in_graph[task_wrapper.id]
      if task_wrapper.dependent_task_ids is None:
        # We've completed a top-level task, so we should allow more to be added.
        self._top_level_task_semaphore.release()
        if not self._task_wrappers_in_graph:
          self.is_empty.set()
        return []

      # After removing this task, some dependent tasks may now be executable.
      # We can check this by decrementing all of their dependency counts and
      # recursively calling this function.
      submittable_tasks = []
      for task_id in task_wrapper.dependent_task_ids:
        dependent_task_wrapper = self._task_wrappers_in_graph[task_id]
        dependent_task_wrapper.dependency_count -= 1

        # Aggregates all of the submittable tasks found by recursive calls.
        submittable_tasks += self.complete(dependent_task_wrapper)
      return submittable_tasks

  def update_from_executed_task(self, executed_task_wrapper, task_output):
    r"""Updates the graph based on the output of an executed task.

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
      task_output (Optional[task.Output]): Additional tasks and
        messages returned by the task in executed_task_wrapper.

    Returns:
      An Iterable[task_graph.TaskWrapper] containing tasks that are ready to be
      executed after performing graph updates.
    """
    with self._lock:
      if (task_output is not None
          and task_output.messages is not None
          and executed_task_wrapper.dependent_task_ids is not None):
        for task_id in executed_task_wrapper.dependent_task_ids:
          dependent_task_wrapper = self._task_wrappers_in_graph[task_id]
          dependent_task_wrapper.task.received_messages.extend(
              task_output.messages)

      if task_output is None or not task_output.additional_task_iterators:
        # The executed task did not return new tasks, so the only ones newly
        # ready for execution will be those freed up after removing the executed
        # task.
        return self.complete(executed_task_wrapper)

      parent_tasks_for_next_layer = [executed_task_wrapper]

      # Tasks return additional tasks in the order they should be executed in,
      # but adding them to the graph is more easily done in reverse.
      for task_iterator in reversed(task_output.additional_task_iterators):
        dependent_task_ids = [
            task_wrapper.id for task_wrapper in parent_tasks_for_next_layer
        ]

        parent_tasks_for_next_layer = []
        for task in task_iterator:
          task_wrapper = self.add(task, dependent_task_ids=dependent_task_ids)
          if task_wrapper is not None:
            parent_tasks_for_next_layer.append(task_wrapper)
      # If the dependent tasks are skipped, then the parent tasks needs to be
      # marked as completed
      if not parent_tasks_for_next_layer:
        self.complete(executed_task_wrapper)
      return parent_tasks_for_next_layer

  def __str__(self):
    """Returns a string representation of the TaskGraph."""
    output: List[str] = [
        TASK_GRAPH_HEADER,
        f' - Empty: {self.is_empty.is_set()}',
        f' - Task Wrappers: {len(self._task_wrappers_in_graph)}',
    ]
    if self._task_wrappers_in_graph:
      printed_tasks = set()
      output.extend(
          self._print_task_wrapper_recursive(
              self._task_wrappers_in_graph.values(),
              INITIAL_INDENT_LEVEL,
              printed_tasks,
          )
      )
    else:
      output.append('No tasks in the graph to print.')
    return '\n'.join(output)

  def _print_task_wrapper_recursive(
      self, task_wrappers, indent_level, printed_tasks
  ) -> List[str]:
    """Recursively yields task wrappers and their dependencies.

    Example:
      Suppose we have task wrappers representing tasks with dependencies:

      task_wrapper1 = TaskWrapper(id='task1',
      dependent_task_ids=['task2', 'task3']),
      task_wrapper2 = TaskWrapper(id='task2', dependent_task_ids=['task4'])
      task_wrapper3 = TaskWrapper(id='task3', dependent_task_ids=[])
      task_wrapper4 = TaskWrapper(id='task4', dependent_task_ids=[])

      task_wrappers = [task_wrapper1, task_wrapper2,
                       task_wrapper3, task_wrapper4]

      Calling _print_task_wrapper_recursive(task_wrappers, 0, set())
      would produce:

      ['task1',
        '  task2',
        '    task4',
        '  task3']

      This shows the tasks and their dependencies formatted with appropriate
      indentation levels.

    Args:
      task_wrappers (list): List of task wrappers to print.
      indent_level (int): Current level of indentation for formatting.
      printed_tasks (set): Set of task IDs that have already been printed.


    Yields:
      List of formatted strings representing the task wrappers
      and their dependencies.
    """

    for task_wrapper in task_wrappers:
      if task_wrapper.id not in printed_tasks:
        printed_tasks.add(task_wrapper.id)
        yield str(task_wrapper)
        if task_wrapper.dependent_task_ids:
          dependent_task_wrappers = [
              self._task_wrappers_in_graph[task_id]
              for task_id in task_wrapper.dependent_task_ids
          ]
          yield from self._print_task_wrapper_recursive(
              dependent_task_wrappers, indent_level + 2, printed_tasks)
