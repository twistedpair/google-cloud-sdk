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

# TODO(b/275749579): Rename this module.

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum

from googlecloudsdk.command_lib.storage import storage_url


class Capability(enum.Enum):
  """Used to track API capabilities relevant to logic in tasks."""
  COMPOSE_OBJECTS = 'COMPOSE_OBJECTS'
  CLIENT_SIDE_HASH_VALIDATION = 'CLIENT_SIDE_HASH_VALIDATION'
  ENCRYPTION = 'ENCRYPTION'
  RESUMABLE_UPLOAD = 'RESUMABLE_UPLOAD'
  SLICED_DOWNLOAD = 'SLICED_DOWNLOAD'
  # For daisy chain operations, the upload stream is not purely seekable.
  # For certain seek calls, we raise errors to avoid re-downloading the object.
  # We do not want the "seekable" method for the upload stream to always return
  # False because in case of GCS, Apitools checks for this value to determine
  # if a resumable upload can be performed. However, for S3,
  # boto3's upload_fileobj calls "seek" with
  # unsupported offset and whence combinations, and to avoid that,
  # we need to mark the upload stream as non-seekable for S3.
  # This value is used by daisy chain operation to determine if the upload
  # stream can be treated as seekable.
  DAISY_CHAIN_SEEKABLE_UPLOAD_STREAM = 'DAISY_CHAIN_SEEKABLE_UPLOAD_STREAM'


class DownloadStrategy(enum.Enum):
  """Enum class for specifying download strategy."""
  ONE_SHOT = 'oneshot'  # No in-flight retries performed.
  # Operations are retried on network errors.
  RETRIABLE_IN_FLIGHT = 'retriable_in_flight'
  # In addition to retrying on errors, operations can be resumed if halted.
  # This option will write tracker files to track the downloads in progress.
  RESUMABLE = 'resumable'


class UploadStrategy(enum.Enum):
  """Enum class for specifying upload strategy."""
  SIMPLE = 'simple'
  RESUMABLE = 'resumable'
  STREAMING = 'streaming'


class NotificationEventType(enum.Enum):
  """Used to filter what events a notification configuration notifies on."""
  OBJECT_ARCHIVE = 'OBJECT_ARCHIVE'
  OBJECT_DELETE = 'OBJECT_DELETE'
  OBJECT_FINALIZE = 'OBJECT_FINALIZE'
  OBJECT_METADATA_UPDATE = 'OBJECT_METADATA_UPDATE'


class NotificationPayloadFormat(enum.Enum):
  """Used to format the body of notifications."""
  JSON = 'json'
  NONE = 'none'


class FieldsScope(enum.Enum):
  """Values used to determine fields and projection values for API calls."""
  FULL = 1
  NO_ACL = 2
  RSYNC = 3  # Only for objects.
  SHORT = 4


class HmacKeyState(enum.Enum):
  ACTIVE = 'ACTIVE'
  INACTIVE = 'INACTIVE'


DEFAULT_PROVIDER = storage_url.ProviderPrefix.GCS
NUM_ITEMS_PER_LIST_PAGE = 1000


class CloudApi(object):
  """Abstract base class for interacting with cloud storage providers.

  Implementations of the Cloud API are not guaranteed to be thread-safe.
  Behavior when calling a Cloud API instance simultaneously across
  threads is undefined and doing so will likely cause errors. Therefore,
  a separate instance of the Cloud API should be instantiated per-thread.

  Attributes:
    capabilities (set[Capability]): If a Capability is present in this set, this
      API can be used to execute related logic in tasks.
  """
  capabilities = set()

  # Some APIs limit the number of objects that can be composed in a single call.
  # This field should be overidden by those APIs, and default to 1 for APIs
  # that do not support compose_objects.
  MAX_OBJECTS_PER_COMPOSE_CALL = 1

  def create_bucket(self, bucket_resource, request_config, fields_scope=None):
    """Creates a new bucket with the specified metadata.

    Args:
      bucket_resource (resource_reference.UnknownResource): The bucket to
        create.
      request_config (RequestConfig): Contains metadata for new bucket.
      fields_scope (FieldsScope): Determines the fields and projection
        parameters of API call.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
      ValueError: Invalid fields_scope.

    Returns:
      resource_reference.BucketResource representing new bucket.
    """
    raise NotImplementedError('create_bucket must be overridden.')

  def delete_bucket(self, bucket_name, request_config):
    """Deletes a bucket.

    Args:
      bucket_name (str): Name of the bucket to delete.
      request_config (RequestConfig): Object containing general API function
        arguments. Subclasses for specific cloud providers are available.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    raise NotImplementedError('delete_bucket must be overridden.')

  def get_bucket(self, bucket_name, fields_scope=None):
    """Gets bucket metadata.

    Args:
      bucket_name (str): Name of the bucket.
      fields_scope (FieldsScope): Determines the fields and projection
        parameters of API call.

    Returns:
      resource_reference.BucketResource containing the bucket metadata.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
      ValueError: Invalid fields_scope.
    """
    raise NotImplementedError('get_bucket must be overridden.')

  def get_bucket_iam_policy(self, bucket_name):
    """Gets bucket IAM policy.

    Args:
      bucket_name (str): Name of the bucket.

    Returns:
      Provider-specific data type. Currently, only available for GCS so returns
        Apitools messages.Policy object. If supported for
        more providers in the future, use a generic container.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    raise NotImplementedError('get_bucket_iam_policy must be overridden.')

  def list_buckets(self, fields_scope=None):
    """Lists bucket metadata for the given project.

    Args:
      fields_scope (FieldsScope): Determines the fields and projection
        parameters of API call.

    Yields:
      Iterator over resource_reference.BucketResource objects

    Raises:
      NotImplementedError: This function was not implemented by a class using
        this interface.
      ValueError: Invalid fields_scope.
    """
    raise NotImplementedError('list_buckets must be overridden.')

  def lock_bucket_retention_policy(self, bucket_resource, request_config):
    """Locks a bucket's retention policy.

    Args:
      bucket_resource (UnknownResource): The bucket with the policy to lock.
      request_config (RequestConfig): Object containing general API function
        arguments. Subclasses for specific cloud providers are available.

    Returns:
      resource_reference.BucketResource containing the bucket metadata.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
          this interface.
    """
    raise NotImplementedError(
        'lock_bucket_retention_policy must be overridden.')

  def patch_bucket(self, bucket_resource, request_config, fields_scope=None):
    """Patches bucket metadata.

    Args:
      bucket_resource (BucketResource|UnknownResource): The bucket to patch.
      request_config (RequestConfig): Contains new metadata for the bucket.
      fields_scope (FieldsScope): Determines the fields and projection
        parameters of API call.

    Returns:
      resource_reference.BucketResource containing the bucket metadata.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
          this interface.
      ValueError: Invalid fields_scope.
    """
    raise NotImplementedError('patch_bucket must be overridden.')

  def set_bucket_iam_policy(self, bucket_name, policy):
    """Sets bucket IAM policy.

    Args:
      bucket_name (str): Name of the bucket.
      policy (object): Provider-specific data type. Currently, only
        available for GCS so Apitools messages.Policy object. If supported for
        more providers in the future, use a generic container.

    Returns:
      Provider-specific data type. Currently, only available for GCS so returns
        Apitools messages.Policy object. If supported for
        more providers in the future, use a generic container.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    raise NotImplementedError('get_bucket_iam_policy must be overridden.')

  def create_hmac_key(self, service_account_email):
    """Creates an HMAC key.

    Args:
      service_account_email (str): The email of the service account to use.

    Returns:
      gcs_resource_reference.GcsHmacKeyResource. Provider-specific data type
      is used for now because we currently support this feature only for the
      JSON API.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    raise NotImplementedError('create_hmac_key must be overridden.')

  def delete_hmac_key(self, access_id):
    """Deletes an HMAC key.

    Args:
      access_id (str): The access ID corresponding to the HMAC key.

    Returns:
      None

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    raise NotImplementedError('delete_hmac_key must be overridden.')

  def get_hmac_key(self, access_id):
    """Gets an HMAC key.

    Args:
      access_id (str): The access ID corresponding to the HMAC key.

    Returns:
      gcs_resource_reference.GcsHmacKeyResource. Provider-specific data type
      is used for now because we currently support this feature only for the
      JSON API.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    raise NotImplementedError('get_hmac_key must be overridden.')

  def list_hmac_keys(self, service_account_email=None, show_deleted_keys=False,
                     fields_scope=None):
    """Lists HMAC keys.

    Args:
      service_account_email (str): Return HMAC keys for the given service
        account email.
      show_deleted_keys (bool): If True, include keys in the DELETED state.
      fields_scope (FieldsScope): Determines which metadata keys
        the API should return for each key.

    Yields:
      Iterator over gcs_resource_reference.GcsHmacKeyResource objects.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    pass

  def patch_hmac_key(self, access_id, etag, state):
    """Updates an HMAC key.

    Args:
      access_id (str): The access ID corresponding to the HMAC key.
      etag (str): Only perform the patch request if the etag matches this value.
      state (HmacKeyState): The desired state of the HMAC key.

    Returns:
      gcs_resource_reference.GcsHmacKeyResource. Provider-specific data type
      is used for now because we currently support this feature only for the
      JSON API.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    raise NotImplementedError('patch_hmac_key must be overridden.')

  def compose_objects(self,
                      source_resources,
                      destination_resource,
                      request_config,
                      original_source_resource=None):
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

    Returns:
      resource_reference.ObjectResource with composite object's metadata.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    raise NotImplementedError('compose_object must be overridden.')

  def copy_object(self,
                  source_resource,
                  destination_resource,
                  request_config,
                  should_deep_copy_metadata=False,
                  progress_callback=None):
    """Copies an object within the cloud of one provider.

    Args:
      source_resource (resource_reference.ObjectResource): Resource for
        source object. Must have been confirmed to exist in the cloud.
      destination_resource (resource_reference.ObjectResource|UnknownResource):
        Resource for destination object. Existence doesn't have to be confirmed.
      request_config (RequestConfig): Object containing general API function
        arguments. Subclasses for specific cloud providers are available.
      should_deep_copy_metadata (bool): Rather than copying select fields of
        the source metadata, if True, copy everything. The request_config data
        (containing user args) overrides the deep-copied data.
      progress_callback (function): Optional callback function for progress
        notifications. Receives calls with arguments (bytes_transferred,
        total_size).

    Returns:
      resource_reference.ObjectResource with new object's metadata.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    raise NotImplementedError('copy_object must be overridden')

  def delete_object(self, object_url, request_config):
    """Deletes an object.

    Args:
      object_url (storage_url.CloudUrl): Url of object to delete.
      request_config (RequestConfig): Object containing general API function
        arguments. Subclasses for specific cloud providers are available.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
          this interface.
    """
    raise NotImplementedError('delete_object must be overridden.')

  def download_object(self,
                      cloud_resource,
                      download_stream,
                      request_config,
                      digesters=None,
                      do_not_decompress=False,
                      download_strategy=DownloadStrategy.ONE_SHOT,
                      progress_callback=None,
                      start_byte=0,
                      end_byte=None):
    """Gets object data.

    Args:
      cloud_resource (resource_reference.ObjectResource): Contains metadata and
        information about object being downloaded.
      download_stream (stream): Stream to send the object data to.
      request_config (RequestConfig): Contains arguments for API calls.
      digesters (dict): Dict of {string : digester}, where string is the name of
        a hash algorithm, and digester is a validation digester object that
        update(bytes) and digest() using that algorithm. Implementation can set
        the digester value to None to indicate supports bytes were not
        successfully digested on-the-fly.
      do_not_decompress (bool): If true, gzipped objects will not be
        decompressed on-the-fly if supported by the API.
      download_strategy (DownloadStrategy): Cloud API download strategy to use
        for download.
      progress_callback (function): Optional callback function for progress
        notifications. Receives calls with arguments (bytes_transferred,
        total_size).
      start_byte (int): Starting point for download (for resumable downloads and
        range requests). Can be set to negative to request a range of bytes
        (python equivalent of [:-3]).
      end_byte (int): Ending byte number, inclusive, for download (for range
        requests). If None, download the rest of the object.

    Returns:
      server_encoding (str): Useful for determining what the server actually
        sent versus what object metadata claims.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    raise NotImplementedError('download_object must be overridden.')

  def get_object_iam_policy(self, bucket_name, object_name, generation=None):
    """Gets object IAM policy.

    Args:
      bucket_name (str): Name of the bucket.
      object_name (str): Name of the object.
      generation (str|None): Generation of object.

    Returns:
      Provider-specific data type. Currently, only available for GCS so returns
        Apitools messages.Policy object. If supported for
        more providers in the future, use a generic container.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    raise NotImplementedError('get_object_iam_policy must be overridden.')

  def get_object_metadata(self,
                          bucket_name,
                          object_name,
                          request_config=None,
                          generation=None,
                          fields_scope=None):
    """Gets object metadata.

    If decryption is supported by the implementing class, this function will
    read decryption keys from configuration and appropriately retry requests to
    encrypted objects with the correct key.

    Args:
      bucket_name (str): Bucket containing the object.
      object_name (str): Object name.
      request_config (RequestConfig): Contains API call arguments.
      generation (string): Generation of the object to retrieve.
      fields_scope (FieldsScope): Determines the fields and projection
        parameters of API call.

    Returns:
      resource_reference.ObjectResource with object metadata.

    Raises:
      CloudApiError: API returned an error.
      NotFoundError: Raised if object does not exist.
      NotImplementedError: This function was not implemented by a class using
        this interface.
      ValueError: Invalid fields_scope.
    """
    raise NotImplementedError('get_object_metadata must be overridden.')

  def list_objects(self,
                   bucket_name,
                   prefix=None,
                   delimiter=None,
                   all_versions=None,
                   fields_scope=None):
    """Lists objects (with metadata) and prefixes in a bucket.

    Args:
      bucket_name (str): Bucket containing the objects.
      prefix (str): Prefix for directory-like behavior.
      delimiter (str): Delimiter for directory-like behavior.
      all_versions (boolean): If true, list all object versions.
      fields_scope (FieldsScope): Determines the fields and projection
        parameters of API call.

    Yields:
      Iterator over resource_reference.ObjectResource objects.

    Raises:
      NotImplementedError: This function was not implemented by a class using
        this interface.
      ValueError: Invalid fields_scope.
    """
    raise NotImplementedError('list_objects must be overridden.')

  def patch_object_metadata(self,
                            bucket_name,
                            object_name,
                            object_resource,
                            request_config,
                            fields_scope=None,
                            generation=None):
    """Updates object metadata with patch semantics.

    Args:
      bucket_name (str): Bucket containing the object.
      object_name (str): Object name.
      object_resource (resource_reference.ObjectResource): Contains metadata
        that will be used to update cloud object. May have different name than
        object_name argument.
      request_config (RequestConfig): Object containing general API function
        arguments. Subclasses for specific cloud providers are available.
      fields_scope (FieldsScope): Determines the fields and projection
        parameters of API call.
      generation (string): Generation (or version) of the object to update.

    Returns:
      resource_reference.ObjectResource with patched object metadata.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
      ValueError: Invalid fields_scope.
    """
    raise NotImplementedError('patch_object_metadata must be overridden.')

  def set_object_iam_policy(self,
                            bucket_name,
                            object_name,
                            policy,
                            generation=None):
    """Sets object IAM policy.

    Args:
      bucket_name (str): Name of the bucket.
      object_name (str): Name of the object.
      policy (object): Provider-specific data type. Currently, only available
        for GCS so Apitools messages.Policy object. If supported for more
        providers in the future, use a generic container.
      generation (str|None): Generation of object.

    Returns:
      Provider-specific data type. Currently, only available for GCS so returns
        Apitools messages.Policy object. If supported for
        more providers in the future, use a generic container.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    raise NotImplementedError('set_bucket_iam_policy must be overridden.')

  def upload_object(self,
                    source_stream,
                    destination_resource,
                    request_config,
                    source_resource=None,
                    serialization_data=None,
                    tracker_callback=None,
                    upload_strategy=UploadStrategy.SIMPLE):
    """Uploads object data and metadata.

    Args:
      source_stream (stream): Seekable stream of object data.
      destination_resource (resource_reference.ObjectResource|UnknownResource):
        Contains the correct metadata to upload.
      request_config (RequestConfig): Object containing general API function
        arguments. Subclasses for specific cloud providers are available.
      source_resource (resource_reference.FileObjectResource|None):
        Contains the source StorageUrl. Can be None if source is pure stream.
      serialization_data (dict): API-specific data needed to resume an upload.
        Only used with UploadStrategy.RESUMABLE.
      tracker_callback (Callable[[dict], None]): Function that writes a tracker
        file with serialization data. Only used with UploadStrategy.RESUMABLE.
      upload_strategy (UploadStrategy): Strategy to use for this upload.

    Returns:
      resource_reference.ObjectResource with uploaded object's metadata.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
    """
    raise NotImplementedError('upload_object must be overridden.')

  def get_service_agent(self, project_id=None, project_number=None):
    """Returns the email address (str) used to identify the service agent.

    For some providers, the service agent is responsible for encrypting and
    decrypting objects using CMEKs. project_number is useful because it may be
    in bucket metadata when project ID is not.

    If neither project_id or project_number are available, uses the
      default project configured in gcloud.


    Args:
      project_id (str|None): Project to get service account for. Takes
        precedence over project_number.
      project_number (int|None): Project to get service account for.

    Returns:
      Email of service account (str).
    """
    raise NotImplementedError('get_service_agent must be overridden.')

  def create_notification_configuration(
      self,
      url,
      pubsub_topic,
      custom_attributes=None,
      event_types=None,
      object_name_prefix=None,
      payload_format=NotificationPayloadFormat.JSON):
    """Creates a new notification on a bucket with the specified parameters.

    Args:
      url (storage_url.CloudUrl): Bucket URL.
      pubsub_topic (str): Cloud Pub/Sub topic to publish to.
      custom_attributes (dict[str, str]|None): Dictionary of custom attributes
        to apply to all notifications sent by the new configuration.
      event_types (list[NotificationEventType]|None): Event type filters, e.g.
        'OBJECT_FINALIZE'.
      object_name_prefix (str|None): Filter on object name.
      payload_format (NotificationPayloadFormat): Format of body of
        notifications sent by the new configuration.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
      ValueError: Received a non-bucket URL.

    Returns:
      Apitools Notification object for the new notification configuration.
    """
    raise NotImplementedError(
        'create_notification_configuration must be overridden.')

  def delete_notification_configuration(self, url, notification_id):
    """Deletes a notification configuration on a bucket.

    Args:
      url (storage_url.CloudUrl): Bucket URL.
      notification_id (str): Name of the notification configuration.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
      ValueError: Received a non-bucket URL.
    """
    raise NotImplementedError(
        'delete_notification_configuration must be overridden.')

  def get_notification_configuration(self, url, notification_id):
    """Gets a notification configuration on a bucket.

    Args:
      url (storage_url.CloudUrl): Bucket URL.
      notification_id (str): Name of the notification configuration.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
      ValueError: Received a non-bucket URL.
    """
    raise NotImplementedError(
        'get_notification_configuration must be overridden.')

  def list_notification_configurations(self, url):
    """Lists notification configurations on a bucket.

    Args:
      url (storage_url.CloudUrl): Bucket URL.

    Raises:
      CloudApiError: API returned an error.
      NotImplementedError: This function was not implemented by a class using
        this interface.
      ValueError: Received a non-bucket URL.

    Yields:
      List of  apitools Notification objects.
    """
    raise NotImplementedError(
        'list_notification_configurations must be overridden.')
