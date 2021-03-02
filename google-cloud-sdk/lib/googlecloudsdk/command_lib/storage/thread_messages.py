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
"""Messages parallel workers might send to the main thread."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import threading


class ProgressMessage(object):
  """Message class for sending information about operation progress.

  This class contains specific information on the progress of operating on a
  file, cloud object, or single component.

  Attributes:
    size (int): Total size of file/component in bytes.
    processed_bytes (int): Number of bytes already operated on.
    finished (bool): Indicates if the operation is complete.
    time (float): When message was created (seconds since epoch).
    source_url (StorageUrl): Represents source of data used by operation.
    destination_url (StorageUrl|None): Represents destination of data used by
      operation. None for unary operations like hashing.
    component_number (int|None): If a multipart operation, indicates the
      component number.
    total_components (int|None): If a multipart operation, indicates the
        total number of components.
    operation_name (task_status.OperationName|None): Name of the operation
      running on target data.
    process_id (int|None): Identifies process that produced the instance of this
      message (overridable for testing).
    thread_id (int|None): Identifies thread that produced the instance of this
      message (overridable for testing).
  """

  def __init__(self,
               size,
               processed_bytes,
               time,
               source_url,
               destination_url=None,
               component_number=None,
               total_components=None,
               operation_name=None,
               process_id=None,
               thread_id=None):
    """Initializes a ProgressMessage. See attributes docstring for arguments."""
    self.size = size
    self.processed_bytes = processed_bytes
    self.finished = (size == processed_bytes)
    self.time = time

    self.source_url = source_url
    self.destination_url = destination_url
    self.component_number = component_number
    self.total_components = total_components

    self.operation_name = operation_name
    self.process_id = process_id or os.getpid()
    self.thread_id = thread_id or threading.current_thread().ident

  def __repr__(self):
    """Returns a string with a valid constructor for this message."""
    destination_url_string = ("'{}'".format(
        self.destination_url)) if self.destination_url else None
    operation_name_string = ("'{}'".format(
        self.operation_name.value)) if self.operation_name else None
    return ("{class_name}(time={time}, size={size},"
            " processed_bytes={processed_bytes}, source_url='{source_url}',"
            " destination_url={destination_url},"
            " component_number={component_number},"
            " operation_name={operation_name}, process_id={process_id},"
            " thread_id={thread_id})").format(
                class_name=self.__class__.__name__,
                time=self.time,
                size=self.size,
                processed_bytes=self.processed_bytes,
                source_url=self.source_url,
                destination_url=destination_url_string,
                component_number=self.component_number,
                operation_name=operation_name_string,
                process_id=self.process_id,
                thread_id=self.thread_id)
