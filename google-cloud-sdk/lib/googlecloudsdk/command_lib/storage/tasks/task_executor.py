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

"""Function for executing the tasks contained in a Task Iterator.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.storage.tasks import task_graph_executor
from googlecloudsdk.core import properties


def _ExecuteTasksSequential(task_iterator,
                            received_messages=None,
                            task_status_queue=None):
  """Executes task objects sequentially.

  Args:
    task_iterator (Iterable[task.Task]): An iterator for task objects.
    received_messages (Iterable[task.Message]): Messages sent to each
      task in task_iterator.
    task_status_queue (multiprocessing.Queue|None): Used by task to report it
      progress to a central location.

  Returns:
    Iterable[task.Message] emitted by tasks in task_iterator.
  """
  messages_from_current_task_iterator = []
  for task in task_iterator:
    if received_messages is not None:
      task.received_messages = received_messages
    task_output = task.execute(task_status_queue=task_status_queue)

    if task_output is None:
      continue

    if task_output.messages is not None:
      messages_from_current_task_iterator.extend(task_output.messages)

    if task_output.additional_task_iterators is not None:
      messages_for_dependent_tasks = []
      for additional_task_iterator in task_output.additional_task_iterators:
        messages_for_dependent_tasks = _ExecuteTasksSequential(
            additional_task_iterator,
            messages_for_dependent_tasks,
            task_status_queue=task_status_queue)

  return messages_from_current_task_iterator


def ExecuteTasks(task_iterator, is_parallel=False, task_status_queue=None):
  """Call appropriate executor.

  Args:
    task_iterator: An iterator for task objects.
    is_parallel (boolean): Should tasks be executed in parallel.
    task_status_queue (multiprocessing.Queue|None): Used by task to report its
      progress to a central location.
  """
  process_count = properties.VALUES.storage.process_count.GetInt()
  thread_count = properties.VALUES.storage.thread_count.GetInt()

  if is_parallel and (process_count > 1 or thread_count > 1):
    task_graph_executor.TaskGraphExecutor(
        task_iterator,
        max_process_count=process_count,
        thread_count=thread_count,
        task_status_queue=task_status_queue).run()
  else:
    _ExecuteTasksSequential(
        task_iterator, task_status_queue=task_status_queue)
