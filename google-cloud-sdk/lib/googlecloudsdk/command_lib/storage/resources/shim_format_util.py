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
"""Shim-related utils for storage resource formatters."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime

from googlecloudsdk.command_lib.storage.resources import resource_util
from googlecloudsdk.core.util import scaled_integer

_BUCKET_FIELDS_WITH_PRESENT_VALUE = ('cors_config', 'lifecycle_config',
                                     'logging_config', 'retention_policy',
                                     'website_config')
_BYTE_EXPONENTS_AND_UNIT_STRINGS = [
    (0, 'B'),
    (10, 'KiB'),
    (20, 'MiB'),
    (30, 'GiB'),
    (40, 'TiB'),
    (50, 'PiB'),
    (60, 'EiB'),
]
# Using literal strings as default so that they get displayed
# if the value is missing.
NONE_STRING = 'None'
EMPTY_LIST_STRING = '[]'
PRESENT_STRING = 'Present'


def _gsutil_format_byte_values(byte_count):
  """Generates a gsutil-style human-readable string for a number of bytes."""
  final_exponent, final_unit_string = _BYTE_EXPONENTS_AND_UNIT_STRINGS[0]
  for exponent, unit_string in _BYTE_EXPONENTS_AND_UNIT_STRINGS:
    if byte_count < 2**exponent:
      break
    final_exponent = exponent
    final_unit_string = unit_string

  rounded_number = round(byte_count / 2**final_exponent, 2)
  return '{:g} {}'.format(rounded_number, final_unit_string)


def get_human_readable_byte_value(byte_count, use_gsutil_style=False):
  """Generates a string for bytes with human-readable units.

  Args:
    byte_count (int): A number of bytes to format.
    use_gsutil_style (bool): Outputs units in the style of the gsutil CLI (e.g.
      gcloud -> "1.00kiB", gsutil -> "1 KiB").

  Returns:
    A string form of the number using size abbreviations (KiB, MiB, etc).
  """
  if use_gsutil_style:
    return _gsutil_format_byte_values(byte_count)
  return scaled_integer.FormatBinaryNumber(byte_count, decimal_places=2)


def replace_bucket_values_with_present_string(displayable_bucket_data):
  """Updates fields with complex data to a simple 'Present' string."""
  for field in _BUCKET_FIELDS_WITH_PRESENT_VALUE:
    value = getattr(displayable_bucket_data, field)
    # Checking for string because these fields might have error strings.
    if value and not isinstance(value, str):
      setattr(displayable_bucket_data, field, PRESENT_STRING)


def replace_object_values_with_encryption_string(displayable_object_data,
                                                 encrypted_marker_string):
  """Updates fields to reflect that they are encrypted."""
  if displayable_object_data.encryption_algorithm is None:
    return
  # Handle special case of missing hash for encrypted objects.
  # We check for _crc32c_hash value instead of crc32c_hash because we
  # want to be able to avoid displaying the field if it is explicitly set
  # to DO_NOT_DISPLAY.
  for key in ('md5_hash', '_crc32c_hash'):
    if getattr(displayable_object_data, key) is None:
      setattr(displayable_object_data, key, encrypted_marker_string)


def replace_time_values_with_gsutil_style_strings(displayable_resource_data):
  """Updates fields in gcloud time format to gsutil time format."""
  # Convert "2022-06-30T16:02:49Z" to "Thu, 30 Jun 2022 16:02:49 GMT".
  for key in (
      'creation_time',
      'custom_time',
      'noncurrent_time',
      'retention_expiration',
      'storage_class_update_time',
      'update_time',
  ):
    gcloud_datetime_string = getattr(displayable_resource_data, key, None)
    if gcloud_datetime_string is not None:
      datetime_object = datetime.datetime.strptime(gcloud_datetime_string,
                                                   '%Y-%m-%dT%H:%M:%SZ')
      setattr(displayable_resource_data, key,
              datetime_object.strftime('%a, %d %b %Y %H:%M:%S GMT'))


def reformat_custom_metadata_for_gsutil(displayable_object_data):
  """Reformats custom metadata full format string in gsutil style."""
  metadata = displayable_object_data.additional_properties
  if not metadata:
    return

  if isinstance(metadata, dict):
    iterable_metadata = metadata.items()
  else:
    # Assuming GCS format: [{"key": "_", "value": "_"}, ...]
    iterable_metadata = [(d['key'], d['value']) for d in metadata]

  metadata_lines = []
  for k, v in iterable_metadata:
    metadata_lines.append(
        resource_util.get_padded_metadata_key_value_line(k, v, extra_indent=2))
  displayable_object_data.additional_properties = '\n' + '\n'.join(
      metadata_lines)
