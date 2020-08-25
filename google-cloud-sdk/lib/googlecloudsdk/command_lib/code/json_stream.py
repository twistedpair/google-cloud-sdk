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
"""Read JSON objects from a stream."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import os
import sys

import six


def ReadJsonStream(file_obj, chunk_size_bytes=50, ignore_non_json=False):
  """Read the events from the skaffold event stream.

  Args:
    file_obj: A File object.
    chunk_size_bytes: Size of the chunk to read.
    ignore_non_json: Ignore data that is not valid json. If False, raise an
      exception on invalid json.

  Yields:
    Events from the JSON payloads.
  """
  for line in _ReadStreamingLines(file_obj, chunk_size_bytes=chunk_size_bytes):
    if not line:
      continue
    try:
      payload = json.loads(line)
    except ValueError as e:
      if ignore_non_json:
        continue
      else:
        six.reraise(type(e), e, sys.exc_info()[2])
    if not isinstance(payload, dict):
      continue
    yield payload


def _ReadStreamingLines(file_obj, chunk_size_bytes=50):
  """Read lines from a file object.

  Generally, in file objects, readlines() waits until either the buffer is full
  or the connection closes. This function returns the line of text as soon
  as new-line appears in the buffer, regardless if the buffer is full or not.
  This function serves the same purpose as readlines() except without the
  blocking.

  Args:
    file_obj: A file object.
    chunk_size_bytes: Size of the chunk to read.

  Yields:
    Lines as read from the response.
  """
  pending = None

  while True:
    chunk = os.read(file_obj.fileno(), chunk_size_bytes)
    if not chunk:
      break

    if pending is not None:
      chunk = pending + chunk
      pending = None

    lines = chunk.split(b'\n')
    if lines[-1]:
      pending = lines.pop()

    for line in lines:
      yield six.ensure_text(line)

  if pending:
    yield six.ensure_text(pending)
