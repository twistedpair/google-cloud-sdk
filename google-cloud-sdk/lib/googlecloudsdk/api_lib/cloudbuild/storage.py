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

"""Utilities for interacting with Google Cloud Storage.

"""

import os.path

from apitools.base.py import exceptions as api_exceptions
from apitools.base.py import transfer

from googlecloudsdk.core import apis as core_apis


class Client(object):
  """Client wraps cloudbuild operations on the storage API.

  """

  def __init__(self, project):
    self.project = project
    self.client = core_apis.GetClientInstance('storage', 'v1')
    self.messages = core_apis.GetMessagesModule('storage', 'v1')

  def CreateBucketIfNotExists(self, bucket):
    """Create a bucket if it does not already exist.

    If it already exists and is owned by the creator, no problem.

    Args:
      bucket: str, The storage bucket to be created.

    Raises:
      api_exceptions.HttpError: If the bucket is owned by someone else
          or is otherwise not able to be created.
    """
    try:
      self.client.buckets.Insert(
          self.messages.StorageBucketsInsertRequest(
              project=self.project,
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

  def Upload(self, local_file, dst, mime_type=None):
    """Upload a local file into GCS.

    Args:
      local_file: str, The local file to be uploaded.
      dst: Resource, The storage object resource to be copied to.
      mime_type: str, The MIME type of this file.

    Returns:
      Object, the storage object that was copied to.
    """
    return self.client.objects.Insert(
        self.messages.StorageObjectsInsertRequest(
            bucket=dst.bucket,
            name=dst.object,
            object=self.messages.Object(
                size=os.path.getsize(local_file),
            ),
        ),
        upload=transfer.Upload.FromFile(
            local_file,
            mime_type=mime_type,
        ),
    )
