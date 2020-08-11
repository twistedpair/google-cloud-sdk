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
"""Iterator wrapper that allows checking the plurality of remaining items."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class PluralityCheckableIterator:
  """Buffers items from an iterator to allow checking if more than one remains.

  Yields one item at a time from the buffer.
  """

  def __init__(self, iterator):
    self._iterator = iterator
    self._buffer = []

  def __iter__(self):
    return self

  def __next__(self):
    self._populate_buffer()
    if self._buffer:
      return self._buffer.pop(0)
    else:
      raise StopIteration

  def is_plural(self):
    self._populate_buffer(num_elements=2)
    return len(self._buffer) > 1

  def _populate_buffer(self, num_elements=1):
    while len(self._buffer) < num_elements:
      # TODO(b/162756667): Handle and test buffering exceptions.
      try:
        self._buffer.append(next(self._iterator))
      except StopIteration:
        break
