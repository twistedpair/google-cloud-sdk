# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Tools for making the most of GcsApi metadata."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import copy

from googlecloudsdk.api_lib.storage import gcs_metadata_field_converters
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.storage import encryption_util
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.resources import gcs_resource_reference


# Since CORS is a list in apitools, we need special handling, or blank
# CORS lists will get sent with other configuration commands, such as lifecycle,
# which would cause CORS configuration to be unintentionally removed.
# Protorpc defaults list values to an empty list and won't allow us to set the
# value to None like other configuration fields, so there is no way to
# distinguish the default value from when we actually want to remove the CORS
# configuration. To work around this, we create a fake CORS entry that
# signifies that we should nullify the CORS configuration.
# A value of [] means don't modify the CORS configuration.
# A value of REMOVE_CORS_CONFIG means remove the CORS configuration.
REMOVE_CORS_CONFIG = [
    apis.GetMessagesModule('storage', 'v1').Bucket.CorsValueListEntry(
        maxAgeSeconds=-1, method=['REMOVE_CORS_CONFIG'])
]

# Similar to CORS above, we need a sentinel value allowing us to specify
# when a default object ACL should be private (containing no entries).
# A defaultObjectAcl value of [] means don't modify the default object ACL.
# A value of [PRIVATE_DEFAULT_OBJ_ACL] means create an empty/private default
# object ACL.
PRIVATE_DEFAULT_OBJECT_ACL = apis.GetMessagesModule(
    'storage', 'v1').ObjectAccessControl(id='PRIVATE_DEFAULT_OBJ_ACL')


def copy_select_object_metadata(source_metadata, destination_metadata):
  """Copies specific metadata from source_metadata to destination_metadata.

  The API manually generates metadata for destination objects most of the time,
  but here are some fields that may not be populated.

  Args:
    source_metadata (messages.Object): Metadata from source object.
    destination_metadata (messages.Object): Metadata for destination object.
  """
  destination_metadata.cacheControl = source_metadata.cacheControl
  destination_metadata.contentDisposition = source_metadata.contentDisposition
  destination_metadata.contentEncoding = source_metadata.contentEncoding
  destination_metadata.contentLanguage = source_metadata.contentLanguage
  destination_metadata.contentType = source_metadata.contentType
  destination_metadata.crc32c = source_metadata.crc32c
  destination_metadata.customTime = source_metadata.customTime
  destination_metadata.md5Hash = source_metadata.md5Hash
  destination_metadata.metadata = copy.deepcopy(source_metadata.metadata)


def get_apitools_metadata_from_url(cloud_url):
  """Takes storage_url.CloudUrl and returns appropriate Apitools message."""
  messages = apis.GetMessagesModule('storage', 'v1')
  if cloud_url.is_bucket():
    return messages.Bucket(name=cloud_url.bucket_name)
  elif cloud_url.is_object():
    generation = int(cloud_url.generation) if cloud_url.generation else None
    return messages.Object(
        name=cloud_url.object_name,
        bucket=cloud_url.bucket_name,
        generation=generation)


def get_bucket_resource_from_metadata(metadata):
  """Helper method to generate a BucketResource instance from GCS metadata.

  Args:
    metadata (messages.Bucket): Extract resource properties from this.

  Returns:
    BucketResource with properties populated by metadata.
  """
  url = storage_url.CloudUrl(
      scheme=storage_url.ProviderPrefix.GCS, bucket_name=metadata.name)
  retention_period = getattr(metadata.retentionPolicy, 'retentionPeriod', None)
  uniform_bucket_level_access = getattr(
      getattr(metadata.iamConfiguration, 'uniformBucketLevelAccess', False),
      'enabled', False)
  return gcs_resource_reference.GcsBucketResource(
      url,
      etag=metadata.etag,
      location=metadata.location,
      metadata=metadata,
      retention_period=retention_period,
      storage_class=metadata.storageClass,
      uniform_bucket_level_access=uniform_bucket_level_access)


def get_metadata_from_bucket_resource(resource):
  """Helper method to generate Apitools metadata instance from BucketResource.

  Args:
    resource (BucketResource): Extract metadata properties from this.

  Returns:
    messages.Bucket with properties populated by resource.
  """
  messages = apis.GetMessagesModule('storage', 'v1')
  metadata = messages.Bucket(
      name=resource.name,
      etag=resource.etag,
      location=resource.location,
      storageClass=resource.storage_class)

  if resource.retention_period:
    metadata.retentionPolicy = messages.Bucket.RetentionPolicyValue(
        retentionPeriod=resource.retention_period)
  if resource.uniform_bucket_level_access:
    metadata.iamConfiguration = messages.Bucket.IamConfigurationValue(
        uniformBucketLevelAccess=messages.Bucket.IamConfigurationValue
        .UniformBucketLevelAccessValue(
            enabled=resource.uniform_bucket_level_access))

  return metadata


def get_object_resource_from_metadata(metadata):
  """Helper method to generate a ObjectResource instance from GCS metadata.

  Args:
    metadata (messages.Object): Extract resource properties from this.

  Returns:
    ObjectResource with properties populated by metadata.
  """
  if metadata.generation is not None:
    # Generation may be 0 integer, which is valid although falsy.
    generation = str(metadata.generation)
  else:
    generation = None
  url = storage_url.CloudUrl(
      scheme=storage_url.ProviderPrefix.GCS,
      bucket_name=metadata.bucket,
      object_name=metadata.name,
      generation=generation)

  if metadata.customerEncryption:
    key_hash = metadata.customerEncryption.keySha256
  else:
    key_hash = None

  return gcs_resource_reference.GcsObjectResource(
      url,
      content_type=metadata.contentType,
      creation_time=metadata.timeCreated,
      decryption_key_hash=key_hash,
      etag=metadata.etag,
      crc32c_hash=metadata.crc32c,
      md5_hash=metadata.md5Hash,
      metadata=metadata,
      metageneration=metadata.metageneration,
      size=metadata.size)


def update_bucket_metadata_from_request_config(bucket_metadata, request_config):
  """Sets Apitools Bucket fields based on values in request_config."""
  resource_args = request_config.resource_args
  if not resource_args:
    return
  if resource_args.cors_file_path is not None:
    bucket_metadata.cors = gcs_metadata_field_converters.process_cors(
        resource_args.cors_file_path)
  if resource_args.default_encryption_key is not None:
    bucket_metadata.encryption = (
        gcs_metadata_field_converters.process_default_encryption_key(
            resource_args.default_encryption_key))
  if resource_args.default_event_based_hold is not None:
    bucket_metadata.defaultEventBasedHold = (
        resource_args.default_event_based_hold)
  if resource_args.default_storage_class is not None:
    bucket_metadata.storageClass = resource_args.default_storage_class
  if resource_args.labels_file_path is not None:
    bucket_metadata.labels = gcs_metadata_field_converters.process_labels(
        resource_args.labels_file_path)
  if resource_args.lifecycle_file_path is not None:
    bucket_metadata.lifecycle = (
        gcs_metadata_field_converters.process_lifecycle(
            resource_args.lifecycle_file_path))
  if resource_args.location is not None:
    bucket_metadata.location = resource_args.location
  if resource_args.retention_period is not None:
    bucket_metadata.retentionPolicy = (
        gcs_metadata_field_converters.process_retention_period(
            resource_args.retention_period))
  if resource_args.uniform_bucket_level_access is not None:
    bucket_metadata.iamConfiguration = (
        gcs_metadata_field_converters.process_uniform_bucket_level_access(
            bucket_metadata.iamConfiguration,
            resource_args.uniform_bucket_level_access))
  if resource_args.versioning is not None:
    bucket_metadata.versioning = (
        gcs_metadata_field_converters.process_versioning(
            resource_args.versioning))
  if (resource_args.web_error_page is not None or
      resource_args.web_main_page_suffix is not None):
    bucket_metadata.website = gcs_metadata_field_converters.process_website(
        resource_args.web_error_page, resource_args.web_main_page_suffix)


def update_object_metadata_from_request_config(object_metadata, request_config):
  """Sets Apitools Object fields based on values in request_config."""
  resource_args = request_config.resource_args
  if not resource_args:
    return
  if resource_args.cache_control is not None:
    object_metadata.cacheControl = resource_args.cache_control
  if resource_args.content_disposition is not None:
    object_metadata.contentDisposition = resource_args.content_disposition
  if resource_args.content_encoding is not None:
    object_metadata.contentEncoding = resource_args.content_encoding
  if resource_args.content_language is not None:
    object_metadata.contentLanguage = resource_args.content_language
  if resource_args.custom_time is not None:
    object_metadata.customTime = resource_args.custom_time
  if resource_args.content_type is not None:
    object_metadata.contentType = resource_args.content_type
  if resource_args.md5_hash is not None:
    object_metadata.md5Hash = resource_args.md5_hash

  if (resource_args.encryption_key and
      resource_args.encryption_key.type == encryption_util.KeyType.CMEK):
    object_metadata.kmsKeyName = resource_args.encryption_key.key

  if resource_args.custom_metadata:
    messages = apis.GetMessagesModule('storage', 'v1')

    if not object_metadata.metadata:
      object_metadata.metadata = messages.Object.MetadataValue()
    for key, value in resource_args.custom_metadata.items():
      object_metadata.metadata.additionalProperties.append(
          messages.Object.MetadataValue.AdditionalProperty(
              key=key, value=value))
