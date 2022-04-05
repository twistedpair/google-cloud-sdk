# -*- coding: utf-8 -*- #
# Copyright 2021 Google Inc. All Rights Reserved.
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
"""Utils for generating API-specific RequestConfig objects."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum

from googlecloudsdk.core.util import debug_output


CLEAR = '_CLEAR'
GZIP_IN_FLIGHT_ALL = '_GZIP_IN_FLIGHT_ALL'


class MetadataType(enum.Enum):
  BUCKET = 'bucket'
  OBJECT = 'object'


class _UserBucketArgs:
  """Contains user flag values affecting cloud bucket settings."""

  def __init__(self,
               cors_file_path=None,
               default_encryption_key=None,
               default_event_based_hold=None,
               default_storage_class=None,
               labels_file_path=None,
               labels_to_append=None,
               labels_to_remove=None,
               lifecycle_file_path=None,
               location=None,
               log_bucket=None,
               log_object_prefix=None,
               requester_pays=None,
               retention_period=None,
               uniform_bucket_level_access=None,
               versioning=None,
               web_error_page=None,
               web_main_page_suffix=None):
    """Initializes class, binding flag values to it."""
    self.cors_file_path = cors_file_path
    self.default_encryption_key = default_encryption_key
    self.default_event_based_hold = default_event_based_hold
    self.default_storage_class = default_storage_class
    self.labels_file_path = labels_file_path
    self.labels_to_append = labels_to_append
    self.labels_to_remove = labels_to_remove
    self.lifecycle_file_path = lifecycle_file_path
    self.location = location
    self.log_bucket = log_bucket
    self.log_object_prefix = log_object_prefix
    self.retention_period = retention_period
    self.requester_pays = requester_pays
    self.uniform_bucket_level_access = uniform_bucket_level_access
    self.versioning = versioning
    self.web_error_page = web_error_page
    self.web_main_page_suffix = web_main_page_suffix

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (self.cors_file_path == other.cors_file_path and
            self.default_encryption_key == other.default_encryption_key and
            self.default_event_based_hold == other.default_event_based_hold and
            self.default_storage_class == other.default_storage_class and
            self.labels_file_path == other.labels_file_path and
            self.labels_to_append == other.labels_to_append and
            self.labels_to_remove == other.labels_to_remove and
            self.lifecycle_file_path == other.lifecycle_file_path and
            self.location == other.location and
            self.log_bucket == other.log_bucket and
            self.log_object_prefix == other.log_object_prefix and
            self.requester_pays == other.requester_pays and
            self.retention_period == other.retention_period and
            self.uniform_bucket_level_access
            == other.uniform_bucket_level_access and
            self.versioning == other.versioning and
            self.web_error_page == other.web_error_page and
            self.web_main_page_suffix == other.web_main_page_suffix)

  def __repr__(self):
    return debug_output.generic_repr(self)


class _UserObjectArgs:
  """Contains user flag values affecting cloud object settings."""

  def __init__(
      self,
      cache_control=None,
      content_disposition=None,
      content_encoding=None,
      content_language=None,
      content_type=None,
      custom_metadata=None,
      custom_time=None,
      md5_hash=None,
      storage_class=None,
  ):
    """Initializes class, binding flag values to it."""
    self.cache_control = cache_control
    self.content_disposition = content_disposition
    self.content_encoding = content_encoding
    self.content_language = content_language
    self.content_type = content_type
    self.custom_metadata = custom_metadata
    self.custom_time = custom_time
    self.md5_hash = md5_hash
    self.storage_class = storage_class

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (self.cache_control == other.cache_control and
            self.content_disposition == other.content_disposition and
            self.content_encoding == other.content_encoding and
            self.content_language == other.content_language and
            self.content_type == other.content_type and
            self.custom_metadata == other.custom_metadata and
            self.custom_time == other.custom_time and
            self.md5_hash == other.md5_hash and
            self.storage_class == other.storage_class)

  def __repr__(self):
    return debug_output.generic_repr(self)


class _UserRequestArgs:
  """Class contains user flags and should be passed to RequestConfig factory.

  Should not be mutated while being passed around. See RequestConfig classes
  for "Attributes" docstring. Specifics depend on API client.
  """

  def __init__(self,
               gzip_in_flight=None,
               manifest_path=None,
               max_bytes_per_call=None,
               no_clobber=False,
               precondition_generation_match=None,
               precondition_metageneration_match=None,
               predefined_acl_string=None,
               predefined_default_acl_string=None,
               resource_args=None):
    """Sets properties."""
    self.gzip_in_flight = gzip_in_flight
    self.manifest_path = manifest_path
    self.max_bytes_per_call = max_bytes_per_call
    self.no_clobber = no_clobber
    self.precondition_generation_match = precondition_generation_match
    self.precondition_metageneration_match = precondition_metageneration_match
    self.predefined_acl_string = predefined_acl_string
    self.predefined_default_acl_string = predefined_default_acl_string
    self.resource_args = resource_args

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (self.gzip_in_flight == other.gzip_in_flight and
            self.manifest_path == other.manifest_path and
            self.max_bytes_per_call == other.max_bytes_per_call and
            self.no_clobber == other.no_clobber and
            self.precondition_generation_match
            == other.precondition_generation_match and
            self.precondition_metageneration_match
            == other.precondition_metageneration_match and
            self.predefined_acl_string == other.predefined_acl_string and
            self.predefined_default_acl_string
            == other.predefined_default_acl_string and
            self.resource_args == other.resource_args)

  def __repr__(self):
    return debug_output.generic_repr(self)


def _get_clear_or_value_from_flag(args, clear_flag, setter_flag):
  """Returns CLEAR if clear flag present or setter value."""
  if getattr(args, clear_flag, None):
    return CLEAR
  else:
    return getattr(args, setter_flag, None)


def get_user_request_args_from_command_args(args, metadata_type=None):
  """Returns UserRequestArgs from a command's Run method "args" parameter."""
  resource_args = None
  if metadata_type:
    if metadata_type == MetadataType.BUCKET:
      cors_file_path = _get_clear_or_value_from_flag(args, 'clear_cors',
                                                     'cors_file')
      default_encryption_key = _get_clear_or_value_from_flag(
          args, 'clear_default_encryption_key', 'default_encryption_key')
      default_storage_class = _get_clear_or_value_from_flag(
          args, 'clear_default_storage_class', 'default_storage_class')
      labels_file_path = _get_clear_or_value_from_flag(args, 'clear_labels',
                                                       'labels_file')
      lifecycle_file_path = _get_clear_or_value_from_flag(
          args, 'clear_lifecycle', 'lifecycle_file')
      log_bucket = _get_clear_or_value_from_flag(args, 'clear_log_bucket',
                                                 'log_bucket')
      log_object_prefix = _get_clear_or_value_from_flag(
          args, 'clear_log_object_prefix', 'log_object_prefix')
      retention_period = _get_clear_or_value_from_flag(
          args, 'clear_retention_period', 'retention_period')
      web_error_page = _get_clear_or_value_from_flag(args,
                                                     'clear_web_error_page',
                                                     'web_error_page')
      web_main_page_suffix = _get_clear_or_value_from_flag(
          args, 'clear_web_main_page_suffix', 'web_main_page_suffix')

      resource_args = _UserBucketArgs(
          cors_file_path=cors_file_path,
          default_encryption_key=default_encryption_key,
          default_event_based_hold=getattr(args, 'default_event_based_hold',
                                           None),
          default_storage_class=default_storage_class,
          labels_file_path=labels_file_path,
          labels_to_append=getattr(args, 'update_labels', None),
          labels_to_remove=getattr(args, 'remove_labels', None),
          lifecycle_file_path=lifecycle_file_path,
          location=getattr(args, 'location', None),
          log_bucket=log_bucket,
          log_object_prefix=log_object_prefix,
          requester_pays=getattr(args, 'requester_pays', None),
          retention_period=retention_period,
          uniform_bucket_level_access=getattr(args,
                                              'uniform_bucket_level_access',
                                              None),
          versioning=getattr(args, 'versioning', None),
          web_error_page=web_error_page,
          web_main_page_suffix=web_main_page_suffix,
      )
    elif metadata_type == MetadataType.OBJECT:
      cache_control = _get_clear_or_value_from_flag(args, 'clear_cache_control',
                                                    'cache_control')
      content_disposition = _get_clear_or_value_from_flag(
          args, 'clear_content_disposition', 'content_disposition')
      content_encoding = _get_clear_or_value_from_flag(
          args, 'clear_content_encoding', 'content_encoding')
      content_language = _get_clear_or_value_from_flag(
          args, 'clear_content_language', 'content_language')
      md5_hash = _get_clear_or_value_from_flag(args, 'clear_content_md5',
                                               'content_md5')
      content_type = _get_clear_or_value_from_flag(args, 'clear_content_type',
                                                   'content_type')
      custom_metadata = _get_clear_or_value_from_flag(args,
                                                      'clear_custom_metadata',
                                                      'custom_metadata')
      custom_time = _get_clear_or_value_from_flag(args, 'clear_custom_time',
                                                  'custom_time')
      storage_class = getattr(args, 'storage_class', None)

      resource_args = _UserObjectArgs(
          cache_control=cache_control,
          content_disposition=content_disposition,
          content_encoding=content_encoding,
          content_language=content_language,
          content_type=content_type,
          custom_metadata=custom_metadata,
          custom_time=custom_time,
          md5_hash=md5_hash,
          storage_class=storage_class)

  if getattr(args, 'gzip_in_flight_all', None):
    gzip_in_flight = GZIP_IN_FLIGHT_ALL
  else:
    gzip_in_flight = getattr(args, 'gzip_in_flight_extensions', None)

  return _UserRequestArgs(
      gzip_in_flight=gzip_in_flight,
      manifest_path=getattr(args, 'manifest_path', None),
      no_clobber=getattr(args, 'no_clobber', False),
      precondition_generation_match=getattr(args, 'if_generation_match', None),
      precondition_metageneration_match=getattr(args, 'if_metageneration_match',
                                                None),
      resource_args=resource_args,
  )
