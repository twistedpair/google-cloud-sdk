# -*- coding: utf-8 -*- #
# Copyright 2020 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""API interface for interacting with cloud storage providers."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum
import threading


class ProviderPrefix(enum.Enum):
  """Prefix strings for cloud storage provider URLs."""
  GCS = 'gs'
  S3 = 's3'


class FieldsScope(enum.Enum):
  """Values used to determine fields and projection values for API calls."""
  FULL = 1
  NO_ACL = 2
  SHORT = 3


NUM_ITEMS_PER_LIST_PAGE = 1000

# Module variable for holding one API instance per thread per provider.
_cloud_api_thread_local_storage = threading.local()


def GetApi(provider):
  """Returns thread local API instance for cloud provider.

  Uses thread local storage to make sure only one instance of an API exists
  per thread per provider.

  Args:
    provider (ProviderPrefix): Cloud provider prefix (i.e. "gs").

  Returns:
    API for cloud provider or None if unrecognized provider.

  Raises:
    ValueError: Invalid API provider.
  """
  if getattr(_cloud_api_thread_local_storage, provider, None) is None:
    if provider == ProviderPrefix.GCS:
      # TODO(b/159164504): Update with implemented GCS API.
      _cloud_api_thread_local_storage.gs = CloudApi()
    elif provider == ProviderPrefix.S3:
      # TODO(b/159164385): Update with implemented S3 API.
      _cloud_api_thread_local_storage.s3 = CloudApi()
    else:
      raise ValueError('Provider API value must be "gs" or "s3".')
  return getattr(_cloud_api_thread_local_storage, provider)


class RequestConfig(object):
  """Arguments object for parameters shared between cloud providers.

  Attributes:
      predefined_acl_string (string): ACL to be set on the object.
  """

  def __init__(self, predefined_acl_string=None):
    self.predefined_acl_string = predefined_acl_string


class CloudApi(object):
  """Abstract base class for interacting with cloud storage providers.

  Implementations of the Cloud API are not guaranteed to be thread-safe.
  Behavior when calling a Cloud API instance simultaneously across
  threads is undefined and doing so will likely cause errors. Therefore,
  a separate instance of the Cloud API should be instantiated per-thread.
  """

  def GetBucket(self, bucket_name, fields_scope=None):
    """Gets Bucket metadata.

    Args:
      bucket_name (string): Name of the bucket.
      fields_scope (FieldsScope): Determines the fields and projection
          parameters of API call.

    Return:
      Apitools messages bucket object.

    Raises:
      NotImplementedError: This function was not implemented by a class using
          this interface.
      ValueError: Invalid fields_scope.
    """
    raise NotImplementedError('GetBucket must be overridden.')

  def ListBuckets(self, fields_scope=None):
    """Lists bucket metadata for the given project.

    Args:
      fields_scope (FieldsScope): Determines the fields and projection
          parameters of API call.

    Yields:
      Iterator over Bucket objects.

    Raises:
      NotImplementedError: This function was not implemented by a class using
          this interface.
      ValueError: Invalid fields_scope.
    """
    raise NotImplementedError('ListBuckets must be overridden.')

  def ListObjects(self,
                  bucket_name,
                  prefix=None,
                  delimiter=None,
                  all_versions=None,
                  fields_scope=None):
    """Lists objects (with metadata) and prefixes in a bucket.

    Args:
      bucket_name (string): Bucket containing the objects.
      prefix (string): Prefix for directory-like behavior.
      delimiter (string): Delimiter for directory-like behavior.
      all_versions (boolean): If true, list all object versions.
      fields_scope (FieldsScope): Determines the fields and projection
          parameters of API call.

    Yields:
      Iterator over CsObjectOrPrefix wrapper class.

    Raises:
      NotImplementedError: This function was not implemented by a class using
          this interface.
      ValueError: Invalid fields_scope.
    """
    raise NotImplementedError('ListObjects must be overridden.')

  def GetObjectMetadata(self,
                        bucket_name,
                        object_name,
                        generation=None,
                        fields_scope=None):
    """Gets object metadata.

    If decryption is supported by the implementing class, this function will
    read decryption keys from configuration and appropriately retry requests to
    encrypted objects with the correct key.

    Args:
      bucket_name (string): Bucket containing the object.
      object_name (string): Object name.
      generation (long): Generation of the object to retrieve.
      fields_scope (FieldsScope): Determines the fields and projection
          parameters of API call.

    Raises:
      NotImplementedError: This function was not implemented by a class using
          this interface.
      ValueError: Invalid fields_scope.

    Returns:
      Apitools messages object.
    """
    raise NotImplementedError('GetObjectMetadata must be overridden.')

  def PatchObjectMetadata(self,
                          bucket_name,
                          object_name,
                          metadata,
                          fields_scope=None,
                          generation=None,
                          request_config=None):
    """Updates object metadata with patch semantics.

    Args:
      bucket_name (string): Bucket containing the object.
      object_name (string): Object name.
      metadata (object): Object defining metadata to be updated.
      fields_scope (FieldsScope): Determines the fields and projection
          parameters of API call.
      generation (long): Generation (or version) of the object to update.
      request_config (RequestConfig): Object containing general API function
          arguments. Subclasses for specific cloud providers are available.

    Returns:
      Apitools messages object containing updated metadata.

    Raises:
      NotImplementedError: This function was not implemented by a class using
          this interface.
      ValueError: Invalid fields_scope.
    """
    raise NotImplementedError('PatchObjectMetadata must be overridden.')

  def UploadObject(self,
                   upload_stream,
                   object_metadata,
                   canned_acl=None,
                   crypto_key_wrapper=None,
                   size=None,
                   preconditions=None,
                   progress_callback=None,
                   provider=None,
                   fields_scope=None,
                   gzip_encoded=False):
    """Uploads object data and metadata.

    Args:
      upload_stream: Seekable stream of object data.
      object_metadata: Object metadata for new object.  Must include bucket and
        object name.
      canned_acl: Optional canned ACL to apply to object. Overrides ACL set in
        object_metadata.
      crypto_key_wrapper: Optional utils.encryption_helper.CryptoKeyWrapper for
        encrypting the uploaded object.
      size: Optional object size.
      preconditions: Preconditions for the request.
      progress_callback: Optional callback function for progress notifications.
        Receives calls with arguments (bytes_transferred, total_size).
      provider: Cloud storage provider to connect to.  If not present,
        class-wide default is used.
      fields_scope: Determines the fields and projection parameters of API call.
      gzip_encoded: Whether to use gzip transport encoding for the upload.

    Raises:
      InvalidArgumentException for errors during input validation.
      CloudProviderException for errors interacting with cloud storage
      providers.

    Returns:
      Object object for newly created destination object.
    """
    raise NotImplementedError('UploadObject must be overridden.')
