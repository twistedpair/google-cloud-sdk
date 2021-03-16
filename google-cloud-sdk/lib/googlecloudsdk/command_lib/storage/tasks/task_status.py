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

import enum
import multiprocessing
import threading

from googlecloudsdk.core import log
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import scaled_integer


class OperationName(enum.Enum):
  DOWNLOADING = 'Downloading'
  INTRA_CLOUD_COPYING = 'Intra-Cloud Copying'
  DAISY_CHAIN_COPYING = 'Daisy Chain Copying'
  UPLOADING = 'Uploading'


class ProgressType(enum.Enum):
  FILES_AND_BYTES = 'FILES AND BYTES'
  FILES = 'FILES'


class _StatusTracker:
  """Aggregates and prints information on task statuses.

  We use "start" and "stop" instead of "__enter__" and "__exit__" because
  this class should only be used by ProgressManager as a non-context-manager.
  """

  def __init__(self):
    self._completed_files = 0
    self._processed_bytes = 0
    self._tracked_file_progress = {}
    self._progress_tracker = None

  def _get_status_string(self):
    # TODO(b/180047352) Avoid having other output print on the same line.
    return '\rCopied files {} | {}'.format(
        self._completed_files,
        scaled_integer.FormatBinaryNumber(
            self._processed_bytes, decimal_places=1))

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

    processed_bytes = status_message.current_byte - status_message.offset
    # status_message.current_byte includes bytes from past messages.
    self._processed_bytes += (
        processed_bytes - component_tracker.get(component_number, 0))
    if processed_bytes == status_message.length:
      # Operation complete.
      component_tracker.pop(component_number, None)
      if not component_tracker:
        self._tracked_file_progress[file_url_string] = -1
        self._completed_files += 1
    else:
      component_tracker[component_number] = processed_bytes

  def _add_file_progress(self, status_message):
    """Track progress of a file operation."""
    file_url_string = status_message.source_url.url_string
    if file_url_string not in self._tracked_file_progress:
      self._tracked_file_progress[file_url_string] = 0

    processed_bytes = status_message.current_byte - status_message.offset
    known_progress = self._tracked_file_progress[file_url_string]
    # status_message.current_byte includes bytes from past messages.
    self._processed_bytes += processed_bytes - known_progress

    if processed_bytes == status_message.length:
      # Operation complete.
      self._tracked_file_progress[file_url_string] = -1
      self._completed_files += 1
    else:
      self._tracked_file_progress[file_url_string] = processed_bytes

  def add_message(self, status_message):
    """Processes task status message for printing and aggregation.

    Args:
      status_message (thread_messages.ProgressMessage): Message to process.
    """
    if self._tracked_file_progress.get(status_message.source_url.url_string,
                                       0) == -1:
      # File has already been downloaded. No processing to do.
      return
    if status_message.total_components:
      self._add_component_progress(status_message)
    else:
      self._add_file_progress(status_message)

  def start(self):
    self._progress_tracker = progress_tracker.ProgressTracker(
        message='Starting operation',
        detail_message_callback=self._get_status_string)
    self._progress_tracker.__enter__()
    return self

  def stop(self, exc_type, exc_val, exc_tb):
    if self._progress_tracker:
      return self._progress_tracker.__exit__(exc_type, exc_val, exc_tb)


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


class ProgressManager:
  """Context manager for processing and displaying progress completing command.

  Attributes:
    task_status_queue (multiprocessing.Queue): Tasks can submit their progress
      messages here.
  """

  def __init__(self, progress_type=None):
    """Initializes context manager.

    Args:
      progress_type (ProgressType|None): Determines what type of progress
        indicator to display.
    """
    super(ProgressManager, self).__init__()

    self._progress_type = progress_type
    self._status_message_handler_thread = None
    self._status_tracker = None
    self.task_status_queue = multiprocessing.Queue()

  def __enter__(self):
    if self._progress_type is ProgressType.FILES_AND_BYTES:
      self._status_tracker = _StatusTracker()

    self._status_message_handler_thread = threading.Thread(
        target=status_message_handler,
        args=(self.task_status_queue, self._status_tracker))
    self._status_message_handler_thread.start()

    if self._status_tracker:
      self._status_tracker.start()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.task_status_queue.put('_SHUTDOWN')
    self._status_message_handler_thread.join()

    if self._progress_type is ProgressType.FILES_AND_BYTES:
      self._status_tracker.stop(exc_type, exc_val, exc_tb)
