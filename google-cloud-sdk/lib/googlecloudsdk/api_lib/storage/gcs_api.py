# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Client for interacting with Google Cloud Storage.

Implements CloudApi for the GCS JSON API. Example functions include listing
buckets, uploading objects, and setting lifecycle conditions.

TODO(b/160601969): Update class with remaining API methods for ls and cp.
    Note, this class has not been tested against the GCS API yet.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import http_wrapper as apitools_http_wrapper
from apitools.base.py import list_pager
from apitools.base.py import transfer as apitools_transfer

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import errors as cloud_errors
from googlecloudsdk.api_lib.storage import gcs_metadata_util
# pylint: disable=unused-import
# Applies pickling patches:
from googlecloudsdk.api_lib.storage import patch_gcs_messages
# pylint: enable=unused-import
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.calliope import exceptions as calliope_errors
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import tracker_file_util
from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import requests
from googlecloudsdk.core.credentials import transports
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import retry
from googlecloudsdk.core.util import scaled_integer

import oauth2client

DEFAULT_CONTENT_TYPE = 'application/octet-stream'

# Call the progress callback every PROGRESS_CALLBACK_THRESHOLD bytes to
# improve performance.
KB = 1024  # Bytes.
MINIMUM_PROGRESS_CALLBACK_THRESHOLD = 512 * KB
# The API limits the number of objects that can be composed in a single call.
# https://cloud.google.com/storage/docs/json_api/v1/objects/compose
MAX_OBJECTS_PER_COMPOSE_CALL = 32


def _catch_http_error_raise_gcs_api_error(format_str=None):
  """Decorator catches HttpError and returns GcsApiError with custom message.

  Args:
    format_str (str): A googlecloudsdk.api_lib.util.exceptions.HttpErrorPayload
      format string. Note that any properties that are accessed here are on the
      HttpErrorPayload object, not the object returned from the server.

  Returns:
    A decorator that catches apitools.HttpError and returns GcsApiError with a
      customizable error message.
  """
  return cloud_errors.catch_error_raise_cloud_api_error(
      apitools_exceptions.HttpError,
      cloud_errors.GcsApiError,
      format_str=format_str)


def _no_op_callback(unused_response, unused_object):
  """Disables Apitools' default print callbacks."""
  pass


def get_download_serialization_data(object_resource, progress):
  """Generates download serialization data for Apitools.

  Args:
    object_resource (resource_reference.ObjectResource): Used to get metadata.
    progress (int): Represents how much of download is complete.

  Returns:
    JSON string for use with Apitools.
  """
  serialization_dict = {
      'auto_transfer': 'False',  # Apitools JSON API feature not used.
      'progress': progress,
      'total_size': object_resource.size,
      'url': object_resource.metadata.mediaLink,  # HTTP download link.
  }
  return json.dumps(serialization_dict)


class GcsRequestConfig(cloud_api.RequestConfig):
  """Arguments object for requests with custom GCS parameters.

  Attributes:
      gzip_encoded (bool): Whether to use gzip transport encoding for the
          upload.
      max_bytes_per_call (int): Integer describing maximum number of bytes
          to write per service call.
      md5_hash (str): MD5 digest to use for validation.
      precondition_generation_match (int): Perform request only if generation of
          target object matches the given integer. Ignored for bucket requests.
      precondition_metageneration_match (int): Perform request only if
          metageneration of target object/bucket matches the given integer.
      predefined_acl_string (str): Passed to parent class.
      predefined_default_acl_string (str): Passed to parent class.
      size (int): Object size in bytes.
  """

  def __init__(self,
               gzip_encoded=False,
               max_bytes_per_call=None,
               md5_hash=None,
               precondition_generation_match=None,
               precondition_metageneration_match=None,
               predefined_acl_string=None,
               predefined_default_acl_string=None,
               size=None):
    super(GcsRequestConfig, self).__init__(
        md5_hash=md5_hash,
        predefined_acl_string=predefined_acl_string,
        predefined_default_acl_string=predefined_default_acl_string,
        size=size)
    self.gzip_encoded = gzip_encoded
    self.max_bytes_per_call = max_bytes_per_call
    self.precondition_generation_match = precondition_generation_match
    self.precondition_metageneration_match = precondition_metageneration_match

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (super(GcsRequestConfig, self).__eq__(other) and
            self.gzip_encoded == other.gzip_encoded and
            self.max_bytes_per_call == other.max_bytes_per_call and
            self.precondition_generation_match ==
            other.precondition_generation_match and
            self.precondition_metageneration_match ==
            other.precondition_metageneration_match)


class _StorageStreamResponseHandler(requests.ResponseHandler):
  """Handler for writing the streaming response to the download stream."""

  def __init__(self):
    """Initializes response handler for requests downloads."""
    super(_StorageStreamResponseHandler, self).__init__(use_stream=True)
    self._stream = None
    self._digesters = {}
    self._processed_bytes = 0,
    self._progress_callback = None

    self._chunk_size = scaled_integer.ParseInteger(
        properties.VALUES.storage.download_chunk_size.Get())
    # If progress callbacks is called more frequently than every 512 KB, it
    # can degrate performance.
    self._progress_callback_threshold = max(MINIMUM_PROGRESS_CALLBACK_THRESHOLD,
                                            self._chunk_size)

  def update_destination_info(self, stream,
                              digesters=None,
                              processed_bytes=0,
                              progress_callback=None):
    """Updates the stream handler with destination information.

    The download_http_client object is stored on the gcs_api object. This allows
    resusing the same http_client when the gcs_api is cached using
    threading.local, which improves performance.
    Since this same object gets used for mutliple downloads, we need to update
    the stream handler with the current active download's destination.

    Args:
      stream (stream): Local stream to write downloaded data to.
      digesters (dict<HashAlgorithm, hashlib object> | None): For updating hash
        digests of downloaded objects on the fly.
      processed_bytes (int): For keeping track of how much progress has been
        made.
      progress_callback (func<int>): Accepts processed_bytes and submits
        progress info for aggregation.
    """
    self._stream = stream
    self._digesters = digesters if digesters is not None else {}
    self._processed_bytes = processed_bytes
    self._progress_callback = progress_callback

  def handle(self, source_stream):
    if self._stream is None:
      raise ValueError('Stream was not found.')

    # Start reading the raw stream.
    bytes_since_last_progress_callback = 0
    while True:
      data = source_stream.read(self._chunk_size)
      if data:
        self._stream.write(data)
        self._processed_bytes += len(data)
        bytes_since_last_progress_callback += len(data)
        if (self._progress_callback and bytes_since_last_progress_callback >=
            self._progress_callback_threshold):
          self._progress_callback(self._processed_bytes)
          bytes_since_last_progress_callback = (
              bytes_since_last_progress_callback -
              self._progress_callback_threshold)
      else:
        if self._progress_callback and bytes_since_last_progress_callback:
          # Make a last progress callback call to update the final size.
          self._progress_callback(self._processed_bytes)
        break
      for hash_object in self._digesters.values():
        hash_object.update(data)


class GcsApi(cloud_api.CloudApi):
  """Client for Google Cloud Storage API."""

  def __init__(self):
    self.client = core_apis.GetClientInstance('storage', 'v1')
    self.client.overwrite_transfer_urls_with_client_base = True
    self.messages = core_apis.GetMessagesModule('storage', 'v1')
    self._stream_response_handler = _StorageStreamResponseHandler()
    self._download_http_client = None
    self._upload_http_client = None

  def _get_projection(self, fields_scope, message_class):
    """Generate query projection from fields_scope.

    Args:
      fields_scope (FieldsScope): Used to determine projection to return.
      message_class (object): Apitools message object that contains a projection
          enum.

    Returns:
      projection (ProjectionValueValuesEnum): Determines if ACL properties
          should be returned.

    Raises:
      ValueError: The fields_scope isn't recognized.
    """
    if fields_scope not in cloud_api.FieldsScope:
      raise ValueError('Invalid fields_scope.')
    projection_enum = message_class.ProjectionValueValuesEnum

    if fields_scope == cloud_api.FieldsScope.FULL:
      return projection_enum.full
    return projection_enum.noAcl

  @_catch_http_error_raise_gcs_api_error()
  def create_bucket(self,
                    bucket_resource,
                    fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""
    projection = self._get_projection(fields_scope,
                                      self.messages.StorageBucketsInsertRequest)
    if not bucket_resource.metadata:
      bucket_resource.metadata = gcs_metadata_util.get_metadata_from_bucket_resource(
          bucket_resource)

    request = self.messages.StorageBucketsInsertRequest(
        bucket=bucket_resource.metadata,
        project=properties.VALUES.core.project.GetOrFail(),
        projection=projection)

    created_bucket_metadata = self.client.buckets.Insert(request)
    return gcs_metadata_util.get_bucket_resource_from_metadata(
        created_bucket_metadata)

  @_catch_http_error_raise_gcs_api_error()
  def delete_bucket(self, bucket_name, request_config=None):
    """See super class."""
    if not request_config:
      request_config = GcsRequestConfig()
    request = self.messages.StorageBucketsDeleteRequest(
        bucket=bucket_name,
        ifMetagenerationMatch=request_config.precondition_metageneration_match)
    # Success returns an empty body.
    # https://cloud.google.com/storage/docs/json_api/v1/buckets/delete
    self.client.buckets.Delete(request)

  @_catch_http_error_raise_gcs_api_error()
  def get_bucket(self, bucket_name, fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""
    projection = self._get_projection(fields_scope,
                                      self.messages.StorageBucketsGetRequest)
    request = self.messages.StorageBucketsGetRequest(
        bucket=bucket_name,
        projection=projection)

    metadata = self.client.buckets.Get(request)
    return gcs_metadata_util.get_bucket_resource_from_metadata(metadata)

  @_catch_http_error_raise_gcs_api_error()
  def patch_bucket(self,
                   bucket_resource,
                   request_config=None,
                   fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""
    validated_request_config = cloud_api.get_provider_request_config(
        request_config, GcsRequestConfig)

    projection = self._get_projection(fields_scope,
                                      self.messages.StorageBucketsPatchRequest)
    metadata = (
        bucket_resource.metadata or
        gcs_metadata_util.get_metadata_from_bucket_resource(bucket_resource))

    # Blank metadata objects need to be explicitly emptied.
    apitools_include_fields = []
    for metadata_field in (
        'billing',
        'encryption',
        'lifecycle',
        'logging',
        'retentionPolicy',
        'versioning',
        'website',
    ):
      attr = getattr(metadata, metadata_field, None)
      if attr and not encoding.MessageToDict(attr):
        apitools_include_fields.append(metadata_field)
        setattr(metadata, metadata_field, None)

    # Handle nulling lists with sentinel values.
    if metadata.cors and metadata.cors == gcs_metadata_util.REMOVE_CORS_CONFIG:
      apitools_include_fields.append('cors')
      metadata.cors = []
    if (metadata.defaultObjectAcl and metadata.defaultObjectAcl[0]
        == gcs_metadata_util.PRIVATE_DEFAULT_OBJECT_ACL):
      apitools_include_fields.append('defaultObjectAcl')
      metadata.defaultObjectAcl = []

    # Must null out existing ACLs to apply new ones.
    if validated_request_config.predefined_acl_string:
      apitools_include_fields.append('acl')
      predefined_acl = getattr(
          self.messages.StorageBucketsPatchRequest.PredefinedAclValueValuesEnum,
          validated_request_config.predefined_acl_string)
    else:
      predefined_acl = None
    if validated_request_config.predefined_default_acl_string:
      apitools_include_fields.append('defaultObjectAcl')
      predefined_default_acl = getattr(
          self.messages.StorageBucketsPatchRequest
          .PredefinedDefaultObjectAclValueValuesEnum,
          validated_request_config.predefined_default_acl_string)
    else:
      predefined_default_acl = None

    apitools_request = self.messages.StorageBucketsPatchRequest(
        bucket=bucket_resource.name,
        bucketResource=metadata,
        projection=projection,
        ifMetagenerationMatch=validated_request_config
        .precondition_metageneration_match,
        predefinedAcl=predefined_acl,
        predefinedDefaultObjectAcl=predefined_default_acl)

    with self.client.IncludeFields(apitools_include_fields):
      return gcs_metadata_util.get_bucket_resource_from_metadata(
          self.client.buckets.Patch(apitools_request))

  def list_buckets(self, fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""
    projection = self._get_projection(fields_scope,
                                      self.messages.StorageBucketsListRequest)
    request = self.messages.StorageBucketsListRequest(
        project=properties.VALUES.core.project.GetOrFail(),
        projection=projection)

    global_params = None
    if fields_scope == cloud_api.FieldsScope.SHORT:
      global_params = self.messages.StandardQueryParameters()
      global_params.fields = 'items/name'
    # TODO(b/160238394) Decrypt metadata fields if necessary.
    bucket_iter = list_pager.YieldFromList(
        self.client.buckets,
        request,
        batch_size=cloud_api.NUM_ITEMS_PER_LIST_PAGE,
        global_params=global_params)
    try:
      for bucket in bucket_iter:
        yield gcs_metadata_util.get_bucket_resource_from_metadata(bucket)
    except apitools_exceptions.HttpError as error:
      core_exceptions.reraise(cloud_errors.GcsApiError(error))

  def list_objects(self,
                   bucket_name,
                   prefix=None,
                   delimiter=None,
                   all_versions=None,
                   fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""
    projection = self._get_projection(fields_scope,
                                      self.messages.StorageObjectsListRequest)
    global_params = None
    if fields_scope == cloud_api.FieldsScope.SHORT:
      global_params = self.messages.StandardQueryParameters()
      global_params.fields = (
          'prefixes,items/name,items/size,items/generation,nextPageToken')

    object_list = None
    while True:
      apitools_request = self.messages.StorageObjectsListRequest(
          bucket=bucket_name,
          prefix=prefix,
          delimiter=delimiter,
          versions=all_versions,
          projection=projection,
          pageToken=object_list.nextPageToken if object_list else None,
          maxResults=cloud_api.NUM_ITEMS_PER_LIST_PAGE)

      try:
        object_list = self.client.objects.List(
            apitools_request, global_params=global_params)
      except apitools_exceptions.HttpError as error:
        core_exceptions.reraise(cloud_errors.GcsApiError(error))

      # Yield objects.
      # TODO(b/160238394) Decrypt metadata fields if necessary.
      for object_metadata in object_list.items:
        object_metadata.bucket = bucket_name
        yield gcs_metadata_util.get_object_resource_from_metadata(
            object_metadata)

      # Yield prefixes.
      for prefix_string in object_list.prefixes:
        yield resource_reference.PrefixResource(
            storage_url.CloudUrl(
                scheme=storage_url.ProviderPrefix.GCS,
                bucket_name=bucket_name,
                object_name=prefix_string),
            prefix=prefix_string
        )

      if not object_list.nextPageToken:
        break

  @_catch_http_error_raise_gcs_api_error()
  def delete_object(self, object_url, request_config=None):
    """See super class."""
    if not request_config:
      request_config = GcsRequestConfig()

    # S3 requires a string, but GCS uses an int for generation.
    if object_url.generation is not None:
      generation = int(object_url.generation)
    else:
      generation = None

    request = self.messages.StorageObjectsDeleteRequest(
        bucket=object_url.bucket_name,
        object=object_url.object_name,
        generation=generation,
        ifGenerationMatch=request_config.precondition_generation_match,
        ifMetagenerationMatch=request_config.precondition_metageneration_match)
    # Success returns an empty body.
    # https://cloud.google.com/storage/docs/json_api/v1/objects/delete
    self.client.objects.Delete(request)

  @_catch_http_error_raise_gcs_api_error()
  def get_object_metadata(self,
                          bucket_name,
                          object_name,
                          generation=None,
                          fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""

    # S3 requires a string, but GCS uses an int for generation.
    if generation:
      generation = int(generation)

    projection = self._get_projection(fields_scope,
                                      self.messages.StorageObjectsGetRequest)

    # TODO(b/160238394) Decrypt metadata fields if necessary.
    try:
      object_metadata = self.client.objects.Get(
          self.messages.StorageObjectsGetRequest(
              bucket=bucket_name,
              object=object_name,
              generation=generation,
              projection=projection))
    except apitools_exceptions.HttpNotFoundError:
      raise cloud_errors.NotFoundError(
          'Object not found: {}'.format(storage_url.CloudUrl(
              storage_url.ProviderPrefix.GCS, bucket_name, object_name,
              generation).url_string)
      )
    return gcs_metadata_util.get_object_resource_from_metadata(object_metadata)

  @_catch_http_error_raise_gcs_api_error()
  def patch_object_metadata(self,
                            bucket_name,
                            object_name,
                            object_resource,
                            fields_scope=cloud_api.FieldsScope.NO_ACL,
                            generation=None,
                            request_config=None):
    """See super class."""
    # S3 requires a string, but GCS uses an int for generation.
    if generation:
      generation = int(generation)

    if not request_config:
      request_config = GcsRequestConfig()

    predefined_acl = None
    if request_config.predefined_acl_string:
      predefined_acl = getattr(self.messages.StorageObjectsPatchRequest.
                               PredefinedAclValueValuesEnum,
                               request_config.predefined_acl_string)

    projection = self._get_projection(fields_scope,
                                      self.messages.StorageObjectsPatchRequest)

    # Assume parameters are only for identifying what needs to be patched, and
    # the resource contains the desired patched metadata values.
    patched_metadata = object_resource.metadata
    if not patched_metadata:
      object_resource.metadata = gcs_metadata_util.get_apitools_metadata_from_url(
          object_resource.storage_url)

    request = self.messages.StorageObjectsPatchRequest(
        bucket=bucket_name,
        object=object_name,
        objectResource=object_resource.metadata,
        generation=generation,
        ifGenerationMatch=request_config.precondition_generation_match,
        ifMetagenerationMatch=request_config.precondition_metageneration_match,
        predefinedAcl=predefined_acl,
        projection=projection)

    updated_metadata = self.client.objects.Patch(request)
    return gcs_metadata_util.get_object_resource_from_metadata(updated_metadata)

  @_catch_http_error_raise_gcs_api_error()
  def copy_object(self,
                  source_resource,
                  destination_resource,
                  progress_callback=None,
                  request_config=None):
    """See super class."""
    # TODO(b/161898251): Implement encryption and decryption.
    if not request_config:
      request_config = GcsRequestConfig()

    destination_metadata = getattr(destination_resource, 'metadata', None)
    if not destination_metadata:
      destination_metadata = gcs_metadata_util.get_apitools_metadata_from_url(
          destination_resource.storage_url)
      if source_resource.metadata:
        gcs_metadata_util.copy_select_object_metadata(source_resource.metadata,
                                                      destination_metadata)

    if request_config.max_bytes_per_call:
      max_bytes_per_call = request_config.max_bytes_per_call
    else:
      max_bytes_per_call = scaled_integer.ParseInteger(
          properties.VALUES.storage.copy_chunk_size.Get())

    if request_config.predefined_acl_string:
      predefined_acl = getattr(
          self.messages.StorageObjectsRewriteRequest
          .DestinationPredefinedAclValueValuesEnum,
          request_config.predefined_acl_string)
    else:
      predefined_acl = None

    if source_resource.generation is None:
      source_generation = None
    else:
      source_generation = int(source_resource.generation)

    tracker_file_path = tracker_file_util.get_tracker_file_path(
        destination_resource.storage_url,
        tracker_file_util.TrackerFileType.REWRITE, source_resource.storage_url)
    rewrite_parameters_hash = tracker_file_util.hash_gcs_rewrite_parameters_for_tracker_file(
        source_resource,
        destination_resource,
        destination_metadata,
        request_config=request_config)
    try:
      resume_rewrite_token = tracker_file_util.read_rewrite_tracker_file(
          tracker_file_path, rewrite_parameters_hash)
      log.debug('Found rewrite token. Resuming copy.')
    except files.MissingFileError:
      resume_rewrite_token = None
      log.debug('No rewrite token found. Starting copy from scratch.')

    while True:
      request = self.messages.StorageObjectsRewriteRequest(
          sourceBucket=source_resource.storage_url.bucket_name,
          sourceObject=source_resource.storage_url.object_name,
          destinationBucket=destination_resource.storage_url.bucket_name,
          destinationObject=destination_resource.storage_url.object_name,
          object=destination_metadata,
          sourceGeneration=source_generation,
          ifGenerationMatch=request_config.precondition_generation_match,
          ifMetagenerationMatch=(
              request_config.precondition_metageneration_match),
          destinationPredefinedAcl=predefined_acl,
          rewriteToken=resume_rewrite_token,
          maxBytesRewrittenPerCall=max_bytes_per_call)
      rewrite_response = self.client.objects.Rewrite(request)
      processed_bytes = rewrite_response.totalBytesRewritten
      if progress_callback:
        progress_callback(processed_bytes)

      if rewrite_response.done:
        break
      elif not resume_rewrite_token:
        resume_rewrite_token = rewrite_response.rewriteToken
        tracker_file_util.write_rewrite_tracker_file(
            tracker_file_path, rewrite_parameters_hash,
            rewrite_response.rewriteToken)

    tracker_file_util.delete_tracker_file(tracker_file_path)
    return gcs_metadata_util.get_object_resource_from_metadata(
        rewrite_response.resource)

  # pylint: disable=unused-argument
  def _download_object(self,
                       cloud_resource,
                       download_stream,
                       apitools_download,
                       apitools_request,
                       compressed_encoding=False,
                       decryption_wrapper=None,
                       generation=None,
                       serialization_data=None,
                       start_byte=0,
                       end_byte=None):
    """GCS-specific download implementation.

    Args:
      cloud_resource (resource_reference.ObjectResource): Contains
          metadata and information about object being downloaded.
      download_stream (stream): Stream to send the object data to.
      apitools_download (apitools.transfer.Download): Apitools object for
          managing downloads.
      apitools_request (apitools.messages.StorageObjectsGetReqest):
          Holds call to GCS API.
      compressed_encoding (bool): If true, object is stored with a compressed
          encoding.
      decryption_wrapper (CryptoKeyWrapper):
          utils.encryption_helper.CryptoKeyWrapper that can optionally be added
          to decrypt an encrypted object.
      generation (int): Generation of the object to retrieve.
      serialization_data (str): Implementation-specific JSON string of a dict
          containing serialization information for the download.
      start_byte (int): Starting point for download (for resumable downloads and
          range requests). Can be set to negative to request a range of bytes
          (python equivalent of [:-3]).
      end_byte (int): Ending byte number, inclusive, for download (for range
          requests). If None, download the rest of the object.

    Returns:
      Encoding string for object if requested. Otherwise, None.
    """
    # Fresh download.
    if not serialization_data:
      self.client.objects.Get(apitools_request, download=apitools_download)

    # TODO(b/161453101): Optimize handling of gzip-encoded downloads.
    additional_headers = {}
    if compressed_encoding:
      additional_headers['accept-encoding'] = 'gzip'

    # TODO(b/161437904): Add decryption handling.

    if start_byte or end_byte is not None:
      apitools_download.GetRange(
          additional_headers=additional_headers,
          start=start_byte,
          end=end_byte,
          use_chunks=False)
    else:
      apitools_download.StreamMedia(
          additional_headers=additional_headers,
          callback=_no_op_callback,
          finish_callback=_no_op_callback,
          use_chunks=False)
    return apitools_download.encoding

  def _download_object_resumable(self,
                                 cloud_resource,
                                 download_stream,
                                 apitools_download,
                                 apitools_request,
                                 compressed_encoding=False,
                                 decryption_wrapper=None,
                                 generation=None,
                                 serialization_data=None,
                                 start_byte=0,
                                 end_byte=None):
    """Wraps _download_object to make it retriable."""
    # Hack because nonlocal keyword causes Python 2 syntax error.
    progress_state = {'last_byte_processed': start_byte}

    def _should_retry_resumable_download(exc_type, exc_value, exc_traceback,
                                         state):
      converted_error, _ = calliope_errors.ConvertKnownError(exc_value)
      if isinstance(exc_value, oauth2client.client.HttpAccessTokenRefreshError):
        if exc_value.status < 500 and exc_value.status != 429:
          # Not server error or too many requests error.
          return False
      elif not isinstance(converted_error, core_exceptions.NetworkIssueError):
        # Not known transient network error.
        return False

      start_byte = download_stream.tell()
      if start_byte > progress_state['last_byte_processed']:
        # We've made progress, so allow a fresh set of retries.
        progress_state['last_byte_processed'] = start_byte
        state.retrial = 0
      log.debug('Retrying download from byte {} after exception: {}.'
                ' Trace: {}'.format(start_byte, exc_type, exc_traceback))

      apitools_http_wrapper.RebuildHttpConnections(apitools_download.bytes_http)
      return True

    def _call_download_object():
      return self._download_object(
          cloud_resource,
          download_stream,
          apitools_download,
          apitools_request,
          compressed_encoding=compressed_encoding,
          decryption_wrapper=decryption_wrapper,
          generation=generation,
          serialization_data=serialization_data,
          start_byte=start_byte,
          end_byte=end_byte)

    return retry.RetryOnException(
        _call_download_object,
        max_retrials=properties.VALUES.storage.max_retries.GetInt(),
        # Convert seconds to miliseconds.
        max_wait_ms=properties.VALUES.storage.max_retry_delay.GetInt() * 1000,
        should_retry_if=_should_retry_resumable_download)()

  @_catch_http_error_raise_gcs_api_error()
  def download_object(self,
                      cloud_resource,
                      download_stream,
                      compressed_encoding=False,
                      decryption_wrapper=None,
                      digesters=None,
                      download_strategy=cloud_api.DownloadStrategy.RESUMABLE,
                      progress_callback=None,
                      start_byte=0,
                      end_byte=None):
    """See super class."""
    # S3 requires a string, but GCS uses an int for generation.
    generation = (
        int(cloud_resource.generation) if cloud_resource.generation else None)

    if start_byte and download_strategy == cloud_api.DownloadStrategy.RESUMABLE:
      # Resuming download.
      serialization_data = get_download_serialization_data(
          cloud_resource, start_byte)
      apitools_download = apitools_transfer.Download.FromData(
          download_stream,
          serialization_data,
          num_retries=properties.VALUES.storage.max_retries.GetInt(),
          client=self.client)
    else:
      # New download.
      serialization_data = None
      apitools_download = apitools_transfer.Download.FromStream(
          download_stream,
          auto_transfer=False,
          total_size=cloud_resource.size,
          num_retries=properties.VALUES.storage.max_retries.GetInt())

    self._stream_response_handler.update_destination_info(
        stream=download_stream,
        digesters=digesters,
        processed_bytes=start_byte,
        progress_callback=progress_callback)

    if self._download_http_client is None:
      self._download_http_client = transports.GetApitoolsTransport(
          response_encoding=None,
          response_handler=self._stream_response_handler)
    apitools_download.bytes_http = self._download_http_client

    # TODO(b/161460749) Handle download retries.
    request = self.messages.StorageObjectsGetRequest(
        bucket=cloud_resource.bucket,
        object=cloud_resource.name,
        generation=generation)

    if download_strategy == cloud_api.DownloadStrategy.ONE_SHOT:
      return self._download_object(
          cloud_resource,
          download_stream,
          apitools_download,
          request,
          compressed_encoding=compressed_encoding,
          decryption_wrapper=decryption_wrapper,
          generation=generation,
          serialization_data=serialization_data,
          start_byte=start_byte,
          end_byte=end_byte)
    else:
      return self._download_object_resumable(
          cloud_resource,
          download_stream,
          apitools_download,
          request,
          compressed_encoding=compressed_encoding,
          decryption_wrapper=decryption_wrapper,
          generation=generation,
          serialization_data=serialization_data,
          start_byte=start_byte,
          end_byte=end_byte)

  # pylint: disable=unused-argument
  def _upload_object(self,
                     source_stream,
                     object_metadata,
                     request_config,
                     apitools_strategy=apitools_transfer.SIMPLE_UPLOAD,
                     progress_callback=None,
                     serialization_data=None,
                     tracker_callback=None):
    # pylint: disable=g-doc-args
    """GCS-specific upload implementation. Adds args to Cloud API interface.

    Additional args:
      object_metadata (messages.Object): Apitools metadata for object to
          upload.
      apitools_strategy (str): SIMPLE_UPLOAD or RESUMABLE_UPLOAD constant in
          apitools.base.py.transfer.
      serialization_data (str): Implementation-specific JSON string of a dict
          containing serialization information for the download.
      tracker_callback (function): Callback that keeps track of upload progress.

    Returns:
      Uploaded object metadata in an ObjectResource.

    Raises:
      ValueError if an object can't be uploaded with the provided metadata.
    """
    predefined_acl = None
    if request_config.predefined_acl_string:
      predefined_acl = getattr(self.messages.StorageObjectsInsertRequest.
                               PredefinedAclValueValuesEnum,
                               request_config.predefined_acl_string)

    # TODO(b/160998052): Use encryption_wrapper to generate encryption headers.

    # Fresh upload. Prepare arguments.
    if not serialization_data:
      content_type = object_metadata.contentType

      if not content_type:
        content_type = DEFAULT_CONTENT_TYPE

      request = self.messages.StorageObjectsInsertRequest(
          bucket=object_metadata.bucket,
          object=object_metadata,
          ifGenerationMatch=request_config.precondition_generation_match,
          ifMetagenerationMatch=(
              request_config.precondition_metageneration_match),
          predefinedAcl=predefined_acl)

    if apitools_strategy == apitools_transfer.SIMPLE_UPLOAD:
      apitools_upload = apitools_transfer.Upload(
          source_stream,
          content_type,
          auto_transfer=True,
          chunksize=scaled_integer.ParseInteger(
              properties.VALUES.storage.upload_chunk_size.Get()),
          gzip_encoded=request_config.gzip_encoded,
          num_retries=properties.VALUES.storage.max_retries.GetInt(),
          progress_callback=progress_callback,
          total_size=request_config.size)

      if self._upload_http_client is None:
        self._upload_http_client = transports.GetApitoolsTransport()
      apitools_upload.bytes_http = self._upload_http_client

      result_object_metadata = self.client.objects.Insert(
          request, upload=apitools_upload)

      return gcs_metadata_util.get_object_resource_from_metadata(
          result_object_metadata)
    else:
      # TODO(b/160998556): Implement resumable upload.
      pass

  @_catch_http_error_raise_gcs_api_error()
  def upload_object(self,
                    source_stream,
                    destination_resource,
                    progress_callback=None,
                    request_config=None):
    """See CloudApi class for function doc strings."""
    if progress_callback:
      # Apitools uploads pass response objects to callbacks. Parse these
      # because our callbacks only expect an int "processed_bytes".
      def wrapped_progress_callback(response, message_string):
        del message_string  # Unused.
        # Range field format: "bytes=0-138989".
        _, range_values_string = response.info['range'].split('=')
        start_byte, end_byte = [int(x) for x in range_values_string.split('-')]
        processed_bytes = end_byte - start_byte
        progress_callback(processed_bytes)
    else:
      wrapped_progress_callback = None

    if request_config.size is None:
      # Size is required so that apitools_transfer can pick the
      # optimal upload strategy.
      raise cloud_errors.GcsApiError(
          'Upload failed due to missing size. Destination: {}'.format(
              destination_resource.storage_url.url_string))

    validated_request_config = cloud_api.get_provider_request_config(
        request_config, GcsRequestConfig)

    object_metadata = self.messages.Object(
        name=destination_resource.storage_url.object_name,
        bucket=destination_resource.storage_url.bucket_name,
        md5Hash=validated_request_config.md5_hash)

    upload_result = self._upload_object(
        source_stream,
        object_metadata,
        apitools_strategy=apitools_transfer.SIMPLE_UPLOAD,
        progress_callback=wrapped_progress_callback,
        request_config=validated_request_config,
        serialization_data=None)

    if progress_callback:
      # Apitools does not always run the callback at the end of an upload.
      progress_callback(request_config.size)

    return upload_result

  @_catch_http_error_raise_gcs_api_error()
  def compose_objects(self,
                      source_resources,
                      destination_resource,
                      request_config=None):
    """See CloudApi class for function doc strings."""

    if not source_resources:
      raise cloud_errors.GcsApiError(
          'Compose requires at least one component object.')

    if len(source_resources) > MAX_OBJECTS_PER_COMPOSE_CALL:
      raise cloud_errors.GcsApiError(
          'Compose was called with {} objects. The limit is {}.'.format(
              len(source_resources), MAX_OBJECTS_PER_COMPOSE_CALL))

    validated_request_config = cloud_api.get_provider_request_config(
        request_config, GcsRequestConfig)

    source_messages = []
    for source in source_resources:
      source_message = self.messages.ComposeRequest.SourceObjectsValueListEntry(
          name=source.storage_url.object_name)
      if source.storage_url.generation is not None:
        generation = int(source.storage_url.generation)
        source_message.generation = generation
      source_messages.append(source_message)

    compose_request_payload = self.messages.ComposeRequest(
        sourceObjects=source_messages,
        destination=gcs_metadata_util.get_apitools_metadata_from_url(
            destination_resource.storage_url))

    compose_request = self.messages.StorageObjectsComposeRequest(
        composeRequest=compose_request_payload,
        destinationBucket=destination_resource.storage_url.bucket_name,
        destinationObject=destination_resource.storage_url.object_name,
        ifGenerationMatch=(
            validated_request_config.precondition_generation_match),
        ifMetagenerationMatch=(
            validated_request_config.precondition_metageneration_match),
    )

    if validated_request_config.predefined_acl_string is not None:
      compose_request.destinationPredefinedAcl = getattr(
          self.messages.StorageObjectsComposeRequest.
          DestinationPredefinedAclValueValuesEnum,
          request_config.predefined_acl_string)

    return gcs_metadata_util.get_object_resource_from_metadata(
        self.client.objects.Compose(compose_request))
