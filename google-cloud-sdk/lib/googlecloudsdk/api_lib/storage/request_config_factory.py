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
"""Utils for generating API-specific RequestConfig objects.

RequestConfig is provider neutral and should be subclassed into a
provider-specific class (e.g. GcsRequestConfig) by the factory method.

RequestConfig can hold a BucketConfig or ObjectConfig. These classes also
have provider-specific subclasses (e.g. S3ObjectConfig).
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.storage import encryption_util
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.core import log
from googlecloudsdk.core.util import debug_output


DEFAULT_CONTENT_TYPE = 'application/octet-stream'


# Bucket update fields and corresponding flags unsupported by S3.
S3_UNSUPPORTED_FLAGS = [
    ('default_encryption_key', '--default-encryption-key'),
    ('default_event_based_hold', '--default-event-based-hold'),
    ('default_storage_class', '--default-storage-class'),
    ('retention_period', '--retention-period'),
    ('uniform_bucket_level_access', '--uniform-bucket-level-access'),
]


class _BucketConfig(object):
  """Holder for generic bucket fields.

  Attributes:
    cors_file_path (None|str): Path to file with CORS settings.
    labels_file_path (None|str): Path to file with labels settings.
    labels_to_append (None|Dict): Labels to add to a bucket.
    labels_to_remove (None|List[str]): Labels to remove from a bucket.
    lifecycle_file_path (None|str): Path to file with lifecycle settings.
    location (str|None): Location of bucket.
    log_bucket (str|None): Destination bucket for current bucket's logs.
    log_object_prefix (str|None): Prefix for objects containing logs.
    versioning (None|bool): Whether to turn on object versioning in a bucket.
    web_error_page (None|str): Error page address if bucket is being used
      to host a website.
    web_main_page_suffix (None|str): Suffix of main page address if bucket is
      being used to host a website.
  """

  def __init__(self,
               cors_file_path=None,
               labels_file_path=None,
               labels_to_append=None,
               labels_to_remove=None,
               lifecycle_file_path=None,
               location=None,
               log_bucket=None,
               log_object_prefix=None,
               versioning=None,
               web_error_page=None,
               web_main_page_suffix=None):
    self.location = location
    self.cors_file_path = cors_file_path
    self.labels_file_path = labels_file_path
    self.labels_to_append = labels_to_append
    self.labels_to_remove = labels_to_remove
    self.lifecycle_file_path = lifecycle_file_path
    self.log_bucket = log_bucket
    self.log_object_prefix = log_object_prefix
    self.versioning = versioning
    self.web_error_page = web_error_page
    self.web_main_page_suffix = web_main_page_suffix

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (super(_BucketConfig, self).__eq__(other) and
            self.cors_file_path == other.cors_file_path and
            self.labels_file_path == other.labels_file_path and
            self.labels_to_append == other.labels_to_append and
            self.labels_to_remove == other.labels_to_remove and
            self.lifecycle_file_path == other.lifecycle_file_path and
            self.location == other.location and
            self.log_bucket == other.log_bucket and
            self.log_object_prefix == other.log_object_prefix and
            self.versioning == other.versioning and
            self.web_error_page == other.web_error_page and
            self.web_main_page_suffix == other.web_main_page_suffix)

  def __repr__(self):
    return debug_output.generic_repr(self)


class _GcsBucketConfig(_BucketConfig):
  """Holder for GCS-specific bucket fields.

  See superclass for remaining attributes.

  Subclass Attributes:
    default_encryption_key (str|None): A key used to encrypt objects
      added to the bucket.
    default_event_based_hold (bool|None): Determines if event-based holds will
      automatically be applied to new objects in bucket.
    default_storage_class (str|None): Storage class assigned to objects in the
      bucket by default.
    retention_period (int|None): Minimum retention period in seconds for objects
      in a bucket. Attempts to delete an object earlier will be denied.
    uniform_bucket_level_access (bool|None):
      Determines if the IAM policies will apply to every object in bucket.
  """

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
               retention_period=None,
               uniform_bucket_level_access=None,
               versioning=None,
               web_error_page=None,
               web_main_page_suffix=None):
    super(_GcsBucketConfig,
          self).__init__(cors_file_path, labels_file_path, labels_to_append,
                         labels_to_remove, lifecycle_file_path, location,
                         log_bucket, log_object_prefix, versioning,
                         web_error_page, web_main_page_suffix)
    self.default_encryption_key = default_encryption_key
    self.default_event_based_hold = default_event_based_hold
    self.default_storage_class = default_storage_class
    self.retention_period = retention_period
    self.uniform_bucket_level_access = uniform_bucket_level_access

  def __eq__(self, other):
    return (super(_GcsBucketConfig, self).__eq__(other) and
            self.default_encryption_key == other.default_encryption_key and
            self.default_event_based_hold == other.default_event_based_hold and
            self.default_storage_class == other.default_storage_class and
            self.retention_period == other.retention_period and
            self.uniform_bucket_level_access
            == other.uniform_bucket_level_access)


class _S3BucketConfig(_BucketConfig):
  """Holder for S3-specific bucket fields.

  See superclass for attributes.
  We currently don't support any S3-only fields. This class exists to maintain
  the provider-specific subclass pattern used by the request config factory.
  """


class _ObjectConfig(object):
  """Holder for storage object settings shared between cloud providers.

  Provider-specific subclasses may add more attributes.

  Attributes:
    cache_control (str|None): Influences how backend caches requests and
      responses.
    content_disposition (str|None): Information on how content should be
      displayed.
    content_encoding (str|None): How content is encoded (e.g. "gzip").
    content_language (str|None): Content's language (e.g. "en" = "English).
    content_type (str|None): Type of data contained in content (e.g.
      "text/html").
    custom_metadata (dict|None): Custom metadata fields set by user.
    decryption_key (encryption_util.EncryptionKey): The key that should be used
      to decrypt information in GCS.
    encryption_key (encryption_util.EncryptionKey): The key that should be used
      to encrypt information in GCS.
    md5_hash (str|None): MD5 digest to use for validation.
    size (int|None): Object size in bytes.
  """

  def __init__(self,
               cache_control=None,
               content_disposition=None,
               content_encoding=None,
               content_language=None,
               content_type=None,
               custom_metadata=None,
               decryption_key=None,
               encryption_key=None,
               md5_hash=None,
               size=None):
    self.cache_control = cache_control
    self.content_disposition = content_disposition
    self.content_encoding = content_encoding
    self.content_language = content_language
    self.content_type = content_type
    self.custom_metadata = custom_metadata
    self.decryption_key = decryption_key
    self.encryption_key = encryption_key
    self.md5_hash = md5_hash
    self.size = size

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (self.cache_control == other.cache_control and
            self.content_disposition == other.content_disposition and
            self.content_encoding == other.content_encoding and
            self.content_language == other.content_language and
            self.content_type == other.content_type and
            self.custom_metadata == other.custom_metadata and
            self.decryption_key == other.decryption_key and
            self.encryption_key == other.encryption_key and
            self.md5_hash == other.md5_hash and self.size == other.size)

  def __repr__(self):
    return debug_output.generic_repr(self)


class _GcsObjectConfig(_ObjectConfig):
  """Arguments object for requests with custom GCS parameters.

  See super class for additional attributes.

  Attributes:
    custom_time (datetime|None): Custom time user can set.
    gzip_encoded (bool|None): Whether to use gzip transport encoding for the
      upload.
  """
  # pylint:enable=g-missing-from-attributes

  def __init__(self,
               cache_control=None,
               content_disposition=None,
               content_encoding=None,
               content_language=None,
               content_type=None,
               custom_metadata=None,
               custom_time=None,
               decryption_key=None,
               encryption_key=None,
               gzip_encoded=False,
               md5_hash=None,
               size=None):
    super(_GcsObjectConfig, self).__init__(
        cache_control=cache_control,
        content_disposition=content_disposition,
        content_encoding=content_encoding,
        content_language=content_language,
        content_type=content_type,
        custom_metadata=custom_metadata,
        decryption_key=decryption_key,
        encryption_key=encryption_key,
        md5_hash=md5_hash,
        size=size)
    self.custom_time = custom_time
    self.gzip_encoded = gzip_encoded

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (super(_GcsObjectConfig, self).__eq__(other) and
            self.custom_time == other.custom_time and
            self.gzip_encoded == other.gzip_encoded)


class _S3ObjectConfig(_ObjectConfig):
  """We currently do not support any S3-specific object configurations."""


class _RequestConfig(object):
  """Holder for parameters shared between cloud providers.

  Provider-specific subclasses may add more attributes.

  Attributes:
    predefined_acl_string (str|None): ACL to set on resource.
    predefined_default_acl_string (str|None): Default ACL to set on resources.
    resource_args (_BucketConfig|_ObjectConfig|None): Holds settings for a cloud
      resource.
  """

  def __init__(self,
               predefined_acl_string=None,
               predefined_default_acl_string=None,
               resource_args=None):
    self.predefined_acl_string = predefined_acl_string
    self.predefined_default_acl_string = predefined_default_acl_string
    self.resource_args = resource_args

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (self.predefined_acl_string == other.predefined_acl_string and
            self.predefined_default_acl_string
            == other.predefined_default_acl_string and
            self.resource_args == other.resource_args)

  def __repr__(self):
    return debug_output.generic_repr(self)


# pylint:disable=g-missing-from-attributes
class _GcsRequestConfig(_RequestConfig):
  """Holder for GCS-specific API request parameters.

  See super class for additional attributes.

  Attributes:
    max_bytes_per_call (int|None): Integer describing maximum number of bytes to
      write per service call.
    precondition_generation_match (int|None): Perform request only if generation
      of target object matches the given integer. Ignored for bucket requests.
    precondition_metageneration_match (int|None): Perform request only if
      metageneration of target object/bucket matches the given integer.
  """
  # pylint:enable=g-missing-from-attributes

  def __init__(self,
               max_bytes_per_call=None,
               precondition_generation_match=None,
               precondition_metageneration_match=None,
               predefined_acl_string=None,
               predefined_default_acl_string=None,
               resource_args=None):
    super(_GcsRequestConfig, self).__init__(
        predefined_acl_string=predefined_acl_string,
        predefined_default_acl_string=predefined_default_acl_string,
        resource_args=resource_args)
    self.max_bytes_per_call = max_bytes_per_call
    self.precondition_generation_match = precondition_generation_match
    self.precondition_metageneration_match = precondition_metageneration_match

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (super(_GcsRequestConfig, self).__eq__(other) and
            self.max_bytes_per_call == other.max_bytes_per_call and
            self.precondition_generation_match
            == other.precondition_generation_match and
            self.precondition_metageneration_match
            == other.precondition_metageneration_match)


class _S3RequestConfig(_RequestConfig):
  """Holder for S3-specific API request parameters.

  Currently just meant for use with S3ObjectConfig and S3BucketConfig in
  the parent class "resource_args" field.
  """


def _get_request_config_resource_args(url,
                                      content_type=None,
                                      decryption_key_hash=None,
                                      md5_hash=None,
                                      size=None,
                                      user_request_args=None):
  """Generates metadata for API calls to storage buckets and objects."""
  if not isinstance(url, storage_url.CloudUrl):
    return None
  user_resource_args = getattr(user_request_args, 'resource_args', None)
  new_resource_args = None

  if url.is_bucket():
    if url.scheme in storage_url.VALID_CLOUD_SCHEMES:
      if url.scheme == storage_url.ProviderPrefix.GCS:
        new_resource_args = _GcsBucketConfig()
        if user_resource_args:
          new_resource_args.default_encryption_key = (
              user_resource_args.default_encryption_key)
          new_resource_args.default_event_based_hold = (
              user_resource_args.default_event_based_hold)
          new_resource_args.default_storage_class = (
              user_resource_args.default_storage_class)
          new_resource_args.retention_period = (
              user_resource_args.retention_period)
          new_resource_args.uniform_bucket_level_access = (
              user_resource_args.uniform_bucket_level_access)

      elif url.scheme == storage_url.ProviderPrefix.S3:
        new_resource_args = _S3BucketConfig()

        unsupported_flags_present = []
        for field, flag in S3_UNSUPPORTED_FLAGS:
          if getattr(user_resource_args, field, None):
            unsupported_flags_present.append(flag)

        if unsupported_flags_present:
          log.warning('Some flags do not have S3 support: {}.'.format(
              ', '.join(unsupported_flags_present)))

    else:
      new_resource_args = _BucketConfig()

    new_resource_args.location = getattr(user_resource_args, 'location', None)
    new_resource_args.cors_file_path = getattr(
        user_resource_args, 'cors_file_path', None)
    new_resource_args.labels_file_path = getattr(
        user_resource_args, 'labels_file_path', None)
    new_resource_args.labels_to_append = getattr(
        user_resource_args, 'labels_to_append', None)
    new_resource_args.labels_to_remove = getattr(
        user_resource_args, 'labels_to_remove', None)
    new_resource_args.lifecycle_file_path = getattr(
        user_resource_args, 'lifecycle_file_path', None)
    new_resource_args.log_bucket = getattr(
        user_resource_args, 'log_bucket', None)
    new_resource_args.log_object_prefix = getattr(
        user_resource_args, 'log_object_prefix', None)
    new_resource_args.versioning = getattr(
        user_resource_args, 'versioning', None)
    new_resource_args.web_error_page = getattr(
        user_resource_args, 'web_error_page', None)
    new_resource_args.web_main_page_suffix = getattr(
        user_resource_args, 'web_main_page_suffix', None)

  elif url.is_object():
    if url.scheme == storage_url.ProviderPrefix.GCS:
      new_resource_args = _GcsObjectConfig()
      if user_resource_args:
        new_resource_args.custom_time = user_resource_args.custom_time

    elif url.scheme == storage_url.ProviderPrefix.S3:
      new_resource_args = _S3ObjectConfig()

    else:
      new_resource_args = _ObjectConfig()

    new_resource_args.content_type = content_type
    new_resource_args.md5_hash = md5_hash
    new_resource_args.size = size

    new_resource_args.encryption_key = encryption_util.get_encryption_key()
    if decryption_key_hash:
      new_resource_args.decryption_key = encryption_util.get_decryption_key(
          decryption_key_hash)

    if user_resource_args:
      # User args should override existing settings.
      if user_resource_args.content_type is not None:
        if user_resource_args.content_type:
          new_resource_args.content_type = user_resource_args.content_type
        else:  # Empty string or other falsey value but not completely unset.
          new_resource_args.content_type = DEFAULT_CONTENT_TYPE

      if user_resource_args.md5_hash is not None:
        new_resource_args.md5_hash = user_resource_args.md5_hash

      new_resource_args.cache_control = user_resource_args.cache_control
      new_resource_args.content_disposition = user_resource_args.content_disposition
      new_resource_args.content_encoding = user_resource_args.content_encoding
      new_resource_args.content_language = user_resource_args.content_language
      new_resource_args.custom_metadata = user_resource_args.custom_metadata

  return new_resource_args


def get_request_config(url,
                       content_type=None,
                       decryption_key_hash=None,
                       md5_hash=None,
                       size=None,
                       user_request_args=None):
  """Generates API-specific RequestConfig. See output classes for arg info."""
  resource_args = _get_request_config_resource_args(url, content_type,
                                                    decryption_key_hash,
                                                    md5_hash, size,
                                                    user_request_args)

  if url.scheme == storage_url.ProviderPrefix.GCS:
    request_config = _GcsRequestConfig(resource_args=resource_args)
    if user_request_args:
      if user_request_args.max_bytes_per_call:
        request_config.max_bytes_per_call = int(
            user_request_args.max_bytes_per_call)
      if user_request_args.precondition_generation_match:
        request_config.precondition_generation_match = int(
            user_request_args.precondition_generation_match)
      if user_request_args.precondition_metageneration_match:
        request_config.precondition_metageneration_match = int(
            user_request_args.precondition_metageneration_match)
  elif url.scheme == storage_url.ProviderPrefix.S3:
    request_config = _S3RequestConfig(resource_args=resource_args)
  else:
    request_config = _RequestConfig(resource_args=resource_args)

  request_config.predefined_acl_string = getattr(user_request_args,
                                                 'predefined_acl_string', None)
  request_config.predefined_default_acl_string = getattr(
      user_request_args, 'predefined_default_acl_string', None)

  return request_config
