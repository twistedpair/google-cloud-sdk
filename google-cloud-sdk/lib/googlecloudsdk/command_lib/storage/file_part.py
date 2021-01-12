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


class FilePart:
  """Implements a subset of the io.IOBase API for part of a stream.

  This class behaves as a contiguous subset of a given stream (e.g., this object
  will behave as though the desired part of the stream was written to a file,
  and the second file was opened).

  This is helpful for composite uploads since even when total_size is specified,
  apitools.transfer.Upload looks at the size of the source file to ensure
  that all bytes have been uploaded.
  """

  def __init__(self, stream, offset, length):
    """Initializes a FilePart instance.

    Args:
      stream (io.IOBase): The entire stream that we only want part of.
      offset (int): The position (in bytes) in the original file that
        corresponds to the first byte of the FilePart.
      length: The total number of bytes in the FilePart.
    """
    self._stream = stream
    self._length = length
    self._start_byte = offset
    self._end_byte = self._start_byte + self._length
    self._stream.seek(self._start_byte)

  def tell(self):
    """Returns the current position relative to the part's start byte."""
    return self._stream.tell() - self._start_byte

  def read(self, size=-1):
    """Returns `size` bytes from the underlying stream."""
    if size < 0:
      size = self._length
    size = min(size, self._end_byte - self._stream.tell())
    return self._stream.read(max(0, size))

  def seek(self, offset, whence=os.SEEK_SET):
    """Goes to a specific point in the stream.

    Args:
      offset (int): The number of bytes to move.
      whence: Specifies the position offset is added to.
        os.SEEK_END: offset is added to the last byte in the FilePart.
        os.SEEK_CUR: offset is added to the current position.
        os.SEEK_SET: offset is added to the first byte in the FilePart.

    Returns:
      The new absolute position in the stream (int).
    """
    if whence == os.SEEK_END:
      return self._stream.seek(offset + self._end_byte) - self._start_byte
    elif whence == os.SEEK_CUR:
      return self._stream.seek(offset, whence) - self._start_byte
    else:
      return self._stream.seek(self._start_byte + offset) - self._start_byte

  def close(self):
    """Closes the underlying stream."""
    self._stream.close()

  def __enter__(self):
    return self

  def __exit__(self, *unused_args):
    self.close()
