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
from __future__ import division
from __future__ import unicode_literals

import abc
import io

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.api_lib.storage.gcs_grpc import grpc_util
from googlecloudsdk.api_lib.storage.gcs_grpc import metadata_util
from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.command_lib.storage.tasks.cp import copy_util
from googlecloudsdk.core import gapic_util
import six


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
          | None
      ) = None,
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
      source_resource: Contains the source StorageUrl and source object metadata
        for daisy chain transfers. Can be None if source is pure stream.
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

  def _bidi_write_appendable_object(self, bidi_write_rpc):
    """Yields the responses for writing to an appendable object."""
    try:
      bidi_write_rpc.open()
      yield bidi_write_rpc.recv()
      # TODO: b/440323479 - Add upload logic. (e.g. send data requests, handle
      # exceptions, recv responses, etc.)
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

  @abc.abstractmethod
  def run(self):
    """Performs an upload and returns an Object message."""
    raise NotImplementedError()


class SimpleUpload(_Upload):
  """Uploads an object in single-shot mode."""

  def run(self):
    """Uploads the object in single-shot mode.

    Returns:
      gapic_clients.storage_v2.types.BidiWriteObjectResponse: A
        BidiWriteObjectResponse instance.
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

    raise NotImplementedError()


class ResumableUpload(_Upload):
  """Uploads an object in resumable mode."""

  def run(self):
    """Uploads the object in resumable mode.

    Returns:
      gapic_clients.storage_v2.types.BidiWriteObjectResponse: A
        BidiWriteObjectResponse instance.
    """
    raise NotImplementedError()
