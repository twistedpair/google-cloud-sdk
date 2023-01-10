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
  # TODO(b/246556206): Remove.
  if message is not None:
    result = encoding.MessageToDict(message)
    # Explicit comparison is needed because we don't want to return None for
    # False values.
    if result == []:  # pylint: disable=g-explicit-bool-comparison
      return None
    return result
  return None


class GcsBucketResource(resource_reference.BucketResource):
  """API-specific subclass for handling metadata.

  Additional GCS Attributes:
    autoclass_enabled_time (datetime|None): Datetime autoclass feature was
      enabled on bucket. None means the feature is disabled.
    custom_placement_config (dict|None): Dual Region of a bucket.
    default_acl (dict|None): Default object ACLs for the bucket.
    default_kms_key (str|None): Default KMS key for objects in the bucket.
    location_type (str|None): Region, dual-region, etc.
    project_number (int|None): The project number to which the bucket belongs
      (different from project name and project ID).
    public_access_prevention (str|None): Public access prevention status.
    rpo (str|None): Recovery Point Objective status.
    satisfies_pzs (bool|None): Zone Separation status.
    uniform_bucket_level_access (bool|None): True if all objects in the bucket
      share ACLs rather than the default, fine-grain ACL control.
  """

  def __init__(self,
               storage_url_object,
               acl=None,
               autoclass_enabled_time=None,
               cors_config=None,
               creation_time=None,
               custom_placement_config=None,
               default_acl=None,
               default_event_based_hold=None,
               default_kms_key=None,
               default_storage_class=None,
               etag=None,
               labels=None,
               lifecycle_config=None,
               location=None,
               location_type=None,
               logging_config=None,
               metadata=None,
               metageneration=None,
               project_number=None,
               public_access_prevention=None,
               requester_pays=None,
               retention_policy=None,
               rpo=None,
               satisfies_pzs=None,
               uniform_bucket_level_access=None,
               update_time=None,
               versioning_enabled=None,
               website_config=None):
    """Initializes resource. Args are a subset of attributes."""
    super(GcsBucketResource, self).__init__(
        storage_url_object,
        acl=acl,
        cors_config=cors_config,
        creation_time=creation_time,
        default_event_based_hold=default_event_based_hold,
        default_storage_class=default_storage_class,
        etag=etag,
        labels=labels,
        lifecycle_config=lifecycle_config,
        location=location,
        logging_config=logging_config,
        metageneration=metageneration,
        metadata=metadata,
        requester_pays=requester_pays,
        retention_policy=retention_policy,
        update_time=update_time,
        versioning_enabled=versioning_enabled,
        website_config=website_config,
    )
    self.autoclass_enabled_time = autoclass_enabled_time
    self.custom_placement_config = custom_placement_config
    self.default_acl = default_acl
    self.default_kms_key = default_kms_key
    self.location_type = location_type
    self.project_number = project_number
    self.public_access_prevention = public_access_prevention
    self.rpo = rpo
    self.satisfies_pzs = satisfies_pzs
    self.uniform_bucket_level_access = uniform_bucket_level_access

  @property
  def data_locations(self):
    if self.custom_placement_config:
      return self.custom_placement_config.get('dataLocations')
    return None

  @property
  def retention_period(self):
    if self.retention_policy and self.retention_policy.get('retentionPeriod'):
      return int(self.retention_policy['retentionPeriod'])
    return None

  @property
  def retention_policy_is_locked(self):
    return (self.retention_policy and
            self.retention_policy.get('isLocked', False))

  def get_displayable_bucket_data(self):
    """Returns the DisplaybleBucketData instance."""
    # TODO(b/240444753): Make better use of ObjectResource attributes.
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
        satisfies_pzs=self.metadata.satisfiesPZS,
        storage_class=self.metadata.storageClass,
        update_time=self.metadata.updated,
        versioning_enabled=(self.metadata.versioning and
                            self.metadata.versioning.enabled),
        website_config=_message_to_dict(self.metadata.website))

  def __eq__(self, other):
    return (
        super(GcsBucketResource, self).__eq__(other) and
        self.autoclass_enabled_time == other.autoclass_enabled_time and
        self.custom_placement_config == other.custom_placement_config and
        self.default_acl == other.default_acl and
        self.default_kms_key == other.default_kms_key and
        self.location_type == other.location_type and
        self.project_number == other.project_number and
        self.public_access_prevention == other.public_access_prevention and
        self.rpo == other.rpo and self.satisfies_pzs == other.satisfies_pzs and
        self.uniform_bucket_level_access == other.uniform_bucket_level_access)

  def get_json_dump(self):
    return _get_json_dump(self)


class GcsHmacKeyResource:
  """Holds HMAC key metadata."""

  def __init__(self, metadata):
    self.metadata = metadata

  @property
  def access_id(self):
    key_metadata = getattr(self.metadata, 'metadata', None)
    return getattr(key_metadata, 'accessId', None)

  @property
  def secret(self):
    return getattr(self.metadata, 'secret', None)

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return self.metadata == other.metadata


class GcsObjectResource(resource_reference.ObjectResource):
  """API-specific subclass for handling metadata.

  Additional GCS Attributes:
    storage_class_update_time (datetime|None): Storage class update time.
  """

  def __init__(self,
               storage_url_object,
               acl=None,
               cache_control=None,
               component_count=None,
               content_disposition=None,
               content_encoding=None,
               content_language=None,
               content_type=None,
               crc32c_hash=None,
               creation_time=None,
               custom_fields=None,
               custom_time=None,
               decryption_key_hash_sha256=None,
               encryption_algorithm=None,
               etag=None,
               event_based_hold=None,
               kms_key=None,
               md5_hash=None,
               metadata=None,
               metageneration=None,
               noncurrent_time=None,
               retention_expiration=None,
               size=None,
               storage_class=None,
               storage_class_update_time=None,
               temporary_hold=None,
               update_time=None):
    """Initializes GcsObjectResource."""
    super(GcsObjectResource, self).__init__(
        storage_url_object,
        acl,
        cache_control,
        component_count,
        content_disposition,
        content_encoding,
        content_language,
        content_type,
        crc32c_hash,
        creation_time,
        custom_fields,
        custom_time,
        decryption_key_hash_sha256,
        encryption_algorithm,
        etag,
        event_based_hold,
        kms_key,
        md5_hash,
        metadata,
        metageneration,
        noncurrent_time,
        retention_expiration,
        size,
        storage_class,
        temporary_hold,
        update_time,
    )
    self.storage_class_update_time = storage_class_update_time

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
        event_based_hold=True if self.metadata.eventBasedHold else None,
        generation=self.generation,
        kms_key=self.metadata.kmsKeyName,
        md5_hash=self.metadata.md5Hash,
        metageneration=self.metageneration,
        noncurrent_time=self.metadata.timeDeleted,
        retention_expiration=self.metadata.retentionExpirationTime,
        storage_class=self.metadata.storageClass,
        storage_class_update_time=self.metadata.timeStorageClassUpdated,
        temporary_hold=True if self.metadata.temporaryHold else None,
        update_time=self.metadata.updated)

  def __eq__(self, other):
    return (super(GcsObjectResource, self).__eq__(other) and
            self.storage_class_update_time == other.storage_class_update_time)

  def get_json_dump(self):
    return _get_json_dump(self)

  def is_encrypted(self):
    cmek_in_metadata = self.metadata.kmsKeyName if self.metadata else False
    return cmek_in_metadata or self.decryption_key_hash_sha256
