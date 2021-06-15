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
"""Utilities for representing a part of a stream."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from googlecloudsdk.command_lib.storage import hash_util
from googlecloudsdk.core.updater import installers

_PROGRESS_CALLBACK_THRESHOLD = 16777216  # 16 MiB in bytes.


class FilePart:
  """Implements a subset of the io.IOBase API for part of a stream.

  This class behaves as a contiguous subset of a given stream (e.g., this object
  will behave as though the desired part of the stream was written to a file,
  and the second file was opened).

  This is helpful for composite uploads since even when total_size is specified,
  apitools.transfer.Upload looks at the size of the source file to ensure
  that all bytes have been uploaded.
  """

  def __init__(self,
               stream,
               offset,
               length,
               digesters=None,
               progress_callback=None):
    """Initializes a FilePart instance.

    Args:
      stream (io.IOBase): The entire stream that we only want part of.
      offset (int): The position (in bytes) in the original file that
        corresponds to the first byte of the FilePart.
      length: The total number of bytes in the FilePart.
      digesters (dict[util.HashAlgorithm, hashlib hash object]): Values are
        updated with with data as it's read.
      progress_callback (func<int>): Accepts processed bytes and submits
        progress info for aggregation.
    """
    self._stream = stream
    self._length = length
    self._start_byte = offset
    self._end_byte = self._start_byte + self._length
    self._stream.seek(self._start_byte)
    self._digesters = digesters if digesters is not None else {}
    self._progress_callback = progress_callback

    self._bytes_read_since_last_progress_callback = 0
    self._progress_updated_with_end_byte = False
    self._checkpoint_digesters = None
    self._checkpoint_absolute_index = self._start_byte

  def _save_digesters_checkpoint(self):
    """Updates checkpoint that holds old hashes to optimize backwards seeks."""
    if not self._digesters:
      return
    self._checkpoint_absolute_index = self._stream.tell()
    self._checkpoint_digesters = hash_util.copy_digesters(self._digesters)

  def _catch_up_digesters(self, new_absolute_index):
    """Digests data between last and current stream position."""
    if not self._digesters:
      return
    if new_absolute_index < self._checkpoint_absolute_index:
      # Case 1: New position < Checkpoint position < Old position.
      self._stream.seek(self._start_byte)
      hash_util.reset_digesters(self._digesters)
    elif new_absolute_index < self._stream.tell():
      # Case 2: Checkpoint position < New position < Old position.
      self._stream.seek(self._checkpoint_absolute_index)
      self._digesters = hash_util.copy_digesters(self._checkpoint_digesters)
    elif new_absolute_index == self._stream.tell():
      # Case 3: Old position == New position.
      return
    # Case 4: Old position < New position.
    # Below digester updates are sufficient.

    self._save_digesters_checkpoint()
    while True:
      data = self._stream.read(
          min(new_absolute_index - self._stream.tell(),
              installers.WRITE_BUFFER_SIZE))
      if not data:
        break
      hash_util.update_digesters(self._digesters, data)

  def tell(self):
    """Returns the current position relative to the part's start byte."""
    return self._stream.tell() - self._start_byte

  def read(self, size=-1):
    """Returns `size` bytes from the underlying stream."""
    self._save_digesters_checkpoint()
    if size < 0:
      size = self._length
    size = min(size, self._end_byte - self._stream.tell())
    data = self._stream.read(max(0, size))
    if data:
      hash_util.update_digesters(self._digesters, data)
      if self._progress_callback:
        self._bytes_read_since_last_progress_callback += len(data)
        if (self._bytes_read_since_last_progress_callback >=
            _PROGRESS_CALLBACK_THRESHOLD):
          self._bytes_read_since_last_progress_callback = 0
          current_pos = self._stream.tell()
          self._progress_callback(current_pos)
          self._progress_updated_with_end_byte = current_pos == self._end_byte

    return data

  def seek(self, offset, whence=os.SEEK_SET):
    """Goes to a specific point in the stream.

    Args:
      offset (int): The number of bytes to move.
      whence: Specifies the position offset is added to.
        os.SEEK_END: offset is added to the last byte in the FilePart.
        os.SEEK_CUR: offset is added to the current position.
        os.SEEK_SET: offset is added to the first byte in the FilePart.

    Returns:
      The new relative position in the stream (int).
    """
    if whence == os.SEEK_END:
      new_absolute_index = offset + self._end_byte
    elif whence == os.SEEK_CUR:
      new_absolute_index = self._stream.tell() + offset
    else:
      new_absolute_index = offset + self._start_byte

    self._catch_up_digesters(new_absolute_index)
    # Above may perform seek, but repeating is harmless.
    return self._stream.seek(new_absolute_index) - self._start_byte

  def close(self):
    """Closes the underlying stream."""
    if (self._progress_callback and not self._progress_updated_with_end_byte):
      self._progress_callback(self._stream.tell())
      self._progress_updated_with_end_byte = True
    self._stream.close()

  def __enter__(self):
    return self

  def __exit__(self, *unused_args):
    self.close()
