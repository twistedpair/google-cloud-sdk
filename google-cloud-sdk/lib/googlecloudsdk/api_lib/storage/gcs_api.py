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

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import list_pager
from apitools.base.py import transfer as apitools_transfer

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import errors as cloud_errors
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.command_lib.storage import resource_reference
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core.credentials import transports


DEFAULT_CONTENT_TYPE = 'application/octet-stream'
# TODO(b/161346648) Retrieve number of retries from Boto config file.
DEFAULT_NUM_RETRIES = 23


 # TODO(b/167691513): Replace all BucketResource.from_gcs_metadata_object
 # instances with this.
def _BucketResourceFromMetadata(metadata):
  """Helper method to generate the Bucket instance from GCS metadata.

  Args:
    metadata (messages.Bucket): Extract resource properties from this.

  Returns:
    BucketResource with properties populated by metadata.
  """
  url = storage_url.CloudUrl(scheme=cloud_api.ProviderPrefix.GCS.value,
                             bucket_name=metadata.name)
  return resource_reference.BucketResource(
      url, metadata.name, metadata.etag, metadata)


# Disable Apitools' default print callbacks.
def _NoOpCallback(unused_response, unused_object):
  pass


def _ValidateObjectMetadata(metadata):
  """Ensures metadata supplies the needed fields for copy and insert.

  Args:
    metadata (apitools.messages.Object): Apitools Object metadata to validate.

  Raises:
    ValueError: Metadata is invalid.
  """
  if not metadata:
    raise ValueError(
        'No object metadata supplied for object.')
  if not metadata.name:
    raise ValueError(
        'Object metadata supplied for object had no object name.')
  if not metadata.bucket:
    raise ValueError(
        'Object metadata supplied for object had no bucket name.')


class GcsRequestConfig(cloud_api.RequestConfig):
  """Arguments object for requests with custom GCS parameters.

  Attributes:
      decryption_wrapper (CryptoKeyWrapper):
          utils.encryption_helper.CryptoKeyWrapper for decrypting an object.
      encryption_wrapper (CryptoKeyWrapper):
          utils.encryption_helper.CryptoKeyWrapper for encrypting an object.
      gzip_encoded (bool): Whether to use gzip transport encoding for the
          upload.
      max_bytes_per_call (int): Integer describing maximum number of bytes
          to write per service call.
      precondition_generation_match (int): Perform request only if generation of
          target object matches the given integer. Ignored for bucket requests.
      precondition_metageneration_match (int): Perform request only if
          metageneration of target object/bucket matches the given integer.
      predefined_acl_string (str): Passed to parent class.
      size (int): Object size in bytes.
  """

  def __init__(self,
               decryption_wrapper=None,
               encryption_wrapper=None,
               gzip_encoded=False,
               max_bytes_per_call=None,
               precondition_generation_match=None,
               precondition_metageneration_match=None,
               predefined_acl_string=None,
               size=None):
    super(GcsRequestConfig, self).__init__(
        predefined_acl_string=predefined_acl_string)
    self.decryption_wrapper = decryption_wrapper
    self.encryption_wrapper = encryption_wrapper
    self.gzip_encoded = gzip_encoded
    self.max_bytes_per_call = max_bytes_per_call
    self.precondition_generation_match = precondition_generation_match
    self.precondition_metageneration_match = precondition_metageneration_match
    self.size = size


class GcsApi(cloud_api.CloudApi):
  """Client for Google Cloud Storage API."""

  def __init__(self):
    self.client = core_apis.GetClientInstance('storage', 'v1')
    self.messages = core_apis.GetMessagesModule('storage', 'v1')

  def _GetGlobalParamsAndProjection(self, fields_scope, message_class):
    """Generate query projection and fields from fields_scope.

    Args:
      fields_scope (FieldsScope): Used to determine projection and fields to
          return.
      message_class (object): Apitools message object that contains a projection
          enum.

    Returns:
      global_params (object): API query parameters used across calls.
      projection (ProjectionValueValuesEnum): Determines if ACL properties
          should be returned.

    Raises:
      ValueError: The fields_scope isn't recognized.
    """
    if fields_scope not in cloud_api.FieldsScope:
      raise ValueError('Invalid fields_scope.')
    projection_enum = message_class.ProjectionValueValuesEnum

    global_params = self.messages.StandardQueryParameters()
    projection = None

    if fields_scope == cloud_api.FieldsScope.SHORT:
      global_params.fields = ','.join(['name', 'size'])
      projection = projection_enum.noAcl
    elif fields_scope == cloud_api.FieldsScope.NO_ACL:
      projection = projection_enum.noAcl
    elif fields_scope == cloud_api.FieldsScope.FULL:
      projection = projection_enum.full

    return (global_params, projection)

  @cloud_errors.catch_http_error_raise_gcs_api_error()
  def CreateBucket(self,
                   metadata,
                   fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""
    global_params, projection = self._GetGlobalParamsAndProjection(
        fields_scope, self.messages.StorageBucketsInsertRequest)

    request = self.messages.StorageBucketsInsertRequest(
        bucket=metadata,
        project=properties.VALUES.core.project.GetOrFail(),
        projection=projection)

    created_bucket_metadata = self.client.buckets.Insert(
        request, global_params=global_params)
    return _BucketResourceFromMetadata(created_bucket_metadata)

  @cloud_errors.catch_http_error_raise_gcs_api_error()
  def DeleteBucket(self,
                   bucket_name,
                   request_config=None):
    """See super class."""
    if not request_config:
      request_config = GcsRequestConfig()
    request = self.messages.StorageBucketsDeleteRequest(
        bucket=bucket_name,
        ifMetagenerationMatch=request_config.precondition_metageneration_match)
    # Success returns an empty body.
    # https://cloud.google.com/storage/docs/json_api/v1/buckets/delete
    self.client.buckets.Delete(request)

  @cloud_errors.catch_http_error_raise_gcs_api_error()
  def GetBucket(self, bucket_name, fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""
    global_params, projection = self._GetGlobalParamsAndProjection(
        fields_scope, self.messages.StorageBucketsGetRequest)
    request = self.messages.StorageBucketsGetRequest(
        bucket=bucket_name,
        projection=projection)

    metadata = self.client.buckets.Get(request, global_params=global_params)
    return _BucketResourceFromMetadata(metadata)

  def ListBuckets(self, fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""
    global_params, projection = self._GetGlobalParamsAndProjection(
        fields_scope, self.messages.StorageBucketsListRequest)
    request = self.messages.StorageBucketsListRequest(
        project=properties.VALUES.core.project.GetOrFail(),
        projection=projection)

    # TODO(b/160238394) Decrypt metadata fields if necessary.
    bucket_iter = list_pager.YieldFromList(
        self.client.buckets,
        request,
        batch_size=cloud_api.NUM_ITEMS_PER_LIST_PAGE,
        global_params=global_params)
    try:
      for bucket in bucket_iter:
        yield _BucketResourceFromMetadata(bucket)
    except apitools_exceptions.HttpError as error:
      core_exceptions.reraise(cloud_errors.GcsApiError(error))

  def ListObjects(self,
                  bucket_name,
                  prefix=None,
                  delimiter=None,
                  all_versions=None,
                  fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""
    global_params, projection = self._GetGlobalParamsAndProjection(
        fields_scope, self.messages.StorageObjectsListRequest)

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
      for obj in object_list.items:
        yield resource_reference.ObjectResource.from_gcs_metadata_object(
            provider=cloud_api.ProviderPrefix.GCS.value,
            metadata_object=obj
        )

      # Yield prefixes.
      for prefix_string in object_list.prefixes:
        yield resource_reference.PrefixResource(
            storage_url=storage_url.CloudUrl(
                scheme=cloud_api.ProviderPrefix.GCS.value,
                bucket_name=bucket_name,
                object_name=prefix_string
            ),
            prefix=prefix_string
        )

      if not object_list.nextPageToken:
        break

  @cloud_errors.catch_http_error_raise_gcs_api_error()
  def DeleteObject(self,
                   bucket_name,
                   object_name,
                   generation=None,
                   request_config=None):
    """See super class."""
    if not request_config:
      request_config = GcsRequestConfig()

    request = self.messages.StorageObjectsDeleteRequest(
        bucket=bucket_name,
        object=object_name,
        generation=generation,
        ifGenerationMatch=request_config.precondition_generation_match,
        ifMetagenerationMatch=request_config.precondition_metageneration_match)
    # Success returns an empty body.
    # https://cloud.google.com/storage/docs/json_api/v1/objects/delete
    self.client.objects.Delete(request)

  @cloud_errors.catch_http_error_raise_gcs_api_error()
  def GetObjectMetadata(self,
                        bucket_name,
                        object_name,
                        generation=None,
                        fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""

    # S3 requires a string, but GCS uses an int for generation.
    if generation:
      generation = int(generation)

    global_params, projection = self._GetGlobalParamsAndProjection(
        fields_scope, self.messages.StorageObjectsGetRequest)

    # TODO(b/160238394) Decrypt metadata fields if necessary.
    try:
      object_metadata = self.client.objects.Get(
          self.messages.StorageObjectsGetRequest(
              bucket=bucket_name,
              object=object_name,
              generation=generation,
              projection=projection),
          global_params=global_params)
    except apitools_exceptions.HttpNotFoundError:
      raise cloud_errors.NotFoundError(
          'Object not found: {}'.format(storage_url.CloudUrl(
              'gs', bucket_name, object_name, generation).url_string)
      )
    return resource_reference.ObjectResource.from_gcs_metadata_object(
        cloud_api.ProviderPrefix.GCS.value, object_metadata)

  @cloud_errors.catch_http_error_raise_gcs_api_error()
  def PatchObjectMetadata(self,
                          bucket_name,
                          object_name,
                          metadata,
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

    global_params, projection = self._GetGlobalParamsAndProjection(
        fields_scope, self.messages.StorageObjectsPatchRequest)

    request = self.messages.StorageObjectsPatchRequest(
        bucket=bucket_name,
        object=object_name,
        objectResource=metadata,
        generation=generation,
        ifGenerationMatch=request_config.precondition_generation_match,
        ifMetagenerationMatch=request_config.precondition_metageneration_match,
        predefinedAcl=predefined_acl,
        projection=projection
    )

    object_metadata = self.client.objects.Patch(request,
                                                global_params=global_params)
    return resource_reference.ObjectResource.from_gcs_metadata_object(
        cloud_api.ProviderPrefix.GCS.value, object_metadata)

  # pylint: disable=unused-argument
  @cloud_errors.catch_http_error_raise_gcs_api_error()
  def CopyObject(self,
                 source_object_metadata,
                 destination_object_metadata,
                 source_object_generation=None,
                 progress_callback=None,
                 request_config=None):
    """See super class."""
    # TODO(b/161900052): Implement resumable copies.
    # TODO(b/161898251): Implement encryption and decryption.
    if not getattr(source_object_metadata, 'etag', None):
      raise ValueError('Etag is required for source objects in copy.')
    _ValidateObjectMetadata(source_object_metadata)
    _ValidateObjectMetadata(destination_object_metadata)

    # S3 requires a string, but GCS uses an int for generation.
    if source_object_generation:
      source_object_generation = int(source_object_generation)

    object_metadata = self.client.objects.Copy(
        self.messages.StorageObjectsCopyRequest(
            sourceBucket=source_object_metadata.bucket,
            sourceObject=source_object_metadata.name,
            destinationBucket=destination_object_metadata.bucket,
            destinationObject=destination_object_metadata.name))
    return resource_reference.ObjectResource.from_gcs_metadata_object(
        cloud_api.ProviderPrefix.GCS.value, object_metadata)

  # pylint: disable=unused-argument
  def _DownloadObject(self,
                      bucket_name,
                      object_name,
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
      bucket_name (str): Bucket containing the object.
      object_name (str): Object name.
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

    if start_byte or end_byte:
      apitools_download.GetRange(additional_headers=additional_headers,
                                 start=start_byte,
                                 end=end_byte,
                                 use_chunks=False)
    else:
      apitools_download.StreamMedia(additional_headers=additional_headers,
                                    callback=_NoOpCallback,
                                    finish_callback=_NoOpCallback,
                                    use_chunks=False)
    return apitools_download.encoding

  # pylint: disable=unused-argument
  @cloud_errors.catch_http_error_raise_gcs_api_error()
  def DownloadObject(self,
                     bucket_name,
                     object_name,
                     download_stream,
                     compressed_encoding=False,
                     decryption_wrapper=None,
                     digesters=None,
                     download_strategy=cloud_api.DownloadStrategy.ONE_SHOT,
                     generation=None,
                     object_size=None,
                     progress_callback=None,
                     serialization_data=None,
                     start_byte=0,
                     end_byte=None):
    """See super class."""
    # S3 requires a string, but GCS uses an int for generation.
    if generation:
      generation = int(generation)

    if not serialization_data:
      # New download.
      apitools_download = apitools_transfer.Download.FromStream(
          download_stream,
          auto_transfer=False,
          total_size=object_size,
          num_retries=DEFAULT_NUM_RETRIES)
      apitools_download.bytes_http = transports.GetApitoolsTransport(
          response_encoding=None)
    else:
      # TODO(b/161437901): Handle resumed download.
      pass

    # TODO(b/161460749) Handle download retries.
    request = self.messages.StorageObjectsGetRequest(
        bucket=bucket_name,
        object=object_name,
        generation=generation)

    if download_strategy == cloud_api.DownloadStrategy.ONE_SHOT:
      return self._DownloadObject(bucket_name,
                                  object_name,
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
      # TODO(b/161437901): Handle resumable download.
      pass

  # pylint: disable=unused-argument
  def _UploadObject(self,
                    upload_stream,
                    object_metadata,
                    request_config,
                    apitools_strategy=apitools_transfer.SIMPLE_UPLOAD,
                    progress_callback=None,
                    serialization_data=None,
                    total_size=0,
                    tracker_callback=None):
    # pylint: disable=g-doc-args
    """GCS-specific upload implementation. Adds args to Cloud API interface.

    Additional args:
      apitools_strategy (str): SIMPLE_UPLOAD or RESUMABLE_UPLOAD constant in
          apitools.base.py.transfer.
      serialization_data (str): Implementation-specific JSON string of a dict
          containing serialization information for the download.
      total_size (int): Total size of the upload in bytes.
          If streaming, total size is None.
      tracker_callback (function): Callback that keeps track of upload progress.

    Returns:
      Uploaded object metadata as an Apitools message Object.
    """
    _ValidateObjectMetadata(object_metadata)

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
      # One-shot upload.
      apitools_upload = apitools_transfer.Upload(
          upload_stream,
          content_type,
          total_size=request_config.size,
          auto_transfer=True,
          num_retries=DEFAULT_NUM_RETRIES,
          gzip_encoded=request_config.gzip_encoded)
      # Not settable through the Apitools Upload class constructor.
      apitools_upload.strategy = apitools_strategy

      object_metadata = self.client.objects.Insert(request,
                                                   upload=apitools_upload)
      return resource_reference.ObjectResource.from_gcs_metadata_object(
          cloud_api.ProviderPrefix.GCS.value, object_metadata)
    else:
      # TODO(b/160998556): Implement resumable upload.
      pass

  @cloud_errors.catch_http_error_raise_gcs_api_error()
  def UploadObject(self,
                   upload_stream,
                   object_metadata,
                   progress_callback=None,
                   request_config=None):
    """See CloudApi class for function doc strings."""
    # Doing this as a default argument above can lead to unexpected bugs:
    # https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments
    if request_config is None:
      request_config = GcsRequestConfig()
    return self._UploadObject(
        upload_stream,
        object_metadata,
        apitools_strategy=apitools_transfer.SIMPLE_UPLOAD,
        progress_callback=progress_callback,
        request_config=request_config,
        serialization_data=None)
