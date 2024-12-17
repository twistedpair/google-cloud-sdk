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
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.command_lib.builds import staging_bucket_util
from googlecloudsdk.command_lib.run.sourcedeploys import types
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import times


_GCS_PREFIX = 'gs://'


def Upload(source, region, resource_ref, source_bucket=None):
  """Uploads a source to a staging bucket.

  Args:
    source: Location of the source to be uploaded. Can be local path or a
      reference to a GCS object.
    region: The region to upload to.
    resource_ref: The Cloud Run service resource reference.
    source_bucket: The source bucket to upload to, if not None.

  Returns:
    storage_v1_messages.Object, The written GCS object.
  """
  gcs_client = storage_api.StorageClient()

  bucket_name = _GetOrCreateBucket(gcs_client, region, source_bucket)
  object_name = _GetObject(source, resource_ref)
  log.debug(f'Uploading source to {_GCS_PREFIX}{bucket_name}/{object_name}')

  object_ref = resources.REGISTRY.Create(
      collection='storage.objects',
      bucket=bucket_name,
      object=object_name,
  )
  return staging_bucket_util.Upload(
      source, object_ref, gcs_client, ignore_file=None
  )


def GetGcsObject(source: str):
  """Retrieves the GCS object corresponding to the source location string.

  Args:
    source: The source location string in the format `gs://<bucket>/<object>`.

  Returns:
    storage_v1_messages.Object, The GCS object.
  """
  object_ref = storage_util.ObjectReference.FromUrl(source)
  return storage_api.StorageClient().GetObject(object_ref)


def IsGcsObject(source: str) -> bool:
  """Returns true if the source is located remotely in a GCS object."""
  return (source or '').startswith(_GCS_PREFIX)


def _GetOrCreateBucket(gcs_client, region, bucket_name=None):
  """Gets or Creates bucket used to store sources."""
  bucket = bucket_name or _GetDefaultBucketName(region)

  cors = [
      storage_util.GetMessages().Bucket.CorsValueListEntry(
          method=['GET'],
          origin=[
              'https://*.cloud.google.com',
              'https://*.corp.' + 'google.com',  # To bypass sensitive words
              'https://*.corp.' + 'google.com:*',  # To bypass sensitive words
              'https://*.cloud.google',
              'https://*.byoid.goog',
          ],
      )
  ]

  # This will throw an error if we're using the default bucket but it already
  # exists in a different project, then it could belong to a malicious attacker.
  gcs_client.CreateBucketIfNotExists(
      bucket,
      location=region,
      check_ownership=True,
      cors=cors,
      enable_uniform_level_access=True,
  )
  return bucket


def _GetObject(source, resource_ref):
  """Gets the object name for a source to be uploaded."""
  suffix = '.zip'
  if source.startswith(_GCS_PREFIX) or os.path.isfile(source):
    _, suffix = os.path.splitext(source)

  # TODO(b/319452047) update object naming
  file_name = '{stamp}-{uuid}{suffix}'.format(
      stamp=times.GetTimeStampFromDateTime(times.Now()),
      uuid=uuid.uuid4().hex,
      suffix=suffix,
  )

  object_path = (
      f'{types.GetKind(resource_ref)}s/{resource_ref.Name()}/{file_name}'
  )
  return object_path


def _GetDefaultBucketName(region: str) -> str:
  """Returns the default regional bucket name.

  Args:
    region: Cloud Run region.

  Returns:
    GCS bucket name.
  """
  safe_project = (
      properties.VALUES.core.project.Get(required=True)
      .replace(':', '_')
      .replace('.', '_')
      # The string 'google' is not allowed in bucket names.
      .replace('google', 'elgoog')
  )
  return (
      f'run-sources-{safe_project}-{region}'
      if region is not None
      else f'run-sources-{safe_project}'
  )
