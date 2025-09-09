# -*- coding: utf-8 -*- #
# Copyright 2020 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Returns correct API client instance for user command."""

# TODO(b/275749579): Rename this module.

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import threading

from googlecloudsdk.api_lib.storage import errors as cloud_api_errors
from googlecloudsdk.api_lib.storage.gcs_grpc import client as gcs_grpc_client
from googlecloudsdk.api_lib.storage.gcs_json import client as gcs_json_client
from googlecloudsdk.api_lib.storage.gcs_xml import client as gcs_xml_client
from googlecloudsdk.api_lib.storage.s3_xml import client as s3_xml_client
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.core import log
from googlecloudsdk.core import properties

_INVALID_PROVIDER_PREFIX_MESSAGE = (
    'Invalid provider. Valid provider prefixes: {}'.format(
        ', '.join(
            sorted([scheme.value for scheme in storage_url.VALID_CLOUD_SCHEMES])
        )
    )
)

# Module variable for holding one API instance per thread per (provider + bucket
# type).
_cloud_api_thread_local_storage = None


def _is_gcs_zonal_bucket(provider, bucket_name: str) -> bool:
  """Returns true if the given bucket is a GCS zonal bucket."""
  if not bucket_name or provider != storage_url.ProviderPrefix.GCS:
    return False
  api_client = gcs_json_client.JsonClient()
  try:
    storage_layout = api_client.get_storage_layout(bucket_name)
    return storage_layout.locationType == 'zone'
  except cloud_api_errors.CloudApiError as e:
    status_code = getattr(e, 'status_code', None)
    if status_code in (401, 403, 404):
      log.debug(
          'Failed to get storage layout for bucket %s: %s', bucket_name, e
      )
      # If the bucket does not exist, we can assume it is not a zonal bucket.
      # If the user does not have permission to check the bucket type, we will
      # default to not using a zonal client.
      return False
    raise


def _get_api_class(provider, is_zonal_bucket):
  """Returns a CloudApi subclass corresponding to the requested provider.

  Args:
    provider (storage_url.ProviderPrefix): Cloud provider prefix.
    is_zonal_bucket (bool): Whether the bucket is a zonal bucket.

  Returns:
    An appropriate CloudApi subclass.

  Raises:
    Error: If provider is not a cloud scheme in storage_url.ProviderPrefix.
  """
  if provider == storage_url.ProviderPrefix.GCS:

    if is_zonal_bucket:
      log.debug('Using gRPC Bidi Streaming client for zonal bucket.')
      # pylint: disable=g-import-not-at-top
      from googlecloudsdk.api_lib.storage.gcs_grpc_bidi_streaming import client as grpc_bidi_streaming_client

      return grpc_bidi_streaming_client.GcsGrpcBidiStreamingClient

    # Enabling gRPC basis both properties for the time being.
    # StoragePreferredAPI property will be removed as part of
    # adding gRPC support at the end before releasing.
    # TODO(b/324352239)
    if properties.VALUES.storage.use_grpc_if_available.GetBool() or (
        properties.VALUES.storage.preferred_api.Get()
        == properties.StoragePreferredApi.GRPC_WITH_JSON_FALLBACK.value
    ):
      log.debug('Using gRPC client with JSON Fallback.')
      return gcs_grpc_client.GrpcClientWithJsonFallback
    if (
        properties.VALUES.storage.gs_xml_access_key_id.Get()
        and properties.VALUES.storage.gs_xml_secret_access_key.Get()
    ):
      return gcs_xml_client.XmlClient
    return gcs_json_client.JsonClient
  elif provider == storage_url.ProviderPrefix.S3:
    # TODO(b/275749579): Change this after the refactor is done.
    return s3_xml_client.S3XmlClient
  else:
    raise errors.Error(_INVALID_PROVIDER_PREFIX_MESSAGE)


def _get_thread_local_storage_key(provider, is_zonal_bucket):
  """Returns the thread local storage key for the given provider and bucket."""
  if is_zonal_bucket:
    return f'{provider.value}_zonal'
  return f'{provider.value}'


def get_api(provider, bucket_name=None):
  """Returns thread local API instance based on provider and bucket(if available).

  Uses thread local storage to make sure only one instance of an API exists
  per thread per provider + bucket type.

  Args:
    provider (storage_url.ProviderPrefix): Cloud provider prefix.
    bucket_name (str): Name of the bucket. If available, the API client will be
      chosen based on the bucket type as well. Currently only supported for GCS.

  Returns:
    CloudApi client object for the arguments.

  Raises:
    Error: If provider is not a cloud scheme in storage_url.ProviderPrefix.
  """
  global _cloud_api_thread_local_storage

  # Bucket name is used to determine if the bucket is a zonal bucket. A single
  # zonal bucket client(gRPC Bidi Streaming) can be shared across multiple
  # zonal buckets. Hence, We only use whether a bucket is zonal or not to
  # determine the thread local storage key.
  is_zonal_bucket = _is_gcs_zonal_bucket(provider, bucket_name)

  if properties.VALUES.storage.use_threading_local.GetBool():
    if not _cloud_api_thread_local_storage:
      _cloud_api_thread_local_storage = threading.local()

    api_client = getattr(
        _cloud_api_thread_local_storage,
        _get_thread_local_storage_key(provider, is_zonal_bucket),
        None,
    )
    if api_client:
      return api_client

  api_class = _get_api_class(provider, is_zonal_bucket)
  api_client = api_class()

  if properties.VALUES.storage.use_threading_local.GetBool():
    setattr(
        _cloud_api_thread_local_storage,
        _get_thread_local_storage_key(provider, is_zonal_bucket),
        api_client,
    )

  return api_client


def get_capabilities(provider, bucket_name=None):
  """Gets the capabilities of a cloud provider.

  Args:
    provider (storage_url.ProviderPrefix): Cloud provider prefix.
    bucket_name (str): Name of the bucket. If available, the API client will be
      chosen based on the bucket type as well. Currently only supported for GCS.

  Returns:
    The CloudApi.capabilities attribute for the requested provider.

  Raises:
    Error: If provider is not a cloud scheme in storage_url.ProviderPrefix.
  """
  api_class = _get_api_class(
      provider, _is_gcs_zonal_bucket(provider, bucket_name)
  )
  return api_class.capabilities
