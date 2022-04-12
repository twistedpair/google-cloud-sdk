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


class GcsBucketResource(resource_reference.BucketResource):
  """API-specific subclass for handling metadata."""

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
