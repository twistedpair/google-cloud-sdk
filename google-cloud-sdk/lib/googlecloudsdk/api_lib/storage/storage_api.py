# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Utilities for interacting with Google Cloud Storage.

This makes use of both the Cloud Storage API as well as the gsutil command-line
tool. We use the command-line tool for syncing the contents of buckets as well
as listing the contents. We use the API for checking ACLs.
"""

import cStringIO
import mimetypes
import os

from apitools.base.py import exceptions as api_exceptions
from apitools.base.py import list_pager
from apitools.base.py import transfer

from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


GSUTIL_BUCKET_REGEX = r'^gs://.*$'

LOG_OUTPUT_BEGIN = ' REMOTE BUILD OUTPUT '
LOG_OUTPUT_INCOMPLETE = ' (possibly incomplete) '
OUTPUT_LINE_CHAR = '-'
GCS_URL_PATTERN = (
    'https://www.googleapis.com/storage/v1/b/{bucket}/o/{obj}?alt=media')


class Error(Exception):
  """Base exception for storage API module."""


class UploadError(Error):
  """Error raised when there are problems uploading files."""


def _GetMimetype(local_path):
  mime_type, _ = mimetypes.guess_type(local_path)
  return mime_type or 'application/octet-stream'


def _GetFileSize(local_path):
  try:
    return os.path.getsize(local_path)
  except os.error:
    raise exceptions.BadFileException('[{0}] not found or not accessible'
                                      .format(local_path))


class StorageClient(object):
  """Client for Google Cloud Storage API."""

  def __init__(self, client=None, messages=None):
    self.client = client or storage_util.GetClient()
    self.messages = messages or storage_util.GetMessages()

  def Copy(self, src, dst):
    """Copy one GCS object to another.

    Args:
      src: Resource, the storage object resource to be copied from.
      dst: Resource, the storage object resource to be copied to.

    Returns:
      Object, the storage object that was copied to.
    """
    return self.client.objects.Copy(
        self.messages.StorageObjectsCopyRequest(
            sourceBucket=src.bucket,
            sourceObject=src.object,
            destinationBucket=dst.bucket,
            destinationObject=dst.object,
        ))

  def Rewrite(self, src, dst):
    """Rewrite one GCS object to another.

    This method has the same result as the Copy method, but can handle moving
    large objects that may potentially timeout a Copy request.

    Args:
      src: Resource, the storage object resource to be copied from.
      dst: Resource, the storage object resource to be copied to.

    Returns:
      Object, the storage object that was copied to.
    """
    rewrite_token = None
    while True:
      resp = self.client.objects.Rewrite(
          self.messages.StorageObjectsRewriteRequest(
              sourceBucket=src.bucket,
              sourceObject=src.object,
              destinationBucket=dst.bucket,
              destinationObject=dst.object,
              rewriteToken=rewrite_token,
          ))
      if resp.done:
        return resp.resource
      rewrite_token = resp.rewriteToken

  def GetObject(self, object_ref):
    """Gets an object from the given Cloud Storage bucket.

    Args:
      object_ref: storage_util.ObjectReference, The user-specified bucket to
        download from.

    Returns:
      Object: a StorageV1 Object message with details about the object.
    """
    return self.client.objects.Get(self.messages.StorageObjectsGetRequest(
        bucket=object_ref.bucket,
        object=object_ref.name))

  def CopyFileToGCS(self, bucket_ref, local_path, target_path):
    """Upload a file to the GCS results bucket using the storage API.

    Args:
      bucket_ref: storage_util.BucketReference, The user-specified bucket to
        download from.
      local_path: str, the path of the file to upload. File must be on the local
        filesystem.
      target_path: str, the path of the file on GCS.

    Returns:
      Object, the storage object that was copied to.

    Raises:
      BadFileException if the file upload is not successful.
    """
    file_size = _GetFileSize(local_path)
    src_obj = self.messages.Object(size=file_size)
    mime_type = _GetMimetype(local_path)

    upload = transfer.Upload.FromFile(local_path, mime_type=mime_type)
    insert_req = self.messages.StorageObjectsInsertRequest(
        bucket=bucket_ref.bucket,
        name=target_path,
        object=src_obj)

    log.info('Uploading [{local_file}] to [{gcs}]'.format(local_file=local_path,
                                                          gcs=target_path))
    try:
      response = self.client.objects.Insert(insert_req, upload=upload)
    except api_exceptions.HttpError as err:
      raise exceptions.BadFileException(
          'Could not copy [{local_file}] to [{gcs}]: {err}. Please retry.'
          .format(local_file=local_path, gcs=target_path, err=err))

    if response.size != file_size:
      log.debug('Response size: {0} bytes, but local file is {1} bytes.'.format(
          response.size, file_size))
      raise exceptions.BadFileException(
          'Cloud storage upload failure. Uploaded file does not match local '
          'file: {0}. Please retry.'.format(local_path))
    return response

  def CopyFileFromGCS(self, bucket_ref, object_path, local_path):
    """Download a file from the given Cloud Storage bucket.

    Args:
      bucket_ref: storage_util.BucketReference, The user-specified bucket to
        download from.
      object_path: str, the path of the file on GCS.
      local_path: str, the path of the file to download. Path must be on the
        local filesystem.

    Raises:
      BadFileException if the file download is not successful.
    """
    download = transfer.Download.FromFile(local_path)
    get_req = self.messages.StorageObjectsGetRequest(
        bucket=bucket_ref.bucket,
        object=object_path)

    log.info('Downloading [{gcs}] to [{local_file}]'.format(
        local_file=local_path, gcs=object_path))
    try:
      self.client.objects.Get(get_req, download=download)
      # Close the stream to release the file handle so we can check its contents
      download.stream.close()
      # When there's a download, Get() returns None so we Get() again to check
      # the file size.
      response = self.client.objects.Get(get_req)
    except api_exceptions.HttpError as err:
      raise exceptions.BadFileException(
          'Could not copy [{gcs}] to [{local_file}]: {err}. Please retry.'
          .format(local_file=local_path, gcs=object_path, err=err))

    file_size = _GetFileSize(local_path)
    if response.size != file_size:
      log.debug('Download size: {0} bytes, but expected size is {1} '
                'bytes.'.format(file_size, response.size))
      raise exceptions.BadFileException(
          'Cloud Storage download failure. Downloaded file [{0}] does not '
          'match Cloud Storage object. Please retry.'.format(local_path))

  def ReadObject(self, object_ref):
    """Read a file from the given Cloud Storage bucket.

    Args:
      object_ref: storage_util.ObjectReference, The object to read from.

    Raises:
      BadFileException if the file read is not successful.

    Returns:
      file-like object containing the data read.
    """
    data = cStringIO.StringIO()
    download = transfer.Download.FromStream(data)
    get_req = self.messages.StorageObjectsGetRequest(
        bucket=object_ref.bucket,
        object=object_ref.name)

    log.info('Reading [%s]', object_ref)
    try:
      self.client.objects.Get(get_req, download=download)
    except api_exceptions.HttpError as err:
      raise exceptions.BadFileException(
          'Could not read [{object_}]: {err}. Please retry.'.format(
              object_=object_ref, err=err))

    data.seek(0)
    return data

  def CreateBucketIfNotExists(self, bucket, project=None):
    """Create a bucket if it does not already exist.

    If it already exists and is owned by the creator, no problem.

    Args:
      bucket: str, The storage bucket to be created.
      project: str, The project to use for the API request. If None, current
          Cloud SDK project is used.

    Raises:
      api_exceptions.HttpError: If the bucket is owned by someone else
          or is otherwise not able to be created.
    """
    project = project or properties.VALUES.core.project.Get(required=True)
    try:
      self.client.buckets.Insert(
          self.messages.StorageBucketsInsertRequest(
              project=project,
              bucket=self.messages.Bucket(
                  name=bucket,
              )))
    except api_exceptions.HttpError as e:
      # It's ok if the error was 409, which means the resource already exists.
      if e.status_code != 409:
        raise
      # Make sure we have access to the bucket.  Storage returns a 409 whether
      # the already-existing bucket is owned by you or by someone else, so we
      # do a quick test to figure out which it was.
      self.client.buckets.Get(self.messages.StorageBucketsGetRequest(
          bucket=bucket,
      ))

  def ListBucket(self, bucket_ref):
    """Lists the contents of a cloud storage bucket.

    Args:
      bucket_ref: The reference to the bucket.
    Returns:
      A set of names of items.
    """
    request = self.messages.StorageObjectsListRequest(bucket=bucket_ref.bucket)
    items = set()
    try:
      # batch_size=None gives us the API default
      for item in list_pager.YieldFromList(self.client.objects, request,
                                           batch_size=None):
        items.add(item.name)
    except api_exceptions.HttpError as e:
      raise UploadError('Error uploading files: {e}'.format(e=e))
    return items

  def DeleteObject(self, bucket_ref, object_path):
    """Delete the specified object.

    Args:
      bucket_ref: storage_util.BucketReference to the bucket of the object
      object_path: path to the object within the bucket.
    """
    self.client.objects.Delete(self.messages.StorageObjectsDeleteRequest(
        bucket=bucket_ref.bucket,
        object=object_path))

  def DeleteBucket(self, bucket_ref):
    """Delete the specified bucket.

    Args:
      bucket_ref: storage_util.BucketReference to the bucket of the object
    """
    self.client.buckets.Delete(
        self.messages.StorageBucketsDeleteRequest(bucket=bucket_ref.bucket))


def Rsync(source_dir, dest_dir, exclude_pattern=None):
  """Copies files from the specified file system directory to a GCS bucket.

  Args:
    source_dir: The source directory for the rsync.
    dest_dir: The destination directory for the rsync.
    exclude_pattern: A string representation of a Python regular expression.
      If provided, this is passed as the '-x' argument for the rsync command.

  Returns:
    The exit code of the call to "gsutil rsync".
  """

  # -m Allows concurrent uploads
  # -c Causes gsutil to compute checksums when comparing files.
  # -R recursively copy all files
  # -x Ignore files using the specified pattern.
  command_arg_str = '-R -c '
  if exclude_pattern:
    command_arg_str += '-x \'{0}\' '.format(exclude_pattern)

  command_arg_str += ' '.join([source_dir, dest_dir])
  return storage_util.RunGsutilCommand('rsync', command_arg_str,
                                       run_concurrent=True)
