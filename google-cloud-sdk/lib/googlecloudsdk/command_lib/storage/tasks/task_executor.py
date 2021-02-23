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
from googlecloudsdk.command_lib.storage.tasks import task_status
from googlecloudsdk.core import properties


def _ExecuteTasksSequential(task_iterator, task_status_queue=None):
  """Executes task objects sequentially.

  Args:
    task_iterator (Iterable[Task]): An iterator for task objects.
    task_status_queue (multiprocessing.Queue|None): Used by task to report it
      progress to a central location.
  """
  for task in task_iterator:
    additional_task_iterators = task.execute(
        task_status_queue=task_status_queue)
    if additional_task_iterators is not None:
      for new_task_iterator in additional_task_iterators:
        _ExecuteTasksSequential(new_task_iterator, task_status_queue)


def ExecuteTasks(task_iterator, is_parallel=False, progress_type=None):
  """Call appropriate executor.

  Args:
    task_iterator: An iterator for task objects.
    is_parallel (boolean): Should tasks be executed in parallel.
    progress_type (task_status.ProgressType|None): Determines what type of
      task progress should be tracked and displayed.
  """
  process_count = properties.VALUES.storage.process_count.GetInt()
  thread_count = properties.VALUES.storage.thread_count.GetInt()

  with task_status.ProgressManager(progress_type) as progress_manager:
    if is_parallel and (process_count > 1 or thread_count > 1):
      task_graph_executor.TaskGraphExecutor(
          task_iterator,
          max_process_count=process_count,
          thread_count=thread_count,
          task_status_queue=progress_manager.task_status_queue).run()
    else:
      _ExecuteTasksSequential(task_iterator, progress_manager.task_status_queue)
