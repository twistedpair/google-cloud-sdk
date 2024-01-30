# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Sources for Cloud Run Functions."""
import os
import uuid

from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.command_lib.builds import staging_bucket_util
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import times


def Upload(source):
  """Uploads a source to a staging bucket."""
  gcs_client = storage_api.StorageClient()

  bucket_name = _GetOrCreateBucket(gcs_client)
  object_name = _GetObject(source)
  log.debug(f'Uploading source to gs://{bucket_name}/{object_name}')

  object_ref = resources.REGISTRY.Create(
      collection='storage.objects',
      bucket=bucket_name,
      object=object_name,
  )
  return staging_bucket_util.Upload(
      source, object_ref, gcs_client, ignore_file=None
  )


def _GetOrCreateBucket(gcs_client):
  """Gets or Creates bucket used to store sources."""
  # TODO(b/319451996) Update bucket naming
  bucket = staging_bucket_util.GetDefaultStagingBucket()

  # TODO(b/319451996) Set CORs config
  # this will throw an error if the bucket found isn't in the same project
  gcs_client.CreateBucketIfNotExists(
      bucket,
      location=None,  # TODO(b/319451996) Create regional bucket
      check_ownership=True,
  )
  return bucket


def _GetObject(source):
  """Gets the object name for a source to be uploaded."""
  # TODO(b/319452047) switch to .zip
  suffix = '.tgz'
  if source.startswith('gs://') or os.path.isfile(source):
    _, suffix = os.path.splitext(source)

  # TODO(b/319452047) update object naming
  file_name = '{stamp}-{uuid}{suffix}'.format(
      stamp=times.GetTimeStampFromDateTime(times.Now()),
      uuid=uuid.uuid4().hex,
      suffix=suffix,
  )

  # TODO(b/319452047) update object path
  object_path = 'source/' + file_name
  return object_path
