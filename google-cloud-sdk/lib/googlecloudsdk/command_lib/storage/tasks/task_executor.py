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


def _ExecuteTasksSequential(task_iterator):
  """Executes task objects sequentially.

  Args:
    task_iterator (Iterable[Task]): An iterator for task objects.
  """
  for task in task_iterator:
    additional_task_iterators = task.execute()
    if additional_task_iterators is not None:
      for new_task_iterator in additional_task_iterators:
        _ExecuteTasksSequential(new_task_iterator)


def ExecuteTasks(task_iterator, is_parallel=False):
  """Call appropriate executor.

  Args:
    task_iterator: An iterator for task objects.
    is_parallel (boolean): Should tasks be executed in parallel.
  """
  process_count = properties.VALUES.storage.process_count.GetInt()
  thread_count = properties.VALUES.storage.thread_count.GetInt()

  if is_parallel and (process_count > 1 or thread_count > 1):
    task_graph_executor.TaskGraphExecutor(task_iterator,
                                          max_process_count=process_count,
                                          thread_count=thread_count).run()
  else:
    _ExecuteTasksSequential(task_iterator)
