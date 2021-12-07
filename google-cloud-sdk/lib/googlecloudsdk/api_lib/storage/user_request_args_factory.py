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


class MetadataType(enum.Enum):
  BUCKET = 'bucket'
  OBJECT = 'object'


class _UserBucketArgs:
  """Contains user flag values affecting cloud bucket settings."""

  def __init__(self,
               cors_file_path=None,
               default_encryption_key=None,
               default_storage_class=None,
               labels_file_path=None,
               lifecycle_file_path=None,
               location=None,
               retention_period=None,
               uniform_bucket_level_access=None,
               versioning=None,
               web_error_page=None,
               web_main_page_suffix=None):
    """Initializes class, binding flag values to it."""
    self.cors_file_path = cors_file_path
    self.default_encryption_key = default_encryption_key
    self.default_storage_class = default_storage_class
    self.labels_file_path = labels_file_path
    self.lifecycle_file_path = lifecycle_file_path
    self.location = location
    self.retention_period = retention_period
    self.uniform_bucket_level_access = uniform_bucket_level_access
    self.versioning = versioning
    self.web_error_page = web_error_page
    self.web_main_page_suffix = web_main_page_suffix

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (self.cors_file_path == other.cors_file_path and
            self.default_encryption_key == other.default_encryption_key and
            self.default_storage_class == other.default_storage_class and
            self.labels_file_path == other.labels_file_path and
            self.lifecycle_file_path == other.lifecycle_file_path and
            self.location == other.location and
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
            self.md5_hash == other.md5_hash)

  def __repr__(self):
    return debug_output.generic_repr(self)


class _UserRequestArgs:
  """Class contains user flags and should be passed to RequestConfig factory.

  Should not be mutated while being passed around. See RequestConfig classes
  for "Attributes" docstring. Specifics depend on API client.
  """

  def __init__(self,
               max_bytes_per_call=None,
               precondition_generation_match=None,
               precondition_metageneration_match=None,
               predefined_acl_string=None,
               predefined_default_acl_string=None,
               resource_args=None):
    """Sets properties."""
    self.max_bytes_per_call = max_bytes_per_call
    self.precondition_generation_match = precondition_generation_match
    self.precondition_metageneration_match = precondition_metageneration_match
    self.predefined_acl_string = predefined_acl_string
    self.predefined_default_acl_string = predefined_default_acl_string
    self.resource_args = resource_args

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (self.max_bytes_per_call == other.max_bytes_per_call and
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


def get_user_request_args_from_command_args(args, metadata_type=None):
  """Returns UserRequestArgs from a command's Run method "args" parameter."""
  resource_args = None
  if metadata_type:
    if metadata_type == MetadataType.BUCKET:
      resource_args = _UserBucketArgs(
          cors_file_path=getattr(args, 'cors_file', None),
          default_encryption_key=getattr(args, 'default_encryption_key', None),
          default_storage_class=getattr(args, 'default_storage_class', None),
          labels_file_path=getattr(args, 'labels_file', None),
          lifecycle_file_path=getattr(args, 'lifecycle_file', None),
          location=getattr(args, 'location', None),
          retention_period=getattr(args, 'retention_period', None),
          uniform_bucket_level_access=getattr(args,
                                              'uniform_bucket_level_access',
                                              None),
          versioning=getattr(args, 'versioning', None),
          web_error_page=getattr(args, 'web_error_page', None),
          web_main_page_suffix=getattr(args, 'web_main_page_suffix', None),
      )
    elif metadata_type == MetadataType.OBJECT:
      resource_args = _UserObjectArgs(
          cache_control=getattr(args, 'cache_control', None),
          content_disposition=getattr(args, 'content_disposition', None),
          content_encoding=getattr(args, 'content_encoding', None),
          content_language=getattr(args, 'content_language', None),
          content_type=getattr(args, 'content_type', None),
          custom_metadata=getattr(args, 'custom_metadata', None),
          custom_time=getattr(args, 'custom_time', None),
          md5_hash=getattr(args, 'content_md5', None),
      )

  return _UserRequestArgs(
      precondition_generation_match=getattr(args, 'if_generation_match', None),
      precondition_metageneration_match=getattr(args, 'if_metageneration_match',
                                                None),
      resource_args=resource_args,
  )
