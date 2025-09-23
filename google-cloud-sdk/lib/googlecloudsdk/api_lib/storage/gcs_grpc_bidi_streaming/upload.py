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
import io
import os

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import errors as api_errors
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.api_lib.storage.gcs_grpc import grpc_util
from googlecloudsdk.api_lib.storage.gcs_grpc import metadata_util
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
  """Base class shared by different upload strategies."""

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
        self._uploaded_so_far+length,
    )
    return int.from_bytes(crc32c_hash.digest(), byteorder='big')

  def _bidi_write_appendable_object(
      self, bidi_write_rpc, resuming_upload: bool = False
  ):
    """Yields the responses from the bidi write RPC for an appendable object."""
    try:
      bidi_write_rpc.open()
      response = bidi_write_rpc.recv()
      if resuming_upload:
        self._check_existing_destination_is_valid(response.resource)
        self._start_offset = response.resource.size
      yield response
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

        # TODO: b/441012774 - Send the request to the bidi write RPC in a
        # controlled manner. This is to avoid sending too much data at once and
        # causing excessive throttling, which can lead to errors.
        bidi_write_rpc.send(
            self._client.types.BidiWriteObjectRequest(
                write_offset=self._uploaded_so_far,
                checksummed_data=self._client.types.ChecksummedData(
                    content=data,
                    crc32c=self._get_crc32c_hash(data, length_of_data),
                ),
                flush=should_flush,
                state_lookup=finish_write,
            )
        )
        self._uploaded_so_far += length_of_data

        if finish_write:
          # TODO: b/441012774 - Add support for handling server side errors or
          # additional responses.
          yield bidi_write_rpc.recv()
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

    bidi_write_rpc = gapic_util.MakeBidiRpc(
        self._client,
        self._client.storage.bidi_write_object,
        initial_request=self._get_request_for_creating_append_object(),
        metadata=metadata_util.get_bucket_name_routing_header(
            grpc_util.get_full_bucket_name(
                self._destination_resource.storage_url.bucket_name
            )
        ),
    )

    # The method returns a generator, so we need to consume it. To avoid early
    # exit. The response is additionally required in future implementations
    # for b/440505603.
    _ = list(self._bidi_write_appendable_object(bidi_write_rpc))

    # TODO: b/440505603 - Replace this call with bidi api call since the object
    # metadata is synchronised periodically.
    return self._delegator.get_object_metadata(
        self._destination_resource.storage_url.bucket_name,
        self._destination_resource.storage_url.resource_name,
    )


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
      bidi_write_rpc = gapic_util.MakeBidiRpc(
          self._client,
          self._client.storage.bidi_write_object,
          initial_request=self._get_request_for_resuming_appendable_object_upload(
              destination_object
          ),
          metadata=metadata,
      )
      self._start_offset = destination_object.size
      log.info(
          'Attempting to resume upload for object: %s at offset: %s',
          destination_object.name,
          destination_object.size,
      )
      try:
        list(
            self._bidi_write_appendable_object(
                bidi_write_rpc,
                resuming_upload=True,
            )
        )
        # TODO: b/440505603 - Replace this call with bidi api call since the
        # object metadata is synchronised periodically.
        return self._delegator.get_object_metadata(
            self._destination_resource.storage_url.bucket_name,
            self._destination_resource.storage_url.resource_name,
        )
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

    else:
      return SimpleUpload(
          client=self._client,
          source_stream=self._source_stream,
          destination_resource=self._destination_resource,
          request_config=self._request_config,
          source_resource=self._source_resource,
          start_offset=self._start_offset,
          delegator=self._delegator,
      ).run()
