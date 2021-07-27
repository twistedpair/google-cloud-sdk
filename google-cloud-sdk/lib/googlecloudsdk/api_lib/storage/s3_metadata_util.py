# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Tools for making the most of S3Api metadata."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.command_lib.storage.resources import s3_resource_reference

_GCS_TO_S3_PREDEFINED_ACL_TRANSLATION_DICT = {
    'authenticatedRead': 'authenticated-read',
    'bucketOwnerFullControl': 'bucket-owner-full-control',
    'bucketOwnerRead': 'bucket-owner-read',
    'private': 'private',
    'publicRead': 'public-read',
    'publicReadWrite': 'public-read-write'
}


def translate_predefined_acl_string_to_s3(predefined_acl_string):
  """Translates Apitools predefined ACL enum key (as string) to S3 equivalent.

  Args:
    predefined_acl_string (str): Value representing user permissions.

  Returns:
    Translated ACL string.

  Raises:
    ValueError: Predefined ACL translation could not be found.
  """
  if predefined_acl_string not in _GCS_TO_S3_PREDEFINED_ACL_TRANSLATION_DICT:
    raise ValueError('Could not translate predefined_acl_string {} to'
                     ' AWS-accepted ACL.'.format(predefined_acl_string))
  return _GCS_TO_S3_PREDEFINED_ACL_TRANSLATION_DICT[predefined_acl_string]


def _get_object_url_from_s3_response(object_dict,
                                     bucket_name,
                                     object_name=None):
  """Creates storage_url.CloudUrl from S3 API response.

  Args:
    object_dict (dict): Dictionary representing S3 API response.
    bucket_name (str): Bucket to include in URL.
    object_name (str | None): Object to include in URL.

  Returns:
    storage_url.CloudUrl populated with data.
  """
  return storage_url.CloudUrl(
      scheme=storage_url.ProviderPrefix.S3,
      bucket_name=bucket_name,
      object_name=object_name,
      generation=object_dict.get('VersionId'))


def get_object_resource_from_s3_response(object_dict,
                                         bucket_name,
                                         object_name=None):
  """Creates resource_reference.S3ObjectResource from S3 API response.

  Args:
    object_dict (dict): Dictionary representing S3 API response.
    bucket_name (str): Bucket response is relevant to.
    object_name (str|None): Object if relevant to query.

  Returns:
    resource_reference.S3ObjectResource populated with data.
  """
  object_url = _get_object_url_from_s3_response(
      object_dict, bucket_name, object_name or object_dict['Key'])

  if 'ETag' in object_dict:
    etag = object_dict.get('ETag')
  elif 'CopyObjectResult' in object_dict:
    etag = object_dict['CopyObjectResult'].get('ETag')
  else:
    etag = None

  if 'Size' in object_dict:
    size = object_dict.get('Size')
  else:
    size = object_dict.get('ContentLength')

  return s3_resource_reference.S3ObjectResource(
      object_url,
      content_type=object_dict.get('ContentType'),
      etag=etag,
      metadata=object_dict,
      size=size)


def get_prefix_resource_from_s3_response(prefix_dict, bucket_name):
  """Creates resource_reference.PrefixResource from S3 API response.

  Args:
    prefix_dict (dict): The S3 API response representing a prefix.
    bucket_name (str): Bucket for the prefix.

  Returns:
    A resource_reference.PrefixResource instance.
  """
  prefix = prefix_dict['Prefix']
  return resource_reference.PrefixResource(
      storage_url.CloudUrl(
          scheme=storage_url.ProviderPrefix.S3,
          bucket_name=bucket_name,
          object_name=prefix),
      prefix=prefix)


def get_metadata_dict_from_request_config(request_config):
  """Returns S3 metadata dict fields based on RequestConfig."""
  metadata = {}
  if request_config.predefined_acl_string is not None:
    metadata['ACL'] = translate_predefined_acl_string_to_s3(
        request_config.predefined_acl_string)

  if request_config.cache_control is not None:
    metadata['CacheControl'] = request_config.cache_control
  if request_config.content_disposition is not None:
    metadata['ContentDisposition'] = request_config.content_disposition
  if request_config.content_encoding is not None:
    metadata['ContentEncoding'] = request_config.content_encoding
  if request_config.content_language is not None:
    metadata['ContentLanguage'] = request_config.content_language
  if request_config.content_type is not None:
    metadata['ContentType'] = request_config.content_type
  if request_config.md5_hash is not None:
    metadata['ContentMD5'] = request_config.md5_hash

  if request_config.custom_metadata:
    metadata['Metadata'] = request_config.custom_metadata

  return metadata
