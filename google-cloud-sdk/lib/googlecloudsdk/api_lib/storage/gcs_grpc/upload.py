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
import functools
import os

from googlecloudsdk.api_lib.storage import retry_util as storage_retry_util
from googlecloudsdk.api_lib.storage.gcs_grpc import grpc_util
from googlecloudsdk.api_lib.storage.gcs_grpc import retry_util
from googlecloudsdk.command_lib.storage import hash_util
from googlecloudsdk.command_lib.storage.tasks.cp import copy_util
from googlecloudsdk.core import log
import six


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
    """Returns MD5 hash bytes sequence from resource args if given.

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
      first_message (WriteObjectSpec|str): WriteObjectSpec for Simple uploads,
      str that is the upload id for Resumable uploads.

    Yields:
      (googlecloudsdk.generated_clients.gapic_clients.storage_v2.types.WriteObjectRequest)
      WriteObjectRequest instance.
    """
    first_request_done = False

    if isinstance(first_message, self._client.types.WriteObjectSpec):
      write_object_spec = first_message
      upload_id = None
    else:
      write_object_spec = None
      upload_id = first_message

    # If this method is called multiple times, it is needed to reset
    # what has been uploaded so far.
    self._uploaded_so_far = self._start_offset
    # Set stream position at the start offset.
    self._source_stream.seek(self._start_offset, os.SEEK_SET)

    while True:
      data = self._source_stream.read(
          self._client.types.ServiceConstants.Values.MAX_WRITE_CHUNK_BYTES
      )

      if not first_request_done:
        first_request_done = True
      else:
        write_object_spec = None
        upload_id = None

      if data:
        object_checksums = None
        finish_write = False
      else:
        # Handles final request case.
        object_checksums = self._client.types.ObjectChecksums(
            md5_hash=self._get_md5_hash_if_given()
        )
        finish_write = True

      yield self._client.types.WriteObjectRequest(
          write_object_spec=write_object_spec,
          upload_id=upload_id,
          write_offset=self._uploaded_so_far,
          checksummed_data=self._client.types.ChecksummedData(content=data),
          object_checksums=object_checksums,
          finish_write=finish_write,
      )
      self._uploaded_so_far += len(data)

      if finish_write:
        break

  def _get_write_object_spec(self, size=None):
    """Returns the WriteObjectSpec instance.

    Args:
      size (int|None): Expected object size in bytes.

    Returns:
      (gapic_clients.storage_v2.types.WriteObjectSpec) The WriteObjectSpec
      instance.
    """

    destination_object = self._client.types.Object(
        name=self._destination_resource.storage_url.object_name,
        bucket=grpc_util.get_full_bucket_name(
            self._destination_resource.storage_url.bucket_name),
        size=size)

    return self._client.types.WriteObjectSpec(
        resource=destination_object,
        if_generation_match=copy_util.get_generation_match_value(
            self._request_config
        ),
        if_metageneration_match=(
            self._request_config.precondition_metageneration_match
        ),
        object_size=size)

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
    write_object_spec = self._get_write_object_spec(
        self._request_config.resource_args.size)
    return self._client.storage.write_object(
        requests=self._upload_write_object_request_generator(
            first_message=write_object_spec
        ))


class RecoverableUpload(_Upload):
  """Common logic for strategies allowing retries in-flight."""

  def _initialize_upload(self):
    """Sets up the upload session and returns the upload id.

    This method sets the start offset to 0.

    Returns:
      (str) Session URI for resumable upload operation.
    """

    # TODO(b/267555253): Add size to the spec once the fix is in prod.
    write_object_spec = self._get_write_object_spec()

    request = self._client.types.StartResumableWriteRequest(
        write_object_spec=write_object_spec
    )

    upload_id = self._client.storage.start_resumable_write(
        request=request).upload_id
    self._start_offset = 0
    return upload_id

  def _get_write_offset(self, upload_id):
    """Returns the amount of data persisted on the server.

    Args:
      upload_id (str): Session URI for resumable upload operation.
    Returns:
      (int) The total number of bytes that have been persisted for an object
      on the server. This value can be used as the write_offset.
    """
    request = self._client.types.QueryWriteStatusRequest(
        upload_id=upload_id
    )

    return self._client.storage.query_write_status(
        request=request,
    ).persisted_size

  def _should_retry(self, upload_id, exc_type=None, exc_value=None,
                    exc_traceback=None, state=None):
    if not retry_util.is_retriable(exc_type, exc_value, exc_traceback, state):
      return False

    persisted_size = self._get_write_offset(upload_id)
    is_progress_made_since_last_uplaod = persisted_size > self._start_offset
    if is_progress_made_since_last_uplaod:
      self._start_offset = persisted_size

    return True

  def _perform_upload(self, upload_id):
    return self._client.storage.write_object(
        requests=self._upload_write_object_request_generator(
            first_message=upload_id
        )
    )

  def run(self):
    upload_id = self._initialize_upload()

    new_should_retry = functools.partial(self._should_retry, upload_id)
    return storage_retry_util.retryer(
        target=self._perform_upload,
        should_retry_if=new_should_retry,
        target_args=[upload_id],
    )


class ResumableUpload(RecoverableUpload):
  """Uploads objects with support for resuming between runs of a command."""

  def __init__(
      self,
      client,
      source_stream,
      destination_resource,
      request_config,
      serialization_data=None,
      tracker_callback=None,
  ):
    super(ResumableUpload, self).__init__(client, source_stream,
                                          destination_resource, request_config)
    self._serialization_data = serialization_data
    self._tracker_callback = tracker_callback

  def _initialize_upload(self):
    """Sets up the upload session and returns the upload id.

    Additionally, it does the following tasks:
    1. Grabs the persisted size on the backend.
    2. Sets the appropiate write offset.
    3. Calls the tracker callback.

    Returns:
      The upload session ID.
    """

    if self._serialization_data is not None:
      upload_id = self._serialization_data['upload_id']

      write_offset = self._get_write_offset(upload_id)
      self._start_offset = write_offset
      log.debug('Write offset after resuming: %s', write_offset)
    else:
      upload_id = super(ResumableUpload, self)._initialize_upload()

    if self._tracker_callback is not None:
      self._tracker_callback({'upload_id': upload_id})

    return upload_id
