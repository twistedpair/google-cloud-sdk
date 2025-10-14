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
"""Upload workflow using gRPC bidi streaming API client."""

from __future__ import absolute_import
from __future__ import annotations
from __future__ import division
from __future__ import unicode_literals

import abc
import collections
import io
import os

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import errors as api_errors
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.api_lib.storage.gcs_grpc import grpc_util
from googlecloudsdk.api_lib.storage.gcs_grpc import metadata_util
from googlecloudsdk.api_lib.storage.gcs_grpc import retry_util
from googlecloudsdk.command_lib.storage import errors as command_errors
from googlecloudsdk.command_lib.storage import fast_crc32c_util
from googlecloudsdk.command_lib.storage import hash_util
from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.command_lib.storage.tasks.cp import copy_util
from googlecloudsdk.command_lib.util import crc32c
from googlecloudsdk.core import gapic_util
from googlecloudsdk.core import log
import six

# TODO: b/441010615 - Remove this constant once the flush size is configurable
# by the user. The default flush size is 50MiB.
_DEFAULT_FLUSH_SIZE = 50 * 1024 * 1024


class _Upload(six.with_metaclass(abc.ABCMeta, object)):
  """Base class shared by different upload strategies.

  This class is not thread-safe due to the state maintained in instance
  variables like `_uploaded_so_far`, `_buffer`, and `_initial_request`.
  """

  def __init__(
      self,
      client,
      source_stream: io.IOBase,
      destination_resource: (
          resource_reference.ObjectResource | resource_reference.UnknownResource
      ),
      request_config: request_config_factory._GcsRequestConfig,
      source_resource: (
          resource_reference.FileObjectResource
          | resource_reference.ObjectResource
      ),
      start_offset: int = 0,
      delegator: cloud_api.CloudApi | None = None,
  ):
    """Initializes _Upload.

    Args:
      client (gapic_clients.storage_v2.services.storage.client.StorageClient):
        The GAPIC client.
      source_stream: Yields bytes to upload.
      destination_resource: Metadata for the destination object.
      request_config: Tracks additional request preferences.
      source_resource: Contains the source StorageUrl and source object
        metadata.
      start_offset: The offset from the beginning of the object at which
        the data should be written.
      delegator: The client used to make non-bidi streaming or metadata API
        calls.
    """
    self._client = client
    self._source_stream = source_stream
    self._destination_resource = destination_resource
    self._request_config = request_config
    self._start_offset = start_offset
    # Maintain the state of upload. Useful for resumable and streaming uploads.
    self._uploaded_so_far = start_offset
    self._source_resource = source_resource
    self._delegator = delegator
    self._should_use_crc32c = (
        fast_crc32c_util.check_if_will_use_fast_crc32c(install_if_missing=True)
    )
    self._buffer = collections.deque(maxlen=self._get_max_buffer_size())
    self._initial_request = None

  def _get_max_buffer_size(self):
    """Returns the maximum buffer size."""
    # The buffer size is calculated as follows:
    # 1. The default flush size is 50MiB.
    # 2. The maximum size of a single request is 2MiB.
    # 4. The maximum size of the buffer is calculated as:
    #    (50MiB + (2MiB)) // (2MiB) = 26
    # 5. Similarily for buffer size of odd flush size:
    #    (51MiB + (2MiB)) // (2MiB) = 26
    # 6. The maximum number of requests that can be buffered is 13.
    chunk_size = (
        self._client.types.ServiceConstants.Values.MAX_WRITE_CHUNK_BYTES
    )
    return (_DEFAULT_FLUSH_SIZE + (chunk_size)) // (chunk_size)

  def _initialize_bidi_write(self):
    """Initializes the generator for the upload."""
    self._uploaded_so_far = self._start_offset
    self._source_stream.seek(self._start_offset, os.SEEK_SET)

  def _get_crc32c_hash(self, data: bytes, length: int) -> int | None:
    """Returns CRC32C hash of the given data."""
    if not self._should_use_crc32c:
      return None
    crc32c_hash = hash_util.get_hash_from_data_chunk_or_file(
        self._source_resource.storage_url.resource_name,
        data,
        hash_util.HashAlgorithm.CRC32C,
        self._uploaded_so_far,
        self._uploaded_so_far + length,
    )
    return int.from_bytes(crc32c_hash.digest(), byteorder='big')

  def _send_buffer_to_bidi_write_rpc(self, bidi_write_rpc) -> None:
    """Sends the buffer to the bidi write RPC."""
    if not self._buffer:
      return

    for request in self._buffer:
      bidi_write_rpc.send(request)
    while True:
      response = bidi_write_rpc.recv()
      if response.write_handle:
        self._initial_request.append_object_spec.write_handle = (
            response.write_handle
        )
      if (
          response.persisted_size is not None
          and response.persisted_size == self._uploaded_so_far
      ):
        self._start_offset = response.persisted_size
        break
    self._buffer.clear()

  def _update_initial_request(self, response):
    """Updates the initial request for the bidi write RPC.

    If the initial request is an append_object_spec, then we update the
    write_handle in the initial request with the one from the response, for
    retries.
    If the initial request is a write_object_spec, then we need to update the
    initial request with an append_object_spec based on the response. This is
    because write_object_spec is only used for creating an appendable object.
    For retrying on failures, we need to use append_object_spec to append to an
    existing object.

    For failures on the first request(creating or appending),
    this method is not called, and the initial request is not modified.

    Args:
      response (gapic_clients.storage_v2.types.BidiWriteObjectResponse): The
        response from the bidi write RPC.
    """
    if self._initial_request.append_object_spec:
      if response.write_handle:
        self._initial_request.append_object_spec.write_handle = (
            response.write_handle
        )
      return
    self._initial_request = self._client.types.BidiWriteObjectRequest(
        append_object_spec=self._client.types.AppendObjectSpec(
            bucket=response.resource.bucket,
            object=response.resource.name,
            generation=response.resource.generation,
            if_metageneration_match=(
                self._request_config.precondition_metageneration_match
            ),
            write_handle=response.write_handle,
        ),
    )

  def _get_updated_bidi_write_rpc_if_retrying(self, bidi_write_rpc):
    """Returns the updated bidi write RPC for resuming an upload."""
    # If the call is None, it means that the RPC was not initialized, and its a
    # new upload. In this case we need not initialize the RPC again. As it is
    # already done by the caller.
    if bidi_write_rpc.call is not None:
      # If the call is not None, it means that the RPC was initialized before
      # and we need to create a new RPC with the updated initial request for
      # retrying the upload.
      bidi_write_rpc = gapic_util.MakeBidiRpc(
          self._client,
          self._client.storage.bidi_write_object,
          initial_request=self._initial_request,
          metadata=metadata_util.get_bucket_name_routing_header(
              grpc_util.get_full_bucket_name(
                  self._destination_resource.storage_url.bucket_name
              )
          ),
      )
    return bidi_write_rpc

  @retry_util.grpc_default_retryer
  def _bidi_write_appendable_object(
      self, bidi_write_rpc, resuming_upload: bool = False
  ):
    """Performs the bidi write RPC for an appendable object."""
    bidi_write_rpc = self._get_updated_bidi_write_rpc_if_retrying(
        bidi_write_rpc
    )
    try:
      bidi_write_rpc.open()
      # TODO: b/440507899 - Add support for retrying an upload with a token.
      # (Redirected token error handling) and/or error handling/retries.
      response = bidi_write_rpc.recv()
      self._update_initial_request(response)

      if resuming_upload:
        self._check_existing_destination_is_valid(response.resource)
        self._start_offset = response.resource.size

      # If the upload is being retried, we need to send the existing buffer to
      # the bidi write RPC before initializing the upload. This is because the
      # buffer contains the data that was written before the upload was
      # interrupted. We will be retrying on the entire buffer.
      self._send_buffer_to_bidi_write_rpc(bidi_write_rpc)
      self._initialize_bidi_write()
      flush_interval = self._start_offset + _DEFAULT_FLUSH_SIZE

      while True:
        data = self._source_stream.read(
            self._client.types.ServiceConstants.Values.MAX_WRITE_CHUNK_BYTES
        )
        length_of_data = len(data)

        if self._uploaded_so_far + length_of_data >= flush_interval:
          should_flush = True
          flush_interval += _DEFAULT_FLUSH_SIZE
        else:
          should_flush = False

        finish_write = not length_of_data
        if finish_write:
          # Handles final request case.
          should_flush = True

        self._buffer.append(
            self._client.types.BidiWriteObjectRequest(
                write_offset=self._uploaded_so_far,
                checksummed_data=self._client.types.ChecksummedData(
                    content=data,
                    crc32c=self._get_crc32c_hash(data, length_of_data),
                ),
                flush=should_flush,
                state_lookup=should_flush,
            )
        )
        self._uploaded_so_far += length_of_data
        if should_flush:
          self._send_buffer_to_bidi_write_rpc(bidi_write_rpc)

        if finish_write:
          break
    finally:
      bidi_write_rpc.close()

  def _get_request_for_creating_append_object(self):
    """Returns the request for creating an appendable object.

    Returns:
      gapic_clients.storage_v2.types.BidiWriteObjectRequest: A
        BidiWriteObjectRequest instance.
    """
    destination_object = self._client.types.Object(
        name=self._destination_resource.storage_url.resource_name,
        bucket=grpc_util.get_full_bucket_name(
            self._destination_resource.storage_url.bucket_name
        ),
    )

    metadata_util.update_object_metadata_from_request_config(
        destination_object, self._request_config, self._source_resource
    )

    write_object_spec = self._client.types.WriteObjectSpec(
        resource=destination_object,
        if_generation_match=copy_util.get_generation_match_value(
            self._request_config
        ),
        if_metageneration_match=(
            self._request_config.precondition_metageneration_match
        ),
        appendable=True,
    )
    return self._client.types.BidiWriteObjectRequest(
        write_object_spec=write_object_spec,
    )

  def _get_request_for_resuming_appendable_object_upload(
      self, destination_object: resource_reference.ObjectResource
  ):
    """Returns the request for resuming an appendable object upload."""
    append_object_spec = self._client.types.AppendObjectSpec(
        bucket=grpc_util.get_full_bucket_name(destination_object.bucket),
        object=destination_object.name,
        generation=destination_object.generation,
        if_metageneration_match=(
            self._request_config.precondition_metageneration_match
        ),
    )
    return self._client.types.BidiWriteObjectRequest(
        append_object_spec=append_object_spec
    )

  def _check_existing_destination_is_valid(self, destination_object):
    """Checks if the existing destination object is valid."""
    if not self._should_use_crc32c:
      return
    crc32c_hash = hash_util.get_hash_from_file(
        self._source_resource.storage_url.resource_name,
        hash_util.HashAlgorithm.CRC32C,
        0,
        destination_object.size,
    )
    calculated_crc32c_hash = crc32c.get_hash(crc32c_hash)
    destination_crc32c_hash = crc32c.get_crc32c_hash_string_from_checksum(
        destination_object.checksums.crc32c
    )
    try:
      hash_util.validate_object_hashes_match(
          self._destination_resource.storage_url.url_string,
          calculated_crc32c_hash,
          destination_crc32c_hash,
      )
    except command_errors.HashMismatchError as e:
      self._delegator.delete_object(
          self._destination_resource.storage_url,
          request_config=self._request_config,
      )
      raise e
    else:
      log.info(
          'Destination object is valid. Resuming upload for object: %s',
          self._destination_resource.storage_url.resource_name,
      )

  @retry_util.grpc_default_retryer
  def _get_object_if_exists(self) -> resource_reference.ObjectResource | None:
    """Returns the destination object if it exists."""
    try:
      return self._delegator.get_object_metadata(
          self._destination_resource.storage_url.bucket_name,
          self._destination_resource.storage_url.resource_name,
          self._request_config,
      )
    except api_errors.NotFoundError:
      log.debug(
          'Object %s does not exist. Proceeding with upload.',
          self._destination_resource.storage_url.resource_name,
      )
      return None

  @retry_util.grpc_default_retryer
  def _get_object_metadata_after_upload(
      self,
  ) -> resource_reference.ObjectResource:
    """Returns the object metadata after the upload."""
    read_request = self._client.types.BidiReadObjectRequest(
        read_object_spec=self._client.types.BidiReadObjectSpec(
            bucket=self._initial_request.append_object_spec.bucket,
            object=self._initial_request.append_object_spec.object,
            generation=self._initial_request.append_object_spec.generation,
        )
    )
    bidi_rpc = gapic_util.MakeBidiRpc(
        self._client,
        self._client.storage.bidi_read_object,
        initial_request=read_request,
        metadata=metadata_util.get_bucket_name_routing_header(
            grpc_util.get_full_bucket_name(
                self._destination_resource.storage_url.bucket_name
            )
        ),
    )
    try:
      bidi_rpc.open()
      response = bidi_rpc.recv()
    finally:
      bidi_rpc.close()
    return metadata_util.get_object_resource_from_grpc_object(response.metadata)

  @abc.abstractmethod
  def run(self):
    """Performs an upload and returns an Object message."""
    raise NotImplementedError()


class SimpleUpload(_Upload):
  """Uploads an object in single-shot mode."""

  def run(self):
    """Uploads the object in single-shot mode.

    Returns:
      resource_reference.ObjectResource with object metadata.

    Raises:
      CloudApiError: API returned an error.
    """
    self._initial_request = self._get_request_for_creating_append_object()
    bidi_write_rpc = gapic_util.MakeBidiRpc(
        self._client,
        self._client.storage.bidi_write_object,
        initial_request=self._initial_request,
        metadata=metadata_util.get_bucket_name_routing_header(
            grpc_util.get_full_bucket_name(
                self._destination_resource.storage_url.bucket_name
            )
        ),
    )

    self._bidi_write_appendable_object(bidi_write_rpc)

    return self._get_object_metadata_after_upload()


class ResumableUpload(_Upload):
  """Uploads an object in resumable mode."""

  def run(self):
    """Uploads the object in resumable mode.

    Returns:
      resource_reference.ObjectResource with object metadata.

    Raises:
      CloudApiError: API returned an error.
    """
    metadata = metadata_util.get_bucket_name_routing_header(
        grpc_util.get_full_bucket_name(
            self._destination_resource.storage_url.bucket_name
        )
    )

    destination_object = self._get_object_if_exists()
    if destination_object:
      self._initial_request = (
          self._get_request_for_resuming_appendable_object_upload(
              destination_object
          )
      )
      bidi_write_rpc = gapic_util.MakeBidiRpc(
          self._client,
          self._client.storage.bidi_write_object,
          initial_request=self._initial_request,
          metadata=metadata,
      )
      self._start_offset = destination_object.size
      log.info(
          'Attempting to resume upload for object: %s at offset: %s',
          destination_object.name,
          destination_object.size,
      )
      try:
        self._bidi_write_appendable_object(bidi_write_rpc, resuming_upload=True)
        return self._get_object_metadata_after_upload()
      except command_errors.HashMismatchError as e:
        log.info(e)

    return SimpleUpload(
        client=self._client,
        source_stream=self._source_stream,
        destination_resource=self._destination_resource,
        request_config=self._request_config,
        source_resource=self._source_resource,
        start_offset=0,
        delegator=self._delegator,
    ).run()
