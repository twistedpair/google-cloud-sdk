# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Gcloud-specific formatting of BucketResource and ObjectResource."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from googlecloudsdk.command_lib.storage.resources import full_resource_formatter as base


# Using literal strings as default so that they get displayed
# if the value is missing.
_NONE_STRING = 'None'

_PRESENT = 'Present'
_BUCKET_FIELDS_WITH_PRESENT_VALUE = (
    'cors_config',
    'encryption_config',
    'lifecycle_config',
    'logging_config',
    'retention_policy',
    'website_config')

_BUCKET_DISPLAY_TITLES_AND_DEFAULTS = (
    base.BucketDisplayTitlesAndDefaults(
        # Using literal string 'None' as default so that it gets displayed
        # if the value is missing.
        storage_class=base.FieldDisplayTitleAndDefault(
            title='Storage Class', default=None),
        location_type=base.FieldDisplayTitleAndDefault(
            title='Location Type', default=None),
        location=base.FieldDisplayTitleAndDefault(
            title='Location Constraint', default=_NONE_STRING),
        versioning_enabled=base.FieldDisplayTitleAndDefault(
            title='Versioning Enabled', default=_NONE_STRING),
        logging_config=base.FieldDisplayTitleAndDefault(
            title='Logging Configuration', default=_NONE_STRING),
        website_config=base.FieldDisplayTitleAndDefault(
            title='Website Configuration', default=_NONE_STRING),
        # Using literal string '[]' as default so that it gets displayed
        # if the value is missing.
        cors_config=base.FieldDisplayTitleAndDefault(
            title='CORS Configuration', default='[]'),
        encryption_config=base.FieldDisplayTitleAndDefault(
            title='Encryption Configuration', default=None),
        lifecycle_config=base.FieldDisplayTitleAndDefault(
            title='Lifecycle Configuration', default=_NONE_STRING),
        requester_pays=base.FieldDisplayTitleAndDefault(
            title='Requester Pays Enabled', default=_NONE_STRING),
        retention_policy=base.FieldDisplayTitleAndDefault(
            title='Retention Policy', default=None),
        default_event_based_hold=base.FieldDisplayTitleAndDefault(
            title='Default Event-Based Hold', default=None),
        labels=base.FieldDisplayTitleAndDefault(
            title='Labels', default=None),
        default_kms_key=base.FieldDisplayTitleAndDefault(
            title='Default KMS Key', default=_NONE_STRING),
        creation_time=base.FieldDisplayTitleAndDefault(
            title='Time Created', default=None),
        update_time=base.FieldDisplayTitleAndDefault(
            title='Time Updated', default=None),
        metageneration=base.FieldDisplayTitleAndDefault(
            title='Metageneration', default=None),
        bucket_policy_only_enabled=base.FieldDisplayTitleAndDefault(
            title='Bucket Policy Only Enabled', default=None,
            field_name='_bucket_policy_only_enabled'),
        satisifes_pzs=base.FieldDisplayTitleAndDefault(
            title='Satisfies PZS', default=None),
        acl=base.FieldDisplayTitleAndDefault(
            title='ACL', default='[]'),
        default_acl=base.FieldDisplayTitleAndDefault(
            title='Default ACL', default=None),
    ))


_OBJECT_DISPLAY_TITLES_AND_DEFAULTS = (
    base.ObjectDisplayTitlesAndDefaults(
        creation_time=base.FieldDisplayTitleAndDefault(
            title='Creation Time', default=None),
        update_time=base.FieldDisplayTitleAndDefault(
            title='Update Time', default=None),
        storage_class_update_time=base.FieldDisplayTitleAndDefault(
            title='Storage Class Update Time', default=None),
        storage_class=base.FieldDisplayTitleAndDefault(
            title='Storage Class', default=None),
        temporary_hold=base.FieldDisplayTitleAndDefault(
            title='Temporary Hold', default=None),
        event_based_hold=base.FieldDisplayTitleAndDefault(
            title='Event-Based Hold', default=None),
        retention_expiration=base.FieldDisplayTitleAndDefault(
            title='Retention Expiration', default=None),
        kms_key=base.FieldDisplayTitleAndDefault(title='KMS Key', default=None),
        cache_control=base.FieldDisplayTitleAndDefault(
            title='Cache-Control', default=None),
        content_disposition=base.FieldDisplayTitleAndDefault(
            title='Content-Disposition', default=None),
        content_encoding=base.FieldDisplayTitleAndDefault(
            title='Content-Encoding', default=None),
        content_language=base.FieldDisplayTitleAndDefault(
            title='Content-Language', default=None),
        content_length=base.FieldDisplayTitleAndDefault(
            title='Content-Length', default=_NONE_STRING),
        content_type=base.FieldDisplayTitleAndDefault(
            title='Content-Type', default=_NONE_STRING),
        component_count=base.FieldDisplayTitleAndDefault(
            title='Component-Count', default=None),
        custom_time=base.FieldDisplayTitleAndDefault(
            title='Custom-Time', default=None),
        noncurrent_time=base.FieldDisplayTitleAndDefault(
            title='Noncurrent Time', default=None),
        additional_properties=base.FieldDisplayTitleAndDefault(
            title='Additional Properties', default=None),
        crc32c_hash=base.FieldDisplayTitleAndDefault(
            title='Hash (CRC32C)', default=None),
        md5_hash=base.FieldDisplayTitleAndDefault(
            title='Hash (MD5)', default=None),
        encryption_algorithm=base.FieldDisplayTitleAndDefault(
            title='Encryption Algorithm', default=None),
        encryption_key_sha256=base.FieldDisplayTitleAndDefault(
            title='Encryption Key SHA256', default=None),
        etag=base.FieldDisplayTitleAndDefault(title='ETag', default='None'),
        generation=base.FieldDisplayTitleAndDefault(
            title='Generation', default=None),
        metageneration=base.FieldDisplayTitleAndDefault(
            title='Metageneration', default=None),
        acl=base.FieldDisplayTitleAndDefault(title='ACL', default=[]),
    ))


class GcloudFullResourceFormatter(base.FullResourceFormatter):
  """Format a resource as per Gcloud Storage style for ls -L output."""

  def format_bucket(self, url_string, displayable_bucket_data):
    """See super class."""
    # For some fields, we only display if the field is "Present".
    for field in _BUCKET_FIELDS_WITH_PRESENT_VALUE:
      value = getattr(displayable_bucket_data, field)
      # Checking for string because these feilds might have error strings.
      if value and not isinstance(value, str):
        setattr(displayable_bucket_data, field, _PRESENT)

    return base.get_formatted_string(
        url_string,
        displayable_bucket_data,
        _BUCKET_DISPLAY_TITLES_AND_DEFAULTS)

  def format_object(self, url_string, displayable_object_data):
    """See super class."""
    # Handle special case of missing hash for encrypted objects.
    # We check for _crc32c_hash value instead of crc32c_hash because we
    # want to be able to avoid displaying the field if it is explicitly set
    # to DO_NOT_DISPLAY.
    for key in ('md5_hash', '_crc32c_hash'):
      value = getattr(displayable_object_data, key, None)
      if (value is None and getattr(displayable_object_data,
                                    'encryption_algorithm', None) is not None):
        setattr(displayable_object_data, key, 'Underlying data encrypted')

    return base.get_formatted_string(
        url_string,
        displayable_object_data,
        _OBJECT_DISPLAY_TITLES_AND_DEFAULTS)
