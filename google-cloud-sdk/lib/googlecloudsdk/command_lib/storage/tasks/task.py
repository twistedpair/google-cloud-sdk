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

"""Abstract operation class that command operations will inherit from.

Should typically be executed in a task iterator through
googlecloudsdk.command_lib.storage.tasks.task_executor.

Manual execution example:

>>> class CopyTask(Task):
...   def __init__(self, src, dest):
...     ...
>>> my_copy_task = new CopyTask('~/Desktop/memes.jpg', '/kernel/')
>>> my_copy_task.Execute()
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import collections
import enum

from googlecloudsdk.core.util import debug_output

import six


class Topic(enum.Enum):
  API_DOWNLOAD_RESULT = 'api_download_result'
  CRC32C = 'crc32c'
  CREATED_RESOURCE = 'created_resource'
  ERROR = 'error'
  FATAL_ERROR = 'fatal_error'  # Error that should be reported to the user.
  MD5 = 'md5'
  UPLOADED_COMPONENT = 'uploaded_component'


# Holds information to be passed between tasks.
#
# Attributes:
#   topic (Topic): The type of information this message holds.
#   payload (Any): The information itself.
Message = collections.namedtuple(
    'Message',
    ['topic', 'payload']
)


# Holds information returned from Task.Execute.
#
# Note that because information here is sent between processes, all data in this
# class must be picklable.
#
# Attributes:
#   additional_task_iterators (Optional[Iterable[Iterable[Task]]]): Tasks to be
#     executed such that all tasks in each Iterable[Task] are executed before
#     any tasks in the next Iterable[Task]. Tasks within each Iterable[Task] are
#     unordered. For example, if this value were the following:
#
#     [
#       [UploadObjectTask(), UploadObjectTask(), UploadObjectTask()],
#       [ComposeObjectsTask()]
#     ]
#
#     All UploadObjectTasks should be completed before the ComposeObjectTask
#     could begin, but the UploadObjectTasks could be executed in parallel.
#   messages (Optional[Iterable[Message]]): Information to be passed to all
#     dependent tasks.
Output = collections.namedtuple(
    'Output',
    ['additional_task_iterators', 'messages']
)


class Task(six.with_metaclass(abc.ABCMeta, object)):
  """Abstract class to represent one command operation.

  Attributes:
    parallel_processing_key (Optional[Hashable]): Identifies a task during
      execution. If this value is not None, the executor will skip this task if
      another task being executed is using the same key. If this value is None,
      the executor will not skip any tasks based on it.
    received_messages (Iterable[Message]): Messages sent to this task
      by its dependencies.
    report_error (bool): If True, failure of this task should be reported
      by updating the exit_code to non-zero. Defaults to True.
  """

  def __init__(self):
    self.parallel_processing_key = None
    self.received_messages = []
    self.report_error = True

  @abc.abstractmethod
  def execute(self, task_status_queue=None):
    """Performs some work based on class attributes.

    Args:
      task_status_queue (multiprocessing.Queue): Used by task to report it
        progress to a central location.

    Returns:
      An Output instance, or None.
    """
    pass

  def exit_handler(self, error=None, task_status_queue=None):
    """Task executor calls this method on a completed task before discarding it.

    An example use case is a subclass that needs to report its final status and
    if it failed or succeeded at some operation.

    Args:
      error (Exception|None): Task executor may pass an error object.
      task_status_queue (multiprocessing.Queue): Used by task to report it
        progress to a central location.
    """
    del error, task_status_queue  # Unused.
    pass

  def __repr__(self):
    return debug_output.generic_repr(self)
