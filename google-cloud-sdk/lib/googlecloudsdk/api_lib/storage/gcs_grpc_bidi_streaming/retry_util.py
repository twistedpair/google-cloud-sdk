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
"""Retry wrapper for resumable BiDi downloads."""

from __future__ import absolute_import
from __future__ import annotations
from __future__ import division
from __future__ import unicode_literals

import re
from typing import Any

from googlecloudsdk.api_lib.storage import errors as cloud_errors
from googlecloudsdk.api_lib.storage import retry_util as storage_retry_util
from googlecloudsdk.api_lib.storage.gcs_grpc import grpc_util
from googlecloudsdk.api_lib.storage.gcs_grpc import metadata_util
from googlecloudsdk.api_lib.storage.gcs_grpc import retry_util as grpc_retry_util
from googlecloudsdk.api_lib.storage.gcs_grpc_bidi_streaming import download
from googlecloudsdk.api_lib.storage.gcs_grpc_bidi_streaming import storage_bidi_rpc
from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.core import log
from googlecloudsdk.core.util import retry

_MAX_RETRIES_ON_REDIRECTED_TOKEN_ERROR = 4


class BidiUploadStreamClosedError(cloud_errors.RetryableApiError):
  """Exception raised when the BiDi upload stream is unexpectedly closed."""


def _should_retry_bidi(exc_type, exc_value, exc_traceback, state=None):
  """Returns True if the BiDi download error is retryable."""
  if isinstance(exc_value, BrokenPipeError):
    return False
  return isinstance(
      exc_value, download.BidiDownloadIncompleteError
  ) or grpc_retry_util.is_retriable(exc_type, exc_value, exc_traceback, state)


def run_with_retries(
    process_chunk_func,
    gapic_client,
    cloud_resource,
    download_stream,
    digesters,
    progress_callback,
    start_byte,
    end_byte,
    download_strategy,
    decryption_key,
    target_size,
    redirection_handler,
):
  """Executes download with retries, resuming from processed_bytes."""
  bidi_downloader = download.BidiDownloader(
      process_chunk_func,
      gapic_client,
      cloud_resource,
      download_stream,
      digesters,
      progress_callback,
      start_byte,
      end_byte,
      download_strategy,
      decryption_key,
      target_size,
      redirection_handler,
  )

  try:
    storage_retry_util.retryer(
        target=bidi_downloader.download_chunk,
        should_retry_if=_should_retry_bidi,
    )
  except (download.BidiDownloadIncompleteError, retry.MaxRetrialsException):
    # Retries exhausted.
    pass
  return (
      bidi_downloader.processed_bytes,
      bidi_downloader.destination_pipe_is_broken,
  )


class BidiRedirectedTokenErrorHandler:
  """Handles retries on redirected token errors for BiDi RPCs.

  This class is NOT thread-safe due to in-place modification of the
  `initial_request` object in `_get_bidi_rpc_with_routing_token`.

  A new instance of this handler should be used for independent data transfer
  operation (e.g., each new download or upload). However, the same
  class(routing_token) can be re-used for uploading-downloading the same object.
  The API discards stale tokens, ensuring that an incorrect token from a
  previous or different stream does not result in an incorrect behavior.

  Once created, the routing token remains valid for a few minutes only.

  Attributes:
    _client: The GAPIC client.
    _destination_resource: Metadata for the destination object.
    _routing_token: The routing token to be used for the BiDi RPC.
  """

  _UPLOADS_TYPE_URL = (
      # gcloud-disable-gdu-domain
      'type.googleapis.com/google.storage.v2.BidiWriteObjectRedirectedError'
  )
  _DOWNLOADS_TYPE_URL = (
      # gcloud-disable-gdu-domain
      'type.googleapis.com/google.storage.v2.BidiReadObjectRedirectedError'
  )

  def __init__(
      self,
      client,
      *,
      source_resource: Any | None = None,
      destination_resource: (
          resource_reference.ObjectResource | resource_reference.UnknownResource
      ) | None = None,
  ):
    """Initializes the BidiRedirectedTokenErrorHandler.

    Args:
      client (gapic_clients.storage_v2.services.storage.client.StorageClient):
        The GAPIC client.
      source_resource: The source resource of the data transfer.
      destination_resource: The destination resource of the data transfer.

    """
    self._client = client
    self._source_resource = source_resource
    self._destination_resource = destination_resource
    if (
        destination_resource is not None and
        hasattr(destination_resource, 'storage_url')
        and destination_resource.storage_url.bucket_name
    ):
      self._cloud_resource = destination_resource
    else:
      self._cloud_resource = source_resource
    self._routing_token = None

  def __repr__(self) -> str:
    return (
        f'{self.__class__.__name__}('
        f'client={self._client!r}, '
        f'source_resource={self._source_resource!r}, '
        f'destination_resource={self._destination_resource!r}, '
        f'cloud_resource={self._cloud_resource!r}, '
        f'routing_token={self._routing_token!r})'
    )

  def _get_bidi_rpc_with_routing_token(self, initial_request):
    """Gets the bidi rpc with routing token.

    Incase of redirected token error, the token received is to be provided in
    the header `x-goog-request-params`, with key `routing_token` and the token
    string verbatim as the value.

    We must also populate the initial request with the token, for uploads and
    downloads. Note that this method modifies `initial_request` in place.

    Args:
      initial_request: (gapic_clients.storage_v2.types.BidiWriteObjectRequest
        | gapic_clients.storage_v2.types.BidiReadObjectRequest) The initial
        request to be used for the bidi RPC.

    Returns:
      gapic_util.BidiRpc: The bidi RPC with metadata and initial request
        updated.
    """
    if isinstance(initial_request, self._client.types.BidiWriteObjectRequest):
      rpc_method = self._client.storage.bidi_write_object
      if initial_request.append_object_spec:
        initial_request.append_object_spec.routing_token = self._routing_token
    elif isinstance(initial_request, self._client.types.BidiReadObjectRequest):
      rpc_method = self._client.storage.bidi_read_object
      initial_request.read_object_spec.routing_token = self._routing_token
    else:
      raise ValueError(
          'Unsupported initial request type: %s' % type(initial_request)
      )

    return storage_bidi_rpc.StorageBidiRpc(
        self._client,
        rpc_method,
        initial_request=initial_request,
        metadata=metadata_util.get_bucket_name_routing_header(
            grpc_util.get_full_bucket_name(
                self._cloud_resource.storage_url.bucket_name
            ),
            routing_token=self._routing_token,
        ),
        source_resource=self._source_resource,
        destination_resource=self._destination_resource,
    )

  def start_bidi_rpc_with_retry_on_redirected_token_error(
      self, initial_request
  ):
    """Starts the bidi rpc with retry on redirected token error."""
    for retry_count in range(_MAX_RETRIES_ON_REDIRECTED_TOKEN_ERROR):
      bidi_rpc = self._get_bidi_rpc_with_routing_token(initial_request)
      try:
        bidi_rpc.open()
        return bidi_rpc
      except grpc_retry_util.exceptions.Aborted as e:
        bidi_rpc.close()
        if retry_count == _MAX_RETRIES_ON_REDIRECTED_TOKEN_ERROR - 1:
          # If we have exhausted all retries, re-raise the error.
          raise
        trailing_metadata = e.response.trailing_metadata()
        for key, value in trailing_metadata:
          if key == 'grpc-status-details-bin':
            status_details = value
            break
        else:
          raise
        from google.rpc import status_pb2  # pylint: disable=g-import-not-at-top

        status_msg = status_pb2.Status()
        status_msg.ParseFromString(status_details)
        any_proto, *_ = status_msg.details

        # Retry only if the type_url matches the expected error type.
        if any_proto.type_url not in (
            self._UPLOADS_TYPE_URL,
            self._DOWNLOADS_TYPE_URL,
        ):
          raise
        # The any object is of the format:
        # gcloud-disable-gdu-domain
        # [type.googleapis.com/google.storage.v2.BidiWriteObjectRedirectedError]
        # {
        #   routing_token: "<token>",
        #   <key>: "<value>"
        # }
        # This needs to be deserialized to get the routing token. gcloud does
        # not ship google.storage.v2 module, and we can't use the generated
        # client to deserialize the proto. Hence we are relying on string
        # parsing here.
        # TODO: b/448615330 - Update this to get routing token in a more robust
        # way, so we can also extract read/write handles gracefully and use them
        # in the retry logic.
        any_proto_str = str(any_proto)
        match = re.search(r'routing_token: "([^"]+)"', any_proto_str)
        if match:
          self._routing_token = match.group(1)
        else:
          log.debug(
              'Routing token not found in the redirected token error: %s',
              any_proto_str,
          )
