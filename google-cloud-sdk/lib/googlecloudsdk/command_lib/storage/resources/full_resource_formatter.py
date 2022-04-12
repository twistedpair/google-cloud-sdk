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
"""Base class for handling ls -L formatting of CloudResource."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import collections
import datetime

from googlecloudsdk.command_lib.storage.resources import resource_util

import six


class FieldDisplayTitleAndDefault(object):
  """Holds the title and default value to be displayed for a resource field."""

  def __init__(self, title, default, field_name=None):
    """Initializes FieldDisplayTitleAndDefault.

    Args:
      title (str): The title for the field.
      default (str): The default value to be used if value is missing.
      field_name (str|None): The field name to be used to extract
        the data from DisplayableResourceData object.
        If None, the field name from BucketDisplayTitlesAndDefaults or
        ObjectDisplayTitlesAndDefaults is used.
    """
    self.title = title
    self.default = default
    self.field_name = field_name


# Determines the order in which the fields should be displayed for
# a BucketResource.
BucketDisplayTitlesAndDefaults = collections.namedtuple(
    'BucketDisplayTitlesAndDefaults', (
        'storage_class',
        'location_type',
        'location',
        'versioning_enabled',
        'logging_config',
        'website_config',
        'cors_config',
        'encryption_config',
        'lifecycle_config',
        'requester_pays',
        'retention_policy',
        'default_event_based_hold',
        'labels',
        'default_kms_key',
        'creation_time',
        'update_time',
        'metageneration',
        'bucket_policy_only_enabled',
        'satisifes_pzs',
        'acl',
        'default_acl',
    ))


# Determines the order in which the fields should be displayed for
# an ObjectResource.
ObjectDisplayTitlesAndDefaults = collections.namedtuple(
    'ObjectDisplayTitlesAndDefaults', (
        'creation_time',
        'update_time',
        'storage_class_update_time',
        'storage_class',
        'temporary_hold',
        'event_based_hold',
        'retention_expiration',
        'kms_key',
        'cache_control',
        'content_disposition',
        'content_encoding',
        'content_language',
        'content_length',
        'content_type',
        'component_count',
        'custom_time',
        'noncurrent_time',
        'additional_properties',
        'crc32c_hash',
        'md5_hash',
        'encryption_algorithm',
        'encryption_key_sha256',
        'etag',
        'generation',
        'metageneration',
        'acl',
    ))


def _get_formatted_line(display_name, value, default_value=None):
  """Returns a formatted line for ls -L output."""
  if value is not None:
    if value and (isinstance(value, dict) or isinstance(value, list)):
      return resource_util.get_metadata_json_section_string(display_name, value)
    elif isinstance(value, datetime.datetime):
      return resource_util.get_padded_metadata_time_line(display_name, value)
    else:
      return resource_util.get_padded_metadata_key_value_line(
          display_name, value)
  elif default_value is not None:
    return resource_util.get_padded_metadata_key_value_line(
        display_name, default_value)
  return None


def get_formatted_string(url_string, displayable_resource_data,
                         display_titles_and_defaults):
  """Returns the formatted string representing the resource.

  Args:
    url_string (str): URL string representing the resource.
    displayable_resource_data (resource_reference.DisplayableResourceData):
      Object holding resource metadata that needs to be displayed.
    display_titles_and_defaults (ObjectDisplayTitlesAndDefaults): Holds the
      display titles and default values for each field present in
      DisplayableResourceData.

  Returns:
    A string representing the Resource for ls -L command.
  """
  lines = []
  # In namedtuple, to prevent conflicts with field names,
  # the method and attribute names start with an underscore.
  for key in display_titles_and_defaults._fields:
    field_display_title_and_default = getattr(display_titles_and_defaults, key)

    # The field_name present in field_display_title_and_default takes
    # precedence over the key in display_titles_and_defaults.
    if field_display_title_and_default.field_name is not None:
      field_name = field_display_title_and_default.field_name
    else:
      field_name = key

    value = getattr(displayable_resource_data, field_name, None)
    line = _get_formatted_line(
        field_display_title_and_default.title,
        value,
        field_display_title_and_default.default)
    if line:
      lines.append(line)

  # The data to be displayed might be incomplete.
  # TODO(b/228209680) Log a single warning in the end.
  incomplete_warning = displayable_resource_data.get_incomplete_warning()
  if incomplete_warning is not None:
    lines.append(resource_util.METADATA_LINE_INDENT_STRING + incomplete_warning)

  return ('{url_string}:\n'
          '{fields}').format(
              url_string=url_string,
              fields='\n'.join(lines))


class FullResourceFormatter(six.with_metaclass(abc.ABCMeta, object)):
  """Base class for a formatter to format the Resource object.

  This FullResourceFormatter is specifically used for ls -L output formatting.
  """

  def format_bucket(self, url_string, displayable_bucket_data):
    """Returns a formatted string representing the BucketResource.

    Args:
      url_string (str): String representing the object.
      displayable_bucket_data (resource_reference.DisplayableBucketData): A
        DisplayableBucketData instance.

    Returns:
      Formatted multi-line string representing the BucketResource.
    """
    raise NotImplementedError('format_bucket must be overridden.')

  def format_object(self, url_string, displayable_object_data):
    """Returns a formatted string representing the ObjectResource.

    Args:
      url_string (str): String representing the object.
      displayable_object_data (resource_reference.DisplayableResourceData): A
        DisplayableObjectData instance.

    Returns:
      Formatted multi-line string represnting the ObjectResource.
    """
    raise NotImplementedError('format_object must be overridden.')
