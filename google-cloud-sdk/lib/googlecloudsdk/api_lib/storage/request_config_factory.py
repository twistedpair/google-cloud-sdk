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

from googlecloudsdk.command_lib.storage import encryption_util

from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.core.util import debug_output


DEFAULT_CONTENT_TYPE = 'application/octet-stream'


class UserRequestArgs:
  """Class contains user flags and should be passed to RequestConfig factory.

  Should not be mutated while being passed around. See RequestConfig classes
  for "Attributes" docstring. Specifics depend on API client.
  """

  def __init__(self,
               cache_control=None,
               content_disposition=None,
               content_encoding=None,
               content_language=None,
               content_type=None,
               custom_metadata=None,
               custom_time=None,
               max_bytes_per_call=None,
               md5_hash=None,
               precondition_generation_match=None,
               precondition_metageneration_match=None,
               predefined_acl_string=None,
               predefined_default_acl_string=None):
    """Sets properties."""
    self.cache_control = cache_control
    self.content_disposition = content_disposition
    self.content_encoding = content_encoding
    self.content_language = content_language
    self.content_type = content_type
    self.custom_metadata = custom_metadata
    self.custom_time = custom_time
    self.max_bytes_per_call = max_bytes_per_call
    self.md5_hash = md5_hash
    self.precondition_generation_match = precondition_generation_match
    self.precondition_metageneration_match = precondition_metageneration_match
    self.predefined_acl_string = predefined_acl_string
    self.predefined_default_acl_string = predefined_default_acl_string

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
            self.max_bytes_per_call == other.max_bytes_per_call and
            self.md5_hash == other.md5_hash and
            self.precondition_generation_match
            == other.precondition_generation_match and
            self.precondition_metageneration_match
            == other.precondition_metageneration_match and
            self.predefined_acl_string == other.predefined_acl_string and
            self.predefined_default_acl_string
            == other.predefined_default_acl_string)

  def __repr__(self):
    return debug_output.generic_repr(self)


def get_user_request_args_from_command_args(args):
  """Returns UserRequestArgs from a command's Run method "args" parameter."""
  return UserRequestArgs(
      cache_control=getattr(args, 'cache_control', None),
      content_disposition=getattr(args, 'content_disposition', None),
      content_encoding=getattr(args, 'content_encoding', None),
      content_language=getattr(args, 'content_language', None),
      content_type=getattr(args, 'content_type', None),
      custom_metadata=getattr(args, 'custom_metadata', None),
      custom_time=getattr(args, 'custom_time', None),
      md5_hash=getattr(args, 'content_md5', None),
      precondition_generation_match=getattr(args, 'if_generation_match', None),
      precondition_metageneration_match=getattr(args, 'if_metageneration_match',
                                                None),
  )


class _RequestConfig(object):
  """Arguments object for parameters shared between cloud providers.

  Subclasses may add more attributes.

  Attributes:
    cache_control (str|None): Influences how backend caches requests and
      responses.
    content_disposition (str|None): Information on how content should be
      displayed.
    content_encoding (str|None): How content is encoded (e.g. "gzip").
    content_language (str|None): Content's language (e.g. "en" = "English).
    content_type (str|None): Type of data contained in content
      (e.g. "text/html").
    custom_metadata (dict|None): Custom metadata fields set by user.
    decryption_key (encryption_util.EncryptionKey): The key that should be used
      to decrypt information in GCS.
    encryption_key (encryption_util.EncryptionKey): The key that should be used
      to encrypt information in GCS.
    md5_hash (str|None): MD5 digest to use for validation.
    predefined_acl_string (str|None): ACL to set on resource.
    predefined_default_acl_string (str|None): Default ACL to set on resources.
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
               predefined_acl_string=None,
               predefined_default_acl_string=None,
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
    self.predefined_acl_string = predefined_acl_string
    self.predefined_default_acl_string = predefined_default_acl_string
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
            self.md5_hash == other.md5_hash and
            self.predefined_acl_string == other.predefined_acl_string and
            self.predefined_default_acl_string
            == other.predefined_default_acl_string and self.size == other.size)

  def __repr__(self):
    return debug_output.generic_repr(self)


# pylint:disable=g-missing-from-attributes
class _GcsRequestConfig(_RequestConfig):
  """Arguments object for requests with custom GCS parameters.

  See super class for additional attributes.

  Attributes:
    custom_time (datetime|None): Custom time user can set.
    gzip_encoded (bool|None): Whether to use gzip transport encoding for the
      upload.
    max_bytes_per_call (int|None): Integer describing maximum number of bytes to
      write per service call.
    precondition_generation_match (int|None): Perform request only if generation
      of target object matches the given integer. Ignored for bucket requests.
    precondition_metageneration_match (int|None): Perform request only if
      metageneration of target object/bucket matches the given integer.
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
               max_bytes_per_call=None,
               md5_hash=None,
               precondition_generation_match=None,
               precondition_metageneration_match=None,
               predefined_acl_string=None,
               predefined_default_acl_string=None,
               size=None):
    super().__init__(
        cache_control=cache_control,
        content_disposition=content_disposition,
        content_encoding=content_encoding,
        content_language=content_language,
        content_type=content_type,
        custom_metadata=custom_metadata,
        decryption_key=None,
        encryption_key=None,
        md5_hash=md5_hash,
        predefined_acl_string=predefined_acl_string,
        predefined_default_acl_string=predefined_default_acl_string,
        size=size)
    self.custom_time = custom_time
    self.gzip_encoded = gzip_encoded
    self.max_bytes_per_call = max_bytes_per_call
    self.precondition_generation_match = precondition_generation_match
    self.precondition_metageneration_match = precondition_metageneration_match

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (super().__eq__(other) and self.custom_time == other.custom_time and
            self.gzip_encoded == other.gzip_encoded and
            self.max_bytes_per_call == other.max_bytes_per_call and
            self.precondition_generation_match
            == other.precondition_generation_match and
            self.precondition_metageneration_match
            == other.precondition_metageneration_match)


# pylint:disable=g-missing-from-attributes
class _S3RequestConfig(_RequestConfig):
  """Arguments object for requests with custom S3 parameters.

  See super class for attributes.
  """
  # pylint:enable=g-missing-from-attributes

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
               predefined_acl_string=None,
               predefined_default_acl_string=None,
               size=None):
    super().__init__(
        cache_control=cache_control,
        content_disposition=content_disposition,
        content_encoding=content_encoding,
        content_language=content_language,
        content_type=content_type,
        custom_metadata=custom_metadata,
        decryption_key=None,
        encryption_key=None,
        md5_hash=md5_hash,
        predefined_acl_string=predefined_acl_string,
        predefined_default_acl_string=predefined_default_acl_string,
        size=size)

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return super().__eq__(other)


def get_request_config(url,
                       content_type=None,
                       decryption_key_hash=None,
                       md5_hash=None,
                       size=None,
                       user_request_args=None):
  """Generates API-specific RequestConfig. See output classes for arg info."""
  if url.scheme == storage_url.ProviderPrefix.GCS:
    request_config = _GcsRequestConfig()
  elif url.scheme == storage_url.ProviderPrefix.S3:
    request_config = _S3RequestConfig()
  else:
    request_config = _RequestConfig()

  request_config.content_type = content_type
  request_config.md5_hash = md5_hash
  request_config.size = size

  request_config.encryption_key = encryption_util.get_encryption_key()
  if decryption_key_hash:
    request_config.decryption_key = encryption_util.get_decryption_key(
        decryption_key_hash)

  if user_request_args:
    if url.scheme == storage_url.ProviderPrefix.GCS:
      request_config.custom_time = user_request_args.custom_time

      if user_request_args.max_bytes_per_call:
        request_config.max_bytes_per_call = int(
            user_request_args.max_bytes_per_call)
      if user_request_args.precondition_generation_match:
        request_config.precondition_generation_match = int(
            user_request_args.precondition_generation_match)
      if user_request_args.precondition_metageneration_match:
        request_config.precondition_metageneration_match = int(
            user_request_args.precondition_metageneration_match)

    request_config.cache_control = user_request_args.cache_control
    request_config.content_disposition = user_request_args.content_disposition
    request_config.content_encoding = user_request_args.content_encoding
    request_config.content_language = user_request_args.content_language
    request_config.custom_metadata = user_request_args.custom_metadata
    request_config.predefined_acl_string = user_request_args.predefined_acl_string
    request_config.predefined_default_acl_string = (
        user_request_args.predefined_default_acl_string)

    if user_request_args.content_type is not None:
      if not user_request_args.content_type:
        request_config.content_type = DEFAULT_CONTENT_TYPE
      else:
        request_config.content_type = user_request_args.content_type
    if user_request_args.md5_hash is not None:
      request_config.md5_hash = user_request_args.md5_hash

  return request_config
