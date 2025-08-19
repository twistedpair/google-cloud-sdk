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
"""Download utils for Artifact Registry commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from concurrent import futures
import json
import os
import sys
import threading

from apitools.base.py import transfer
from googlecloudsdk.command_lib.artifacts import requests
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.credentials import transports
from googlecloudsdk.core.util import files


def Download(
    dest_path: str,
    file_res_name: str,
    file_name: str,
    allow_overwrite: bool,
    chunk_size: int,
    parallelism: int = 1,
) -> None:
  """Downloads a file to a local path."""
  client = requests.GetClient()

  # call expanduser so that `~` can be used to represent the home directory.
  dest_path = os.path.expanduser(dest_path)

  # Only move the file to the user specified path if overwrites are allowed.
  if os.path.exists(dest_path) and not allow_overwrite:
    log.error(f'File {dest_path} already exists.')
    sys.exit(1)

  m = requests.GetMessages()
  file_req = m.ArtifactregistryProjectsLocationsRepositoriesFilesGetRequest(
      name=file_res_name
  )
  file_res = client.projects_locations_repositories_files.Get(file_req)

  # Create the placeholder file so we can do parallel seek and write later.
  temp_dest_path = dest_path + '.tmp'
  try:
    with files.BinaryFileWriter(temp_dest_path) as f:
      f.truncate(file_res.sizeBytes)
  except FileExistsError:
    log.error(
        f'Temporary file {temp_dest_path} already exists (likely from a'
        ' previous failed download attempt). Please remove it and try again.'
    )
    sys.exit(1)

  # For some reason, there is no "v1" in the base URL even though it's supposed
  # to have the API version already in the client.
  download_url = f'{client.url}v1/{file_res_name}:download?alt=media'

  # Unlikely but when there are less bytes then the parallelism,
  # We fallback to 1 thread download.
  if file_res.sizeBytes < parallelism:
    parallelism = 1

  range_size = file_res.sizeBytes // parallelism
  ranges = []
  for i in range(0, parallelism):
    if i < parallelism - 1:
      ranges.append((i * range_size, (i + 1) * range_size - 1))
    else:
      ranges.append((i * range_size, file_res.sizeBytes - 1))

  with SharedProgressBar(
      label=f'Downloading {file_name}',
      parallelism=parallelism,
      total=file_res.sizeBytes,
  ) as progress_bar:
    with futures.ThreadPoolExecutor(max_workers=parallelism) as executor:
      fs = [
          executor.submit(
              _DownloadRange,
              i,
              temp_dest_path,
              download_url,
              start,
              end,
              chunk_size,
              progress_bar,
              client,
          )
          for i, (start, end) in enumerate(ranges)
      ]

      for future in futures.as_completed(fs):
        try:
          future.result()
        except Exception as exc:  # pylint: disable=broad-except
          raise exc

  if allow_overwrite and os.path.exists(dest_path):
    os.remove(dest_path)
  # Rename the temp file to the final destination path
  os.rename(temp_dest_path, dest_path)


def _DownloadRange(
    thread_index,
    temp_dest_path,
    download_url,
    start,
    end,
    chunk_size,
    progress_bar,
    client,
):
  """Downloads a range of bytes to the placeholder file."""

  ser_dict = {
      'auto_transfer': True,
      'total_size': end + 1,
      'progress': start,
      'url': download_url,
  }
  json_data = json.dumps(ser_dict)

  with files.BinaryFileWriter(temp_dest_path) as f:
    f.seek(start)
    d = transfer.Download.FromData(
        f,
        json_data,
        chunksize=chunk_size,
        client=client,
    )
    d.bytes_http = transports.GetApitoolsTransport(response_encoding=None)
    try:
      d.StreamMedia(
          callback=lambda _, dl: progress_bar.SetProgress(
              thread_index,
              dl.progress - start,
          )
      )
    finally:
      d.stream.close()


class SharedProgressBar(object):
  """A thread safe progress bar that allows adding increamental progress."""

  def __init__(self, parallelism, total, *args, **kwargs):
    self.completed_per_thread = [0] * parallelism
    self.total = total
    self._progress_bar = console_io.ProgressBar(*args, **kwargs)
    self._lock = threading.Lock()

  def __enter__(self):
    self._progress_bar.__enter__()
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self._progress_bar.__exit__(exc_type, exc_value, traceback)

  def SetProgress(self, thread_index, p):
    with self._lock:
      self.completed_per_thread[thread_index] = p
      self._progress_bar.SetProgress(
          sum(self.completed_per_thread) / self.total
      )
