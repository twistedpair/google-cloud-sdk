# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Task for listing, sorting, and writing files for rsync."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import errno
import heapq
import itertools
import os
import threading

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import rsync_command_util
from googlecloudsdk.command_lib.storage import wildcard_iterator
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files


class GetSortedContainerContentsTask(task.Task):
  """Updates a local file's POSIX metadata."""

  def __init__(
      self,
      container,
      output_path,
      recurse=False,
  ):
    """Initializes task.

    Args:
      container (Resource): Contains path of files to fetch.
      output_path (str): Where to write final sorted file list.
      recurse (bool): Gather nested items in container.
    """
    super(GetSortedContainerContentsTask, self).__init__()
    self._container_path = container.storage_url.join(
        '**' if recurse else '*'
    ).versionless_url_string
    self._output_path = output_path

    self._worker_id = 'process {} thread {}'.format(
        os.getpid(), threading.get_ident()
    )

  def execute(self, task_status_queue=None):
    del task_status_queue  # Unused.
    file_iterator = iter(
        wildcard_iterator.get_wildcard_iterator(
            self._container_path,
            files_only=True,
        )
    )
    chunk_count = file_count = 0
    chunk_file_paths = []
    chunk_file_readers = []
    # TODO(b/267511582): Test perf of different default chunk sizes.
    chunk_size = properties.VALUES.storage.rsync_list_chunk_size.GetInt()
    try:
      while True:
        resources_chunk = list(itertools.islice(file_iterator, chunk_size))
        if not resources_chunk:
          break
        chunk_count += 1
        file_count += len(resources_chunk)
        log.status.Print(
            'At {}, worker {} listed {}...'.format(
                self._container_path, self._worker_id, file_count
            )
        )

        chunk_file_paths.append(
            rsync_command_util.get_hashed_list_file_path(
                self._container_path, chunk_count
            )
        )
        sorted_encoded_chunk = sorted(
            [
                rsync_command_util.get_csv_line_from_resource(x)
                for x in resources_chunk
            ]
        )
        sorted_encoded_chunk.append('')  # Add trailing newline.
        files.WriteFileContents(
            chunk_file_paths[-1],
            '\n'.join(sorted_encoded_chunk),
        )

      chunk_file_readers = [files.FileReader(path) for path in chunk_file_paths]
      with files.FileWriter(self._output_path, create_path=True) as file_writer:
        file_writer.writelines(heapq.merge(*chunk_file_readers))

    except OSError as e:
      if e.errno == errno.EMFILE:
        raise errors.Error(
            'Too many open chunk files. Try increasing the'
            ' size with `gcloud config set storage/rsync_list_chunk_size`.'
            ' The current size is {}.'.format(chunk_size)
        )
      raise e

    finally:
      for reader in chunk_file_readers:
        try:
          reader.close()
        except Exception as e:  # pylint:disable=broad-except
          log.debug('Failed to close file reader {}: {}'.format(reader.name, e))
      for path in chunk_file_paths:
        rsync_command_util.try_to_delete_file(path)

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (
        self._container_path == other._container_path
        and self._output_path == other._output_path
    )
