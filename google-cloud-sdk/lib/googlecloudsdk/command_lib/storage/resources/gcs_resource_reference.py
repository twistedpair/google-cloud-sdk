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
"""GCS API-specific resource subclasses."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import json

from apitools.base.py import encoding

from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.command_lib.storage.resources import resource_util


def _json_dump_helper(metadata):
  """See _get_json_dump docstring."""
  return json.loads(encoding.MessageToJson(metadata))


def _get_json_dump(resource):
  """Formats GCS resource metadata for printing.

  Args:
    resource (GcsBucketResource|GcsObjectResource): Resource object.

  Returns:
    Formatted JSON string for printing.
  """
  return resource_util.configured_json_dumps(
      collections.OrderedDict([
          ('url', resource.storage_url.url_string),
          ('type', resource.TYPE_STRING),
          ('metadata', _json_dump_helper(resource.metadata)),
      ]))


def _message_to_dict(message):
  """Converts message to dict. Returns None is message is None."""
  if message is not None:
    result = encoding.MessageToDict(message)
    # Explicit comparison is needed because we don't want to return None for
    # False values.
    if result == []:  # pylint: disable=g-explicit-bool-comparison
      return None
    return result
  return None


def _get_full_bucket_metadata_string(resource):
  """Formats GCS resource metadata as string with rows.

  Args:
    resource (GCSBucketResource): Resource with metadata.

  Returns:
    Formatted multi-line string.
  """
  # Heavily-formatted sections.
  if resource.metadata.labels:
    labels_section = resource_util.get_metadata_json_section_string(
        'Labels', resource.metadata.labels, _json_dump_helper)
  else:
    labels_section = resource_util.get_padded_metadata_key_value_line(
        'Labels', 'None')

  if resource.metadata.acl:
    acl_section = resource_util.get_metadata_json_section_string(
        'ACL', resource.metadata.acl, _json_dump_helper)
  else:
    acl_section = resource_util.get_padded_metadata_key_value_line('ACL', '[]')

  if resource.metadata.defaultObjectAcl:
    default_acl_section = resource_util.get_metadata_json_section_string(
        'Default ACL', resource.metadata.defaultObjectAcl, _json_dump_helper)
  else:
    default_acl_section = resource_util.get_padded_metadata_key_value_line(
        'Default ACL', '[]')

  # Optional lines. Include all formatting since their presence is conditional.
  if resource.metadata.locationType is not None:
    optional_location_type_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Location Type', resource.metadata.locationType))
  else:
    optional_location_type_line = ''

  if resource.metadata.retentionPolicy is not None:
    optional_retention_policy_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Retention Policy', 'Present'))
  else:
    optional_retention_policy_line = ''

  if resource.metadata.defaultEventBasedHold:
    # Boolean. Only show for True.
    optional_default_event_based_hold_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Default Event-Based Hold',
            resource.metadata.defaultEventBasedHold))
  else:
    optional_default_event_based_hold_line = ''

  if resource.metadata.timeCreated is not None:
    optional_time_created_line = resource_util.get_padded_metadata_time_line(
        'Time Created', resource.metadata.timeCreated)
  else:
    optional_time_created_line = ''

  if resource.metadata.updated is not None:
    optional_time_updated_line = resource_util.get_padded_metadata_time_line(
        'Time Updated', resource.metadata.updated)
  else:
    optional_time_updated_line = ''

  if resource.metadata.metageneration is not None:
    optional_metageneration_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Metageneration', resource.metadata.metageneration))
  else:
    optional_metageneration_line = ''

  bucket_policy_only_object = getattr(resource.metadata.iamConfiguration,
                                      'bucketPolicyOnly', None)
  if bucket_policy_only_object is not None:
    optional_bucket_policy_only_enabled_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Bucket Policy Only Enabled', bucket_policy_only_object.enabled))
  else:
    optional_bucket_policy_only_enabled_line = ''

  if resource.metadata.satisfiesPZS is not None:
    optional_satisfies_pzs_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Satisfies PZS', resource.metadata.satisfiesPZS))
  else:
    optional_satisfies_pzs_line = ''

  return (
      '{bucket_url}:\n'
      '{storage_class_line}'
      '{optional_location_type_line}'
      '{location_constraint_line}'
      '{versioning_enabled_line}'
      '{logging_config_line}'
      '{website_config_line}'
      '{cors_config_line}'
      '{lifecycle_config_line}'
      '{requester_pays_line}'
      '{optional_retention_policy_line}'
      '{optional_default_event_based_hold_line}'
      '{labels_section}'
      '{default_kms_key_line}'
      '{optional_time_created_line}'
      '{optional_time_updated_line}'
      '{optional_metageneration_line}'
      '{optional_bucket_policy_only_enabled_line}'
      '{optional_satisfies_pzs_line}'
      '{acl_section}'
      '{default_acl_section}'
  ).format(
      bucket_url=resource.storage_url.versionless_url_string,
      storage_class_line=resource_util.get_padded_metadata_key_value_line(
          'Storage Class', resource.metadata.storageClass),
      optional_location_type_line=optional_location_type_line,
      location_constraint_line=resource_util.get_padded_metadata_key_value_line(
          'Location Constraint', resource.metadata.location),
      versioning_enabled_line=resource_util.get_padded_metadata_key_value_line(
          'Versioning Enabled', (resource.metadata.versioning and
                                 resource.metadata.versioning.enabled)),
      logging_config_line=resource_util.get_padded_metadata_key_value_line(
          'Logging Configuration',
          resource_util.get_exists_string(resource.metadata.logging)),
      website_config_line=resource_util.get_padded_metadata_key_value_line(
          'Website Configuration',
          resource_util.get_exists_string(resource.metadata.website)),
      cors_config_line=resource_util.get_padded_metadata_key_value_line(
          'CORS Configuration',
          resource_util.get_exists_string(resource.metadata.cors)),
      lifecycle_config_line=resource_util.get_padded_metadata_key_value_line(
          'Lifecycle Configuration',
          resource_util.get_exists_string(resource.metadata.lifecycle)),
      requester_pays_line=resource_util.get_padded_metadata_key_value_line(
          'Requester Pays Enabled', (resource.metadata.billing and
                                     resource.metadata.billing.requesterPays)),
      optional_retention_policy_line=optional_retention_policy_line,
      optional_default_event_based_hold_line=(
          optional_default_event_based_hold_line),
      labels_section=labels_section,
      default_kms_key_line=resource_util.get_padded_metadata_key_value_line(
          'Default KMS Key',
          resource_util.get_exists_string(
              getattr(resource.metadata.encryption, 'defaultKmsKeyName',
                      None))),
      optional_time_created_line=optional_time_created_line,
      optional_time_updated_line=optional_time_updated_line,
      optional_metageneration_line=optional_metageneration_line,
      optional_bucket_policy_only_enabled_line=(
          optional_bucket_policy_only_enabled_line),
      optional_satisfies_pzs_line=optional_satisfies_pzs_line,
      acl_section=acl_section,
      # Remove ending newline character because this is the last list item.
      default_acl_section=default_acl_section[:-1])


def _get_full_object_metadata_string(resource):
  """Formats GCS resource metadata as string with rows.

  Args:
    resource (GCSObjectResource): Resource with metadata.

  Returns:
    Formatted multi-line string.
  """
  # Non-optional item that will always display.
  if resource.metadata.acl:
    acl_section = resource_util.get_metadata_json_section_string(
        'ACL', resource.metadata.acl, _json_dump_helper)
  else:
    acl_section = resource_util.get_padded_metadata_key_value_line('ACL', '[]')

  # Optional items that will conditionally display.
  if resource.creation_time is not None:
    optional_time_created_line = resource_util.get_padded_metadata_time_line(
        'Creation Time', resource.creation_time)
  else:
    optional_time_created_line = ''

  if resource.metadata.updated is not None:
    optional_time_updated_line = resource_util.get_padded_metadata_time_line(
        'Update Time', resource.metadata.updated)
  else:
    optional_time_updated_line = ''

  if resource.metadata.timeStorageClassUpdated is not None and (
      resource.metadata.timeStorageClassUpdated !=
      resource.metadata.timeCreated):
    optional_time_storage_class_created_line = (
        resource_util.get_padded_metadata_time_line(
            'Storage Class Update Time',
            resource.metadata.timeStorageClassUpdated))
  else:
    optional_time_storage_class_created_line = ''

  if resource.metadata.storageClass is not None:
    optional_storage_class_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Storage Class', resource.metadata.storageClass))
  else:
    optional_storage_class_line = ''

  if resource.metadata.temporaryHold is not None:
    optional_temporary_hold_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Temporary Hold', resource.metadata.temporaryHold))
  else:
    optional_temporary_hold_line = ''

  if resource.metadata.eventBasedHold is not None:
    optional_event_based_hold_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Event-Based Hold', resource.metadata.eventBasedHold))
  else:
    optional_event_based_hold_line = ''

  if resource.metadata.retentionExpirationTime is not None:
    optional_retention_expiration_time_line = (
        resource_util.get_padded_metadata_time_line(
            'Retention Expiration', resource.metadata.retentionExpirationTime))
  else:
    optional_retention_expiration_time_line = ''

  if resource.metadata.kmsKeyName is not None:
    optional_kms_key_name_line = (
        resource_util.get_padded_metadata_key_value_line(
            'KMS Key', resource.metadata.kmsKeyName))
  else:
    optional_kms_key_name_line = ''

  if resource.metadata.cacheControl is not None:
    optional_cache_control_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Cache-Control', resource.metadata.cacheControl))
  else:
    optional_cache_control_line = ''

  if resource.metadata.contentDisposition is not None:
    optional_content_disposition_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Cache-Disposition', resource.metadata.contentDisposition))
  else:
    optional_content_disposition_line = ''

  if resource.metadata.contentEncoding is not None:
    optional_content_encoding_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Content-Encoding', resource.metadata.contentEncoding))
  else:
    optional_content_encoding_line = ''

  if resource.metadata.contentLanguage is not None:
    optional_content_language_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Content-Language', resource.metadata.contentLanguage))
  else:
    optional_content_language_line = ''

  if resource.metadata.componentCount is not None:
    optional_component_count_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Component-Count', resource.metadata.componentCount))
  else:
    optional_component_count_line = ''

  if resource.metadata.customTime is not None:
    optional_custom_time_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Custom-Time', resource.metadata.customTime))
  else:
    optional_custom_time_line = ''

  if resource.metadata.timeDeleted is not None:
    optional_noncurrent_time_line = resource_util.get_padded_metadata_time_line(
        'Noncurrent Time', resource.metadata.timeDeleted)
  else:
    optional_noncurrent_time_line = ''

  if getattr(resource.metadata.metadata, 'additionalProperties', None):
    optional_metadata_section = resource_util.get_metadata_json_section_string(
        'Additional Properties',
        resource.metadata.metadata.additionalProperties, _json_dump_helper)
  else:
    optional_metadata_section = ''

  if resource.metadata.crc32c is not None:
    optional_crc32c_line = resource_util.get_padded_metadata_key_value_line(
        'Hash (CRC32C)', resource.metadata.crc32c)
  else:
    if resource.metadata.customerEncryption:
      optional_crc32c_line = resource_util.get_padded_metadata_key_value_line(
          'Hash (CRC32C)', 'Underlying data encrypted')
    else:
      optional_crc32c_line = ''

  if resource.metadata.md5Hash is not None:
    optional_md5_line = resource_util.get_padded_metadata_key_value_line(
        'Hash (MD5)', resource.metadata.md5Hash)
  else:
    if resource.metadata.customerEncryption is not None:
      optional_md5_line = resource_util.get_padded_metadata_key_value_line(
          'Hash (MD5)', 'Underlying data encrypted')
    else:
      optional_md5_line = ''

  if getattr(resource.metadata.customerEncryption, 'encryptionAlgorithm', None):
    optional_encryption_algorithm_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Encryption Algorithm',
            resource.metadata.customerEncryption.encryptionAlgorithm))
  else:
    optional_encryption_algorithm_line = ''

  if getattr(resource.metadata.customerEncryption, 'keySha256', None):
    optional_encryption_key_sha_256_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Encryption Key SHA256',
            resource.metadata.customerEncryption.keySha256))
  else:
    optional_encryption_key_sha_256_line = ''

  if resource.generation is not None:
    optional_generation_line = resource_util.get_padded_metadata_key_value_line(
        'Generation', resource.generation)
  else:
    optional_generation_line = ''

  if resource.metageneration is not None:
    optional_metageneration_line = (
        resource_util.get_padded_metadata_key_value_line(
            'Metageneration', resource.metageneration))
  else:
    optional_metageneration_line = ''

  return (
      '{object_url}:\n'
      '{optional_time_created_line}'
      '{optional_time_updated_line}'
      '{optional_time_storage_class_created_line}'
      '{optional_storage_class_line}'
      '{optional_temporary_hold_line}'
      '{optional_event_based_hold_line}'
      '{optional_retention_expiration_time_line}'
      '{optional_kms_key_name_line}'
      '{optional_cache_control_line}'
      '{optional_content_disposition_line}'
      '{optional_content_encoding_line}'
      '{optional_content_language_line}'
      '{content_length_line}'
      '{content_type_line}'
      '{optional_component_count_line}'
      '{optional_custom_time_line}'
      '{optional_noncurrent_time_line}'
      '{optional_metadata_section}'
      '{optional_crc32c_line}'
      '{optional_md5_line}'
      '{optional_encryption_algorithm_line}'
      '{optional_encryption_key_sha_256_line}'
      '{etag_line}'
      '{optional_generation_line}'
      '{optional_metageneration_line}'
      '{acl_section}'
  ).format(
      object_url=resource.storage_url.versionless_url_string,
      optional_time_created_line=optional_time_created_line,
      optional_time_updated_line=optional_time_updated_line,
      optional_time_storage_class_created_line=(
          optional_time_storage_class_created_line),
      optional_storage_class_line=optional_storage_class_line,
      optional_temporary_hold_line=optional_temporary_hold_line,
      optional_event_based_hold_line=optional_event_based_hold_line,
      optional_retention_expiration_time_line=(
          optional_retention_expiration_time_line),
      optional_kms_key_name_line=optional_kms_key_name_line,
      optional_cache_control_line=optional_cache_control_line,
      optional_content_disposition_line=optional_content_disposition_line,
      optional_content_encoding_line=optional_content_encoding_line,
      optional_content_language_line=optional_content_language_line,
      content_length_line=resource_util.get_padded_metadata_key_value_line(
          'Content-Length', resource.size),
      content_type_line=resource_util.get_padded_metadata_key_value_line(
          'Content-Type', resource.metadata.contentType),
      optional_component_count_line=optional_component_count_line,
      optional_custom_time_line=optional_custom_time_line,
      optional_noncurrent_time_line=optional_noncurrent_time_line,
      optional_metadata_section=optional_metadata_section,
      optional_crc32c_line=optional_crc32c_line,
      optional_md5_line=optional_md5_line,
      optional_encryption_algorithm_line=optional_encryption_algorithm_line,
      optional_encryption_key_sha_256_line=optional_encryption_key_sha_256_line,
      etag_line=resource_util.get_padded_metadata_key_value_line(
          'ETag', resource.etag),
      optional_generation_line=optional_generation_line,
      optional_metageneration_line=optional_metageneration_line,
      # Remove ending newline character because this is the last list item.
      acl_section=acl_section[:-1])


class GcsBucketResource(resource_reference.BucketResource):
  """API-specific subclass for handling metadata."""

  def get_full_metadata_string(self):
    return _get_full_bucket_metadata_string(self)

  def get_displayable_bucket_data(self):
    """Returns the DisplaybleBucketData instance."""
    if self.metadata.labels is not None:
      labels = encoding.MessageToDict(self.metadata.labels)
    else:
      labels = None

    iam_configuration = self.metadata.iamConfiguration

    return resource_reference.DisplayableBucketData(
        name=self.name,
        url_string=self.storage_url.url_string,
        acl=_message_to_dict(self.metadata.acl),
        bucket_policy_only=_message_to_dict(
            getattr(iam_configuration, 'bucketPolicyOnly', None)),
        cors_config=_message_to_dict(self.metadata.cors),
        creation_time=self.metadata.timeCreated,
        default_acl=_message_to_dict(self.metadata.defaultObjectAcl),
        default_event_based_hold=self.metadata.defaultEventBasedHold,
        default_kms_key=getattr(self.metadata.encryption, 'defaultKmsKeyName',
                                None),
        etag=self.metadata.etag,
        labels=labels,
        lifecycle_config=_message_to_dict(self.metadata.lifecycle),
        location=self.metadata.location,
        location_type=self.metadata.locationType,
        logging_config=_message_to_dict(self.metadata.logging),
        metageneration=self.metadata.metageneration,
        project_number=self.metadata.projectNumber,
        public_access_prevention=getattr(iam_configuration,
                                         'publicAccessPrevention', None),
        requester_pays=(self.metadata.billing and
                        self.metadata.billing.requesterPays),
        retention_policy=_message_to_dict(self.metadata.retentionPolicy),
        rpo=self.metadata.rpo,
        satisifes_pzs=self.metadata.satisfiesPZS,
        storage_class=self.metadata.storageClass,
        update_time=self.metadata.updated,
        versioning_enabled=(self.metadata.versioning and
                            self.metadata.versioning.enabled),
        website_config=_message_to_dict(self.metadata.website))

  def get_json_dump(self):
    return _get_json_dump(self)


class GcsObjectResource(resource_reference.ObjectResource):
  """API-specific subclass for handling metadata."""

  def get_full_metadata_string(self):
    return _get_full_object_metadata_string(self)

  def get_displayable_object_data(self):
    """Returns the DisplaybleObjectData instance."""
    if getattr(self.metadata.metadata, 'additionalProperties', None):
      additional_properties = _message_to_dict(
          self.metadata.metadata.additionalProperties)
    else:
      additional_properties = None

    return resource_reference.DisplayableObjectData(
        name=self.name,
        bucket=self.bucket,
        url_string=self.storage_url.url_string,
        acl=_message_to_dict(self.metadata.acl),
        additional_properties=additional_properties,
        cache_control=self.metadata.cacheControl,
        component_count=self.metadata.componentCount,
        content_disposition=self.metadata.contentDisposition,
        content_encoding=self.metadata.contentEncoding,
        content_language=self.metadata.contentLanguage,
        content_length=self.size,
        content_type=self.metadata.contentType,
        crc32c_hash=self.metadata.crc32c,
        creation_time=self.creation_time,
        custom_time=self.metadata.customTime,
        encryption_algorithm=getattr(self.metadata.customerEncryption,
                                     'encryptionAlgorithm', None),
        encryption_key_sha256=getattr(self.metadata.customerEncryption,
                                      'keySha256', None),
        etag=self.etag,
        event_based_hold=self.metadata.eventBasedHold,
        generation=self.generation,
        kms_key=self.metadata.kmsKeyName,
        md5_hash=self.metadata.md5Hash,
        metageneration=self.metageneration,
        noncurrent_time=self.metadata.timeDeleted,
        retention_expiration=self.metadata.retentionExpirationTime,
        storage_class=self.metadata.storageClass,
        storage_class_update_time=self.metadata.timeStorageClassUpdated,
        temporary_hold=self.metadata.temporaryHold,
        update_time=self.metadata.updated)

  def get_json_dump(self):
    return _get_json_dump(self)

  def is_encrypted(self):
    cmek_in_metadata = self.metadata.kmsKeyName if self.metadata else False
    return cmek_in_metadata or self.decryption_key_hash
