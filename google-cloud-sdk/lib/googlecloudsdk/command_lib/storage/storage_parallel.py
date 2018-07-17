# -*- coding: utf-8 -*- #
# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Utilities for parallelizing Cloud Storage file operations.

Example usage (for simplicity, use absolute *nix-style paths; in practice you'll
want to use os.path.join and friends):

>>> upload_tasks = [
...     FileUploadTask('/tmp/file1.txt', 'gs://my-bucket',
...                    'path/to/remote1.txt'),
...     FileUploadTask('/tmp/file2.txt', 'gs://my-bucket', '/remote2.txt')
... ]
>>> UploadFiles(upload_tasks, num_threads=16)

This will block until all files are uploaded, using 16 threads (but just the
current process). Afterwards, there will be objects at
'gs://my-bucket/path/to/remote1.txt' and 'gs://my-bucket/remote2.txt'.

>>> delete_tasks = [
...     ObjectDeleteTask('gs://my-bucket', 'path/to/remote1.txt'),
...     ObjectDeleteTask('gs://my-bucket', '/remote2.txt')
... ]
>>> DeleteObjects(delete_tasks, num_threads=16)

This removes the objects uploaded in the last code snippet.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools

from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import parallel
from googlecloudsdk.core.util import retry
from googlecloudsdk.core.util import text
from six.moves import zip


# This default value has been chosen after lots of experimentation.
DEFAULT_NUM_THREADS = 16


class FileUploadTask(object):
  """Self-contained representation of a file to upload and its destination.

  The reason not to combine bucket_url and remote_path is that a common use case
  is to upload many files to the same bucket; this saves callers the hassle of
  concatenating themselves while still allowing parallelizing uploads to
  multiple buckets.

  Attributes:
    local_path: str, the path to the file to upload on the local system
    bucket_url: str, the URL of the destination Cloud Storage bucket (e.g.
        'gs://my-bucket')
    remote_path: str, the path to the file destination within its bucket
  """

  def __init__(self, local_path, bucket_url, remote_path):
    self.local_path = local_path
    self.bucket_url = bucket_url
    self.remote_path = remote_path

  def __repr__(self):
    return ('FileUploadTask('
            'local_path={task.local_path!r}, '
            'bucket_url={task.bucket_url!r}, '
            'remote_path={task.remote_path!r})').format(task=self)

  def __hash__(self):
    return hash((self.local_path, self.bucket_url, self.remote_path))


def _UploadFile(value):
  """Complete one FileUploadTask (safe to run in parallel)."""
  file_upload_task, callback = value
  storage_client = storage_api.StorageClient()
  bucket_ref = storage_util.BucketReference.FromBucketUrl(
      file_upload_task.bucket_url)

  local_path = file_upload_task.local_path
  retry.Retryer(max_retrials=3).RetryOnException(
      storage_client.CopyFileToGCS,
      args=(bucket_ref, local_path, file_upload_task.remote_path))
  if callback:
    callback()


def _DoParallelOperation(num_threads, tasks, method, label, show_progress_bar):
  """Perform the given storage operation in parallel.

  Factors out common work: logging, setting up parallelism, managing a progress
  bar (if necessary).

  Args:
    num_threads: int, the number of threads to use
    tasks: list of arguments to be passed to method, one at a time (each zipped
      up in a tuple with a callback)
    method: a function that takes in a single-argument: a tuple of a task to do
      and a zero-argument callback to be done on completion of the task.
    label: str, the label for the progress bar (if used).
    show_progress_bar: bool, whether to show a progress bar during the
      operation.
  """
  log.debug(label)
  log.debug('Using [%d] threads', num_threads)

  pool = parallel.GetPool(num_threads)
  if show_progress_bar:
    progress_bar = console_io.TickableProgressBar(len(tasks), label)
    callback = progress_bar.Tick
  else:
    progress_bar = console_io.NoOpProgressBar()
    callback = None
  with progress_bar, pool:
    pool.Map(method, list(zip(tasks, itertools.cycle((callback,)))))


def UploadFiles(files_to_upload, num_threads=DEFAULT_NUM_THREADS,
                show_progress_bar=False):
  """Upload the given files to the given Cloud Storage URLs.

  Uses the appropriate parallelism (multi-process, multi-thread, both, or
  synchronous).

  Args:
    files_to_upload: list of FileUploadTask
    num_threads: int (optional), the number of threads to use.
    show_progress_bar: bool. If true, show a progress bar to the users when
      uploading files.
  """
  num_files = len(files_to_upload)
  label = 'Uploading {} {} to Google Cloud Storage'.format(
      num_files, text.Pluralize(num_files, 'file'))
  _DoParallelOperation(num_threads, files_to_upload, _UploadFile, label,
                       show_progress_bar)


class ObjectDeleteTask(object):
  """Self-contained representation of an object to delete.

  The reason not to combine bucket_url and remote_path is that a common use case
  is to delete many objects in the same bucket; this saves callers the hassle of
  concatenating themselves while still allowing parallelizing deletions in
  multiple buckets.

  Attributes:
    bucket_url: str, the URL of the destination Cloud Storage bucket (e.g.
        'gs://my-bucket')
    remote_path: str, the path to the file destination within its bucket (
  """

  def __init__(self, bucket_url, remote_path):
    self.bucket_url = bucket_url
    self.remote_path = remote_path

  def __repr__(self):
    return ('ObjectDeleteTask('
            'bucket_url={task.bucket_url!r}, '
            'remote_path={task.remote_path!r})').format(task=self)

  def __hash__(self):
    return hash((self.bucket_url, self.remote_path))


def _DeleteObject(value):
  """Complete one ObjectDeleteTask (safe to run in parallel)."""
  object_delete_task, callback = value
  storage_client = storage_api.StorageClient()
  bucket_ref = storage_util.BucketReference.FromBucketUrl(
      object_delete_task.bucket_url)

  retry.Retryer(max_retrials=3).RetryOnException(
      storage_client.DeleteObject,
      args=(bucket_ref, object_delete_task.remote_path))
  if callback:
    callback()


def DeleteObjects(objects_to_delete, num_threads=DEFAULT_NUM_THREADS,
                  show_progress_bar=False):
  """Delete the given Cloud Storage objects.

  Uses the appropriate parallelism (multi-process, multi-thread, both, or
  synchronous).

  Args:
    objects_to_delete: list of ObjectDeleteTask
    num_threads: int (optional), the number of threads to use.
    show_progress_bar: bool. If true, show a progress bar to the users when
      deleting files.
  """
  num_objects = len(objects_to_delete)
  label = 'Deleting {} {} from Google Cloud Storage'.format(
      num_objects, text.Pluralize(num_objects, 'object'))
  _DoParallelOperation(num_threads, objects_to_delete, _DeleteObject,
                       label, show_progress_bar)
