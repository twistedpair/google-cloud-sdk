# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Upload workflow using gRPC API client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import os

from googlecloudsdk.api_lib.storage.gcs_grpc import grpc_util
from googlecloudsdk.api_lib.storage.gcs_grpc import retry_util
from googlecloudsdk.command_lib.storage import hash_util
import six


def _get_write_object_spec(client, object_resource, size):
  """Returns the WriteObjectSpec instance.

  Args:
    client (StorageClient): The GAPIC client.
    object_resource (resource_reference.ObjectResource|UnknownResource): Object
      metadata.
    size (int|None): Expected object size in bytes.
  Returns:
    (gapic_clients.storage_v2.types.WriteObjectSpec) The WriteObjectSpec
    instance.
  """
  destination_object = client.types.Object(
      name=object_resource.storage_url.object_name,
      bucket=grpc_util.get_full_bucket_name(
          object_resource.storage_url.bucket_name),
      size=size)
  return client.types.WriteObjectSpec(
      resource=destination_object, object_size=size)


class _Upload(six.with_metaclass(abc.ABCMeta, object)):
  """Base class shared by different upload strategies."""

  def __init__(
      self,
      client,
      source_stream,
      destination_resource,
      request_config,
      start_offset=0,
  ):
    """Initializes _Upload.

    Args:
      client (StorageClient): The GAPIC client.
      source_stream (io.IOBase): Yields bytes to upload.
      destination_resource (resource_reference.ObjectResource|UnknownResource):
        Metadata for the destination object.
      request_config (gcs_api.GcsRequestConfig): Tracks additional request
        preferences.
      start_offset (int): The offset from the beginning of the object at
        which the data should be written.
    """
    self._client = client
    self._source_stream = source_stream
    self._destination_resource = destination_resource
    self._request_config = request_config
    self._start_offset = start_offset
    # Maintain the state of upload. Useful for resumable and streaming uploads.
    self._uploaded_so_far = start_offset

  def _get_md5_hash_if_given(self):
    """Get MD5 hash bytes sequence from resource args if given.

    Returns:
      bytes|None: MD5 hash bytes sequence if MD5 string was given, otherwise
      None.
    """
    if (self._request_config.resource_args is not None
        and self._request_config.resource_args.md5_hash is not None):
      return hash_util.get_bytes_from_base64_string(
          self._request_config.resource_args.md5_hash)
    return None

  def _upload_write_object_request_generator(self, first_message):
    """Yields the WriteObjectRequest for each chunk of the source stream.

    Args:
      first_message (WriteObjectSpec): WriteObjectSpec.

    Yields:
      (googlecloudsdk.generated_clients.gapic_clients.storage_v2.types.WriteObjectRequest)
      WriteObjectRequest instance.
    """
    first_request_done = False

    write_object_spec = first_message

    # If this method is called multiple times, it is needed to reset
    # what has been uploaded so far.
    self._uploaded_so_far = self._start_offset
    # Set stream position at the start offset.
    self._source_stream.seek(self._start_offset, os.SEEK_SET)

    while True:
      data = self._source_stream.read(
          self._client.types.ServiceConstants.Values.MAX_WRITE_CHUNK_BYTES
      )
      if data:
        if not first_request_done:
          first_request_done = True
          # The first WriteObjectRequest should specify either
          # the WriteObjectSpec or the upload_id.
          yield self._client.types.WriteObjectRequest(
              write_object_spec=write_object_spec,
              write_offset=self._uploaded_so_far,
              checksummed_data=self._client.types.ChecksummedData(
                  content=data
              ))
        else:
          yield self._client.types.WriteObjectRequest(
              write_offset=self._uploaded_so_far,
              checksummed_data=self._client.types.ChecksummedData(
                  content=data))
        self._uploaded_so_far += len(data)
      else:
        md5_hash = self._get_md5_hash_if_given()
        yield self._client.types.WriteObjectRequest(
            write_offset=self._uploaded_so_far,
            checksummed_data=self._client.types.ChecksummedData(
                content=b''),
            object_checksums=self._client.types.ObjectChecksums(
                md5_hash=md5_hash),
            finish_write=True)
        break

  @abc.abstractmethod
  def run(self):
    """Performs an upload and returns and returns an Object message."""
    raise NotImplementedError


class SimpleUpload(_Upload):
  """Uploads an object with a single request."""

  @retry_util.grpc_default_retryer
  def run(self):
    """"Uploads the object in non-resumable mode.

    Returns:
      (gapic_clients.storage_v2.types.WriteObjectResponse) A WriteObjectResponse
      instance.
    """
    write_object_spec = _get_write_object_spec(
        self._client,
        self._destination_resource,
        self._request_config.resource_args.size,
    )
    return self._client.storage.write_object(
        requests=self._upload_write_object_request_generator(
            first_message=write_object_spec
        ))
