# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Tools for monitoring and reporting task statuses."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import enum
import threading

from googlecloudsdk.command_lib.storage import thread_messages
from googlecloudsdk.core import log
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import scaled_integer

import six


# Recalculate throughput everytime last message time - window_start_time
# is greater than this time threshold.
_THROUGHPUT_WINDOW_THRESHOLD_SECONDS = 3


class OperationName(enum.Enum):
  DOWNLOADING = 'Downloading'
  INTRA_CLOUD_COPYING = 'Intra-Cloud Copying'
  DAISY_CHAIN_COPYING = 'Daisy Chain Copying'
  UPLOADING = 'Uploading'


class ProgressType(enum.Enum):
  FILES_AND_BYTES = 'FILES AND BYTES'
  COUNT = 'COUNT'


def _get_formatted_throughput(bytes_processed, time_delta):
  throughput_bytes = max(bytes_processed / time_delta, 0)
  return scaled_integer.FormatBinaryNumber(
      throughput_bytes, decimal_places=1) + '/s'


class _StatusTracker(six.with_metaclass(abc.ABCMeta, object)):
  """Abstract class for tracking and displaying operation progress."""

  @abc.abstractmethod
  def _get_status_string(self):
    """Generates string to illustrate progress to the user."""
    pass

  def _get_done_string(self):
    """Generates string for when StatusTracker exits."""
    return '\n'

  @abc.abstractmethod
  def add_message(self, status_message):
    """Processes task status message for printing and aggregation.

    Args:
      status_message (thread_messages.*): Message to process.
    """
    pass

  def start(self):
    self._progress_tracker = progress_tracker.ProgressTracker(
        message='  ',
        detail_message_callback=self._get_status_string,
        done_message_callback=self._get_done_string,
        no_spacing=True)
    self._progress_tracker.__enter__()
    return self

  def stop(self, exc_type, exc_val, exc_tb):
    if self._progress_tracker:
      self._progress_tracker.__exit__(exc_type, exc_val, exc_tb)


class _CountStatusTracker(_StatusTracker):
  """See super class. Tracks both file count and byte amount."""

  def __init__(self):
    super(_CountStatusTracker, self).__init__()
    self._completed = 0
    self._total_estimation = 0

  def _get_status_string(self):
    """See super class."""
    if self._total_estimation:
      file_progress_string = '{}/{}'.format(self._completed,
                                            self._total_estimation)
    else:
      file_progress_string = self._completed

    return 'Completed {}\r'.format(file_progress_string)

  def add_message(self, status_message):
    """See super class."""
    if isinstance(status_message, thread_messages.WorkloadEstimatorMessage):
      self._total_estimation += status_message.item_count
    elif isinstance(status_message, thread_messages.IncrementProgressMessage):
      self._completed += 1


class _FilesAndBytesStatusTracker(_StatusTracker):
  """See super class. Tracks both file count and byte amount."""

  def __init__(self):
    super(_FilesAndBytesStatusTracker, self).__init__()
    # For displaying progress.
    self._completed_files = 0
    self._processed_bytes = 0
    self._total_files_estimation = 0
    self._total_bytes_estimation = 0

    # For calculating average throughput.
    self._first_operation_time = None
    self._last_operation_time = None
    self._total_processed_bytes = 0

    # For calculating window throughput.
    self._window_start_time = None
    self._window_processed_bytes = 0
    # String for on-the-fly display.
    self._window_throughput = None

    # For keeping track of progress on different files.
    self._tracked_file_progress = {}

  def _get_status_string(self):
    """See super class."""
    scaled_processed_bytes = scaled_integer.FormatBinaryNumber(
        self._processed_bytes, decimal_places=1)
    if self._total_files_estimation:
      file_progress_string = '{}/{}'.format(self._completed_files,
                                            self._total_files_estimation)
    else:
      file_progress_string = self._completed_files
    if self._total_bytes_estimation:
      scaled_total_bytes_estimation = scaled_integer.FormatBinaryNumber(
          self._total_bytes_estimation, decimal_places=1)
      bytes_progress_string = '{}/{}'.format(scaled_processed_bytes,
                                             scaled_total_bytes_estimation)
    else:
      bytes_progress_string = scaled_processed_bytes

    if self._window_throughput:
      throughput_addendum_string = ' | ' + self._window_throughput
    else:
      throughput_addendum_string = ''

    return 'Completed files {} | {}{}\r'.format(file_progress_string,
                                                bytes_progress_string,
                                                throughput_addendum_string)

  def _update_throughput(self, status_message, processed_bytes):
    """Updates stats and recalculates throughput if past threshold."""
    if self._first_operation_time is None:
      self._first_operation_time = status_message.time
      self._window_start_time = status_message.time
    else:
      self._last_operation_time = status_message.time

    self._window_processed_bytes += processed_bytes

    time_delta = status_message.time - self._window_start_time
    if time_delta > _THROUGHPUT_WINDOW_THRESHOLD_SECONDS:
      self._window_throughput = _get_formatted_throughput(
          self._window_processed_bytes, time_delta)
      self._window_start_time = status_message.time
      self._window_processed_bytes = 0

  def _add_to_workload_estimation(self, status_message):
    """Adds WorloadEstimatorMessage info to total workload estimation."""
    self._total_files_estimation += status_message.item_count
    self._total_bytes_estimation += status_message.size

  def _add_component_progress(self, status_message):
    """Track progress of a multipart file operation."""
    file_url_string = status_message.source_url.url_string
    if file_url_string not in self._tracked_file_progress:
      self._tracked_file_progress[file_url_string] = {
          component_number: 0
          for component_number in range(status_message.total_components)
      }

    component_tracker = self._tracked_file_progress[file_url_string]
    component_number = status_message.component_number

    processed_component_bytes = status_message.current_byte - status_message.offset
    # status_message.current_byte includes bytes from past messages.
    newly_processed_bytes = (
        processed_component_bytes - component_tracker.get(component_number, 0))
    self._processed_bytes += newly_processed_bytes
    self._update_throughput(status_message, newly_processed_bytes)

    if processed_component_bytes == status_message.length:
      # Operation complete.
      component_tracker.pop(component_number, None)
      if not component_tracker:
        del self._tracked_file_progress[file_url_string]
        self._completed_files += 1
    else:
      component_tracker[component_number] = processed_component_bytes

  def _add_file_progress(self, status_message):
    """Track progress of a file operation."""
    file_url_string = status_message.source_url.url_string
    if file_url_string not in self._tracked_file_progress:
      self._tracked_file_progress[file_url_string] = 0

    processed_file_bytes = status_message.current_byte - status_message.offset
    known_progress = self._tracked_file_progress[file_url_string]
    # status_message.current_byte includes bytes from past messages.
    newly_processed_bytes = processed_file_bytes - known_progress
    self._processed_bytes += newly_processed_bytes
    self._update_throughput(status_message, newly_processed_bytes)

    if processed_file_bytes == status_message.length:
      # Operation complete.
      del self._tracked_file_progress[file_url_string]
      self._completed_files += 1
    else:
      self._tracked_file_progress[file_url_string] = processed_file_bytes

  def add_message(self, status_message):
    """See super class."""
    if isinstance(status_message, thread_messages.WorkloadEstimatorMessage):
      self._add_to_workload_estimation(status_message)
    elif isinstance(status_message, thread_messages.DetailedProgressMessage):
      # If files start getting counted twice, see b/225182075.
      if status_message.total_components:
        self._add_component_progress(status_message)
      else:
        self._add_file_progress(status_message)

  def stop(self, exc_type, exc_val, exc_tb):
    super(_FilesAndBytesStatusTracker, self).stop(exc_type, exc_val, exc_tb)

    if (self._first_operation_time is not None and
        self._last_operation_time is not None and
        self._first_operation_time != self._last_operation_time):
      # Don't use get_done_string because it may cause line wrapping.
      log.status.Print('\nAverage throughput: {}'.format(
          _get_formatted_throughput(
              self._processed_bytes,
              self._last_operation_time - self._first_operation_time)))


def status_message_handler(task_status_queue, status_tracker):
  """Thread method for submiting items from queue to tracker for processing."""
  unhandled_message_exists = False

  while True:
    status_message = task_status_queue.get()
    if status_message == '_SHUTDOWN':
      break
    if status_tracker:
      status_tracker.add_message(status_message)
    else:
      unhandled_message_exists = True

  if unhandled_message_exists:
    log.warning('Status message submitted to task_status_queue without a'
                ' manager to print it.')


def progress_manager(task_status_queue=None, progress_type=None):
  """Factory function that returns a ProgressManager instance.

  Args:
    task_status_queue (multiprocessing.Queue|None): Tasks can submit their
      progress messages here.
    progress_type (ProgressType|None): Determines what type of progress
      indicator to display.
  Returns:
    An instance of _ProgressManager or _NoOpProgressManager.
  """
  if task_status_queue is not None:
    return _ProgressManager(task_status_queue, progress_type)
  else:
    return _NoOpProgressManager()


class _ProgressManager:
  """Context manager for processing and displaying progress completing command.

  Ensure that this class is instantiated after all the child
  processes (if any) are started to prevent deadlock.
  """

  def __init__(self, task_status_queue, progress_type=None):
    """Initializes context manager.

    Args:
      task_status_queue (multiprocessing.Queue): Tasks can submit their progress
        messages here.
      progress_type (ProgressType|None): Determines what type of progress
        indicator to display.
    """
    self._progress_type = progress_type
    self._status_message_handler_thread = None
    self._status_tracker = None
    self._task_status_queue = task_status_queue

  def __enter__(self):
    if self._progress_type is ProgressType.COUNT:
      self._status_tracker = _CountStatusTracker()
    elif self._progress_type is ProgressType.FILES_AND_BYTES:
      self._status_tracker = _FilesAndBytesStatusTracker()

    self._status_message_handler_thread = threading.Thread(
        target=status_message_handler,
        args=(self._task_status_queue, self._status_tracker))
    self._status_message_handler_thread.start()

    if self._status_tracker:
      self._status_tracker.start()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self._task_status_queue.put('_SHUTDOWN')
    self._status_message_handler_thread.join()

    if self._status_tracker:
      self._status_tracker.stop(exc_type, exc_val, exc_tb)


class _NoOpProgressManager:
  """Progress Manager that does not do anything.

  Similar to contextlib.nullcontext, but it is available only for Python3.7+.
  """

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    del  exc_type, exc_val, exc_tb  # Unused.
    pass
