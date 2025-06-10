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
"""Client for interacting with Google Cloud Storage using gRPC API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import errors as cloud_errors
from googlecloudsdk.api_lib.storage.gcs_grpc import download
from googlecloudsdk.api_lib.storage.gcs_grpc import grpc_util
from googlecloudsdk.api_lib.storage.gcs_grpc import metadata_util
from googlecloudsdk.api_lib.storage.gcs_grpc import upload
from googlecloudsdk.api_lib.storage.gcs_json import client as gcs_json_client
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.command_lib.storage import encryption_util
from googlecloudsdk.command_lib.storage import gzip_util
from googlecloudsdk.command_lib.storage import tracker_file_util
from googlecloudsdk.command_lib.storage import user_request_args_factory
from googlecloudsdk.command_lib.storage.tasks.cp import copy_util
from googlecloudsdk.command_lib.storage.tasks.cp import download_util
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import scaled_integer


class GrpcClientWithJsonFallback(gcs_json_client.JsonClient):
  """Client for Google Cloud Storage API using gRPC with JSON fallback."""

  ALLOWED_PREDFINED_DESTINATION_ACL_VALUES = (
      'authenticatedRead',
      'bucketOwnerFullControl',
      'bucketOwnerRead',
      'private',
      'projectPrivate',
      'publicRead',
  )

  # The API limits the number of objects that can be composed in a single call.
  # https://cloud.google.com/storage/docs/json_api/v1/objects/compose
  _MAX_OBJECTS_PER_COMPOSE_CALL = 32

  def __init__(self):
    super(GrpcClientWithJsonFallback, self).__init__()
    self._gapic_client = None

  def _get_gapic_client(self, redact_request_body_reason=None):
    # Not using @property because the side-effect is non-trivial and
    # might not be obvious. Someone might accidentally access the
    # property and end up creating the gapic client.
    # Creating the gapic client before "fork" will lead to a deadlock.
    if self._gapic_client is None:
      self._gapic_client = core_apis.GetGapicClientInstance(
          'storage',
          'v2',
          attempt_direct_path=True,
          redact_request_body_reason=redact_request_body_reason,
      )
    return self._gapic_client

  def compose_objects(
      self,
      source_resources,
      destination_resource,
      request_config,
      original_source_resource=None,
      posix_to_set=None,
  ):
    """Concatenates a list of objects into a new object.

    Args:
      source_resources (list[ObjectResource|UnknownResource]): The objects to
        compose.
      destination_resource (resource_reference.UnknownResource): Metadata for
        the resulting composite object.
      request_config (RequestConfig): Object containing general API function
        arguments. Subclasses for specific cloud providers are available.
      original_source_resource (Resource|None): Useful for finding metadata to
        apply to final object. For instance, if doing a composite upload, this
        would represent the pre-split local file.
      posix_to_set (PosixAttributes|None): Set as custom metadata on target.

    Returns:
      resource_reference.ObjectResource with composite object's metadata.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    if not source_resources:
      raise cloud_errors.GcsApiError(
          'Compose requires at least one component object.'
      )

    if len(source_resources) > self._MAX_OBJECTS_PER_COMPOSE_CALL:
      raise cloud_errors.GcsApiError(
          f'Compose was called with {len(source_resources)} objects. The limit'
          f' is {self._MAX_OBJECTS_PER_COMPOSE_CALL}.'
      )

    self._get_gapic_client()

    source_messages = []
    for source in source_resources:
      source_message = (
          self._gapic_client.types.ComposeObjectRequest.SourceObject(
              name=source.storage_url.resource_name
          )
      )
      if source.storage_url.generation is not None:
        source_message.generation = int(source.storage_url.generation)
      source_messages.append(source_message)

    base_destination_metadata = metadata_util.get_grpc_metadata_from_url(
        destination_resource.storage_url, self._gapic_client.types
    )
    if getattr(source_resources[0], 'metadata', None) is not None:
      final_destination_metadata = metadata_util.copy_object_metadata(
          source_resources[0].metadata,
          base_destination_metadata,
          request_config,
      )
    else:
      final_destination_metadata = base_destination_metadata
    metadata_util.update_object_metadata_from_request_config(
        final_destination_metadata,
        request_config,
        attributes_resource=original_source_resource,
        posix_to_set=posix_to_set,
    )

    final_destination_metadata.bucket = grpc_util.get_full_bucket_name(
        destination_resource.storage_url.bucket_name
    )
    final_destination_metadata.name = (
        destination_resource.storage_url.resource_name
    )
    compose_request = self._gapic_client.types.ComposeObjectRequest(
        source_objects=source_messages,
        destination=final_destination_metadata,
        if_generation_match=request_config.precondition_generation_match,
        if_metageneration_match=request_config.precondition_metageneration_match,
    )

    if request_config.resource_args:
      encryption_key = request_config.resource_args.encryption_key
      if (
          encryption_key
          and encryption_key != user_request_args_factory.CLEAR
          and encryption_key.type == encryption_util.KeyType.CMEK
      ):
        compose_request.kms_key = encryption_key.key

    if request_config.predefined_acl_string is not None:
      compose_request.destination_predefined_acl = (
          request_config.predefined_acl_string
      )

    encryption_key = getattr(
        request_config.resource_args, 'encryption_key', None
    )
    with self._encryption_headers_context(encryption_key):
      return metadata_util.get_object_resource_from_grpc_object(
          self._gapic_client.storage.compose_object(compose_request)
      )

  def copy_object(
      self,
      source_resource,
      destination_resource,
      request_config,
      posix_to_set=None,
      progress_callback=None,
      should_deep_copy_metadata=False,
  ):
    """See super class."""
    self._get_gapic_client()
    destination_metadata = getattr(destination_resource, 'metadata', None)
    if not destination_metadata:
      destination_metadata = metadata_util.get_grpc_metadata_from_url(
          destination_resource.storage_url, self._gapic_client.types
      )
    if source_resource.metadata:
      destination_metadata = metadata_util.copy_object_metadata(
          source_metadata=source_resource.metadata,
          destination_metadata=destination_metadata,
          request_config=request_config,
          should_deep_copy=should_deep_copy_metadata,
      )
    metadata_util.update_object_metadata_from_request_config(
        destination_metadata, request_config, posix_to_set=posix_to_set
    )

    if request_config.predefined_acl_string and (
        request_config.predefined_acl_string
        in self.ALLOWED_PREDFINED_DESTINATION_ACL_VALUES
    ):
      predefined_acl = request_config.predefined_acl_string
    else:
      predefined_acl = None

    if source_resource.generation is None:
      source_generation = None
    else:
      source_generation = int(source_resource.generation)

    tracker_file_path = tracker_file_util.get_tracker_file_path(
        destination_resource.storage_url,
        tracker_file_util.TrackerFileType.REWRITE,
        source_url=source_resource.storage_url,
    )
    rewrite_parameters_hash = (
        tracker_file_util.hash_gcs_rewrite_parameters_for_tracker_file(
            source_object_resource=source_resource,
            destination_object_resource=destination_resource,
            destination_metadata=destination_metadata,
            request_config=request_config,
        )
    )

    resume_rewrite_token = (
        tracker_file_util.get_rewrite_token_from_tracker_file(
            tracker_file_path, rewrite_parameters_hash
        )
    )
    if resume_rewrite_token:
      log.debug('Found rewrite token. Resuming copy.')
    else:
      log.debug('No rewrite token found. Starting copy from scratch.')

    max_bytes_per_call = scaled_integer.ParseInteger(
        properties.VALUES.storage.copy_chunk_size.Get()
    )

    with self._encryption_headers_for_rewrite_call_context(request_config):
      while True:
        request = self._gapic_client.types.RewriteObjectRequest(
            source_bucket=grpc_util.get_full_bucket_name(
                source_resource.storage_url.bucket_name
            ),
            source_object=source_resource.storage_url.resource_name,
            destination_bucket=grpc_util.get_full_bucket_name(
                destination_resource.storage_url.bucket_name
            ),
            destination_name=destination_resource.storage_url.resource_name,
            destination=destination_metadata,
            source_generation=source_generation,
            if_generation_match=copy_util.get_generation_match_value(
                request_config
            ),
            if_metageneration_match=request_config.precondition_metageneration_match,
            destination_predefined_acl=predefined_acl,
            rewrite_token=resume_rewrite_token,
            max_bytes_rewritten_per_call=max_bytes_per_call,
        )

        encryption_key = getattr(
            request_config.resource_args, 'encryption_key', None
        )
        if (
            encryption_key
            and encryption_key != user_request_args_factory.CLEAR
            and encryption_key.type == encryption_util.KeyType.CMEK
        ):
          # This key is also provided in destination_metadata.kmsKeyName by
          # update_object_metadata_from_request_config. This has no effect on
          # the copy object request, which references the field below, and is a
          # side-effect of logic required for uploads and compose operations.
          request.destination_kms_key = encryption_key.key

        rewrite_response = self._gapic_client.storage.rewrite_object(request)
        processed_bytes = rewrite_response.total_bytes_rewritten
        if progress_callback:
          progress_callback(processed_bytes)

        if rewrite_response.done:
          break

        if not resume_rewrite_token:
          resume_rewrite_token = rewrite_response.rewrite_token
          if source_resource.size >= scaled_integer.ParseInteger(
              properties.VALUES.storage.resumable_threshold.Get()
          ):
            tracker_file_util.write_rewrite_tracker_file(
                tracker_file_path,
                rewrite_parameters_hash,
                rewrite_response.rewrite_token,
            )

    tracker_file_util.delete_tracker_file(tracker_file_path)
    return metadata_util.get_object_resource_from_grpc_object(
        rewrite_response.resource
    )

  def delete_object(self, object_url, request_config):
    """See super class."""
    # S3 requires a string, but GCS uses an int for generation.
    if object_url.generation is not None:
      generation = int(object_url.generation)
    else:
      generation = None

    self._get_gapic_client()

    request = self._gapic_client.types.DeleteObjectRequest(
        bucket=grpc_util.get_full_bucket_name(object_url.bucket_name),
        object=object_url.resource_name,
        generation=generation,
        if_generation_match=request_config.precondition_generation_match,
        if_metageneration_match=request_config.precondition_metageneration_match,
    )
    # Success returns an empty body.
    self._gapic_client.storage.delete_object(request)

  def restore_object(self, url, request_config):
    """See super class."""
    if request_config.resource_args:
      preserve_acl = request_config.resource_args.preserve_acl
    else:
      preserve_acl = None

    self._get_gapic_client()

    object_metadata = self._gapic_client.storage.restore_object(
        self._gapic_client.types.RestoreObjectRequest(
            bucket=grpc_util.get_full_bucket_name(url.bucket_name),
            object=url.resource_name,
            generation=int(url.generation),
            if_generation_match=request_config.precondition_generation_match,
            if_metageneration_match=(
                request_config.precondition_metageneration_match
            ),
            copy_source_acl=preserve_acl,
        )
    )

    return metadata_util.get_object_resource_from_grpc_object(object_metadata)

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
    if download_util.return_and_report_if_nothing_to_download(
        cloud_resource, progress_callback
    ):
      return None

    if (
        request_config.resource_args is not None
        and request_config.resource_args.decryption_key is not None
    ):
      decryption_key = request_config.resource_args.decryption_key
    else:
      decryption_key = None
    downloader = download.GrpcDownload(
        gapic_client=self._get_gapic_client(),
        cloud_resource=cloud_resource,
        download_stream=download_stream,
        start_byte=start_byte,
        end_byte=end_byte,
        digesters=digesters,
        progress_callback=progress_callback,
        download_strategy=download_strategy,
        decryption_key=decryption_key)
    downloader.run()
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

    client = self._get_gapic_client(
        redact_request_body_reason=(
            'Object data is not displayed to keep the log output clean.'
            ' Set log_http_show_request_body property to True to print the'
            ' body of this request.'
        )
    )

    source_path = self._get_source_path(source_resource)
    should_gzip_in_flight = gzip_util.should_gzip_in_flight(
        request_config.gzip_settings, source_path)

    if should_gzip_in_flight:
      raise core_exceptions.InternalError(
          'Gzip transport encoding is not supported with GRPC API, please use'
          ' the JSON API instead, changing the storage/preferred_api config'
          ' value to json.'
      )

    if upload_strategy == cloud_api.UploadStrategy.SIMPLE:
      uploader = upload.SimpleUpload(
          client=client,
          source_stream=source_stream,
          destination_resource=destination_resource,
          request_config=request_config,
          source_resource=source_resource,
      )
    elif upload_strategy == cloud_api.UploadStrategy.RESUMABLE:
      uploader = upload.ResumableUpload(
          client=client,
          source_stream=source_stream,
          destination_resource=destination_resource,
          request_config=request_config,
          serialization_data=serialization_data,
          source_resource=source_resource,
          tracker_callback=tracker_callback,
      )
    else:  # Streaming.
      uploader = upload.StreamingUpload(
          client=client,
          source_stream=source_stream,
          destination_resource=destination_resource,
          request_config=request_config,
          source_resource=source_resource,
      )

    response = uploader.run()
    return metadata_util.get_object_resource_from_grpc_object(
        response.resource)
