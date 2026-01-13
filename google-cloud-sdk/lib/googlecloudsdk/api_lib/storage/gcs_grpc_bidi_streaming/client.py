# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Client for Google Cloud Storage data plane API using gRPC bidi streaming."""

from __future__ import annotations

from typing import Any

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage.gcs_grpc import grpc_util
from googlecloudsdk.api_lib.storage.gcs_grpc import metadata_util
from googlecloudsdk.api_lib.storage.gcs_grpc import retry_util as grpc_retry_util
from googlecloudsdk.api_lib.storage.gcs_grpc_bidi_streaming import download
from googlecloudsdk.api_lib.storage.gcs_grpc_bidi_streaming import retry_util
from googlecloudsdk.api_lib.storage.gcs_grpc_bidi_streaming import upload
from googlecloudsdk.api_lib.storage.gcs_json import client as gcs_json_client
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.command_lib.storage import gzip_util
from googlecloudsdk.command_lib.storage.tasks.cp import download_util
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


def _log_transfer(
    transfer_type: str,
    source: Any,
    destination: Any,
    strategy: cloud_api.DownloadStrategy | cloud_api.UploadStrategy,
) -> None:
  """Logs transfer operation details."""
  log.debug(
      'Starting %s from %s to %s with strategy: %s.',
      transfer_type,
      source,
      destination,
      strategy,
  )


def _log_transfer_error(
    transfer_type: str, source: Any, destination: Any, error: Exception,
) -> None:
  """Logs transfer operation error."""
  log.debug(
      'Operation %s from %s to %s failed with error: %s.',
      transfer_type,
      source,
      destination,
      error,
  )


class GcsGrpcBidiStreamingClient(cloud_api.CloudApi):
  """Client for Google Cloud Storage data plane API using gRPC bidi streaming.

  Bidi streaming is supported for Zonal buckets currently so this
  client will only used for zonal buckets. This client will be merged with gRPC
  once the support is added for all the bucket types.

  TODO(b/437037554): Merge this client with gRPC client once the support is
  added for all bucket types.
  """

  capabilities = [
      cloud_api.Capability.APPENDABLE_UPLOAD,
      cloud_api.Capability.RESUMABLE_UPLOAD,
      cloud_api.Capability.SLICED_DOWNLOAD,
  ]

  def __init__(self):
    super(GcsGrpcBidiStreamingClient, self).__init__()
    self._gapic_client = None
    # The delegator is responsible for delegating the requests to the
    # appropriate client.
    self._delegator = gcs_json_client.JsonClient()

  def _get_gapic_client(self, redact_request_body_reason=None):
    # Not using @property because the side-effect is non-trivial and
    # might not be obvious. Someone might accidentally access the
    # property and end up creating the gapic client.
    # Creating the gapic client before "fork" will lead to a deadlock.
    if self._gapic_client is None:
      self._gapic_client = core_apis.GetGapicClientInstance(
          'storage',
          'v2',
          attempt_direct_path=properties.VALUES.storage.attempt_grpc_direct_path.GetBool(),
          redact_request_body_reason=redact_request_body_reason,
          channel_options={
              'grpc.http2.lookahead_bytes': (
                  properties.VALUES.grpc.http2_lookahead_bytes.GetInt()
              ),
              'grpc.http2.bdp_probe': (
                  properties.VALUES.grpc.enable_http2_bdp_probe.GetBool()
              ),
          },
      )
    return self._gapic_client

  def _get_source_path(self, source_resource):
    """Get source path from source_resource.

    Args:
      source_resource (FileObjectResource|None): Contains the
        source StorageUrl. Can be None if source is pure stream.

    Returns:
      (str|None) Source path.
    """
    if source_resource:
      return source_resource.storage_url.versionless_url_string

    return None

  @grpc_retry_util.grpc_default_retryer
  def get_grpc_bidi_object_metadata(
      self,
      bucket_name,
      object_name,
      source_resource=None,
      destination_resource=None,
      request_config=None,
      generation=None,
  ):
    """Get object metadata using gRPC bidi streaming API."""
    gapic_client = self._get_gapic_client()
    decryption_key = getattr(
        getattr(request_config, 'resource_args', None), 'decryption_key', None
    )
    read_request = gapic_client.types.BidiReadObjectRequest(
        read_object_spec=gapic_client.types.BidiReadObjectSpec(
            bucket=grpc_util.get_full_bucket_name(bucket_name),
            object_=object_name,
            generation=generation,
            common_object_request_params=grpc_util.get_encryption_request_params(
                gapic_client, decryption_key
            ),
        )
    )

    redirection_handler = retry_util.BidiRedirectedTokenErrorHandler(
        gapic_client, source_resource=source_resource,
        destination_resource=destination_resource,
    )
    bidi_read_object_rpc = (
        redirection_handler.start_bidi_rpc_with_retry_on_redirected_token_error(
            read_request
        )
    )
    try:
      response = bidi_read_object_rpc.recv()
    finally:
      bidi_read_object_rpc.close()
    return metadata_util.get_object_resource_from_grpc_object(response.metadata)

  def get_object_metadata(
      self,
      bucket_name,
      object_name,
      request_config=None,
      generation=None,
      fields_scope=None,
      soft_deleted=False,
  ):
    """See super class."""
    object_metadata = self._delegator.get_object_metadata(
        bucket_name=bucket_name,
        object_name=object_name,
        request_config=request_config,
        generation=generation,
        fields_scope=fields_scope,
        soft_deleted=soft_deleted,
    )
    return object_metadata

  def download_object(
      self,
      cloud_resource,
      download_stream,
      request_config,
      digesters=None,
      do_not_decompress=False,
      download_strategy=cloud_api.DownloadStrategy.RESUMABLE,
      progress_callback=None,
      start_byte=0,
      end_byte=None,
  ):
    """See super class."""
    _log_transfer(
        'download',
        cloud_resource.storage_url.resource_name,
        download_stream,
        download_strategy,
    )
    if download_util.return_and_report_if_nothing_to_download(
        cloud_resource, progress_callback
    ):
      return None

    decryption_key = None
    if request_config.resource_args:
      decryption_key = getattr(
          request_config.resource_args, 'decryption_key', None
      )

    downloader = download.BidiGrpcDownload(
        gapic_client=self._get_gapic_client(),
        cloud_resource=cloud_resource,
        download_stream=download_stream,
        start_byte=start_byte,
        end_byte=end_byte,
        digesters=digesters,
        progress_callback=progress_callback,
        download_strategy=download_strategy,
        decryption_key=decryption_key,
    )
    try:
      downloader.run()
    except Exception as e:
      _log_transfer_error(
          'download',
          cloud_resource.storage_url.resource_name,
          download_stream,
          e,
      )
      raise
    # Unlike JSON, the response message for gRPC does not hold any
    # content-encoding information. Hence, we do not have to return the
    # server encoding here.
    return None

  def upload_object(
      self,
      source_stream,
      destination_resource,
      request_config,
      posix_to_set=None,
      serialization_data=None,
      source_resource=None,
      tracker_callback=None,
      upload_strategy=cloud_api.UploadStrategy.SIMPLE,
  ):
    """See super class."""
    _log_transfer(
        'upload',
        source_stream,
        destination_resource,
        upload_strategy,
    )
    client = self._get_gapic_client(
        redact_request_body_reason=(
            'Object data is not displayed to keep the log output clean.'
            ' Set log_http_show_request_body property to True to print the'
            ' body of this request.'
        )
    )

    source_path = self._get_source_path(source_resource)
    should_gzip_in_flight = gzip_util.should_gzip_in_flight(
        request_config.gzip_settings, source_path
    )

    if should_gzip_in_flight:
      raise core_exceptions.InternalError(
          'Gzip transport encoding is not supported with Zonal Buckets.'
      )

    if upload_strategy == cloud_api.UploadStrategy.SIMPLE:
      uploader = upload.SimpleUpload(
          client=client,
          source_stream=source_stream,
          destination_resource=destination_resource,
          request_config=request_config,
          source_resource=source_resource,
          delegator=self._delegator,
          posix_to_set=posix_to_set,
      )
    elif upload_strategy == cloud_api.UploadStrategy.RESUMABLE:
      uploader = upload.ResumableUpload(
          client=client,
          source_stream=source_stream,
          destination_resource=destination_resource,
          request_config=request_config,
          source_resource=source_resource,
          delegator=self._delegator,
          posix_to_set=posix_to_set,
      )
    else:
      raise core_exceptions.InternalError(
          'Only simple/resumable upload strategy is supported for Zonal Buckets'
          ' with bidi streaming API.'
      )
    try:
      return uploader.run()
    except Exception as e:
      _log_transfer_error(
          'upload', source_stream, destination_resource, e,
      )
      raise
