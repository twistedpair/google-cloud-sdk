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
>>> UploadFiles(upload_tasks, num_processes=1, threads_per_process=16)

This will block until all files are uploaded, using 16 threads (but just the
current process). Afterwards, there will be objects at
'gs://my-bucket/path/to/remote1.txt' and 'gs://my-bucket/remote2.txt'.

>>> delete_tasks = [
...     ObjectDeleteTask('gs://my-bucket', 'path/to/remote1.txt'),
...     ObjectDeleteTask('gs://my-bucket', '/remote2.txt')
... ]
>>> DeleteObjects(delete_tasks, num_processes=1, threads_per_process=16)

This removes the objects uploaded in the last code snippet.
"""
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.core import log
from googlecloudsdk.core.util import parallel
from googlecloudsdk.core.util import retry


# These default values have been chosen after lots of experimentation.
DEFAULT_NUM_THREADS = 16
DEFAULT_NUM_PROCESSES = 1


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
    return (u'FileUploadTask('
            u'local_path={task.local_path!r}, '
            u'bucket_url={task.bucket_url!r}, '
            u'remote_path={task.remote_path!r})').format(task=self)

  def __hash__(self):
    return hash((self.local_path, self.bucket_url, self.remote_path))


def _UploadFile(file_upload_task):
  """Complete one FileUploadTask (safe to run in parallel)."""
  storage_client = storage_api.StorageClient()
  bucket_ref = storage_util.BucketReference.FromBucketUrl(
      file_upload_task.bucket_url)

  local_path = file_upload_task.local_path
  retry.Retryer(max_retrials=3).RetryOnException(
      storage_client.CopyFileToGCS,
      args=(bucket_ref, local_path, file_upload_task.remote_path))


def UploadFiles(files_to_upload, num_processes=DEFAULT_NUM_PROCESSES,
                threads_per_process=DEFAULT_NUM_THREADS):
  """Upload the given files to the given Cloud Storage URLs.

  Uses the appropriate parallelism (multi-process, multi-thread, both, or
  synchronous).

  Args:
    files_to_upload: list of FileUploadTask
    num_processes: int (optional), the number of processes to use
    threads_per_process: int (optional), the number of threads to use per
        process.
  """
  log.debug(u'Uploading:\n' + u'\n'.join(map(str, files_to_upload)))
  log.debug(u'Using [%d] processes, [%d] threads per process', num_processes,
            threads_per_process)

  with parallel.GetPool(num_processes, threads_per_process) as pool:
    pool.Map(_UploadFile, files_to_upload)


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
    return (u'ObjectDeleteTask('
            u'bucket_url={task.bucket_url!r}, '
            u'remote_path={task.remote_path!r})').format(task=self)

  def __hash__(self):
    return hash((self.bucket_url, self.remote_path))


def _DeleteObject(object_delete_task):
  """Complete one ObjectDeleteTask (safe to run in parallel)."""
  storage_client = storage_api.StorageClient()
  bucket_ref = storage_util.BucketReference.FromBucketUrl(
      object_delete_task.bucket_url)

  retry.Retryer(max_retrials=3).RetryOnException(
      storage_client.DeleteObject,
      args=(bucket_ref, object_delete_task.remote_path))


def DeleteObjects(objects_to_delete, num_processes=DEFAULT_NUM_PROCESSES,
                  threads_per_process=DEFAULT_NUM_THREADS):
  """Delete the given Cloud Storage objects.

  Uses the appropriate parallelism (multi-process, multi-thread, both, or
  synchronous).

  Args:
    objects_to_delete: list of ObjectDeleteTask
    num_processes: int (optional), the number of processes to use
    threads_per_process: int (optional), the number of threads to use per
        process.
  """
  log.debug(u'Deleting:\n' + u'\n'.join(map(str, objects_to_delete)))
  log.debug(u'Using [%d] processes, [%d] threads per process', num_processes,
            threads_per_process)

  with parallel.GetPool(num_processes, threads_per_process) as pool:
    pool.Map(_DeleteObject, objects_to_delete)
