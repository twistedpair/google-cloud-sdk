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
from googlecloudsdk.core.util import debug_output


DEFAULT_CONTENT_TYPE = 'application/octet-stream'


# TODO (b/203088491): Implement bucket config fields.
class _BucketConfig(object):

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return True

  def __repr__(self):
    return debug_output.generic_repr(self)


# TODO (b/203088491): Implement bucket config for GCS.
class _GcsBucketConfig(_BucketConfig):
  pass


# TODO (b/203088491): Implement bucket config for S3.
class _S3BucketConfig(_BucketConfig):
  pass


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
    super().__init__(
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
    return (super().__eq__(other) and self.custom_time == other.custom_time and
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
    super().__init__(
        predefined_acl_string=predefined_acl_string,
        predefined_default_acl_string=predefined_default_acl_string,
        resource_args=resource_args)
    self.max_bytes_per_call = max_bytes_per_call
    self.precondition_generation_match = precondition_generation_match
    self.precondition_metageneration_match = precondition_metageneration_match

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (super().__eq__(other) and
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
    if url.scheme == storage_url.ProviderPrefix.GCS:
      new_resource_args = _GcsBucketConfig()
    elif url.scheme == storage_url.ProviderPrefix.S3:
      new_resource_args = _S3BucketConfig()
    else:
      new_resource_args = _BucketConfig()

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
