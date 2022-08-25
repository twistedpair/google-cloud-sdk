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

import base64
import binascii
import copy
import re

from googlecloudsdk.api_lib.storage import errors
from googlecloudsdk.api_lib.storage import metadata_util
from googlecloudsdk.api_lib.storage import s3_metadata_field_converters
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import user_request_args_factory
from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.command_lib.storage.resources import s3_resource_reference
from googlecloudsdk.core import log

_COMMON_S3_METADATA_FIELDS = frozenset([
    'ACL',
    'AccessControlPolicy',
    'CacheControl',
    'ContentDisposition',
    'ContentEncoding',
    'ContentLanguage',
    'ContentType',
    'Metadata',
    'StorageClass',
])
_GCS_TO_S3_PREDEFINED_ACL_TRANSLATION_DICT = {
    'authenticatedRead': 'authenticated-read',
    'bucketOwnerFullControl': 'bucket-owner-full-control',
    'bucketOwnerRead': 'bucket-owner-read',
    'private': 'private',
    'publicRead': 'public-read',
    'publicReadWrite': 'public-read-write'
}
# Determines whether an etag is a valid MD5.
MD5_REGEX = re.compile(r'^[a-fA-F0-9]{32}$')


def get_acl_policy_with_added_and_removed_grants(acl_dict, request_config):
  """Returns full ACL policy object with requested changes.

  Args:
    acl_dict (dict): Contains S3-format ACL policy dict for bucket or object.
      Usually of the form: "{"Grants": [...], "Owner": {...}}". See:
      https://boto3.amazonaws.com/v1/documentation/api/latest/reference
      /services/s3.html#S3.Client.get_bucket_acl
    request_config (request_config_factory._RequestConfig): Contains desired
      changes for the ACL policy.

  Returns:
    dict: Deep copy of acl_dict with added and removed grants and
      removed "ResponseMetadata" field to allow for reuse in PUT API calls.
  """
  # Avoid unexpected destructive side effect of popping to original acl_dict.
  acl_dict_copy = copy.deepcopy(acl_dict)
  # Unnecessary extra metadata that we need to remove for PUT calls.
  acl_dict_copy.pop('ResponseMetadata', None)

  if not request_config.resource_args:
    # No ACL grants to add or remove.
    return acl_dict_copy

  acl_grants_to_add = request_config.resource_args.acl_grants_to_add
  if acl_grants_to_add:
    for new_grant in acl_grants_to_add:
      # Avoid unexpected destructive side effect of pop to request_config.
      new_grant_copy = copy.deepcopy(new_grant)
      # Input format flattens Grantee fields for UX.
      permission = new_grant_copy.pop('Permission')
      acl_dict_copy['Grants'].append({
          'Permission': permission,
          'Grantee': new_grant_copy,
      })

  acl_grants_to_remove = request_config.resource_args.acl_grants_to_remove
  if acl_grants_to_remove:
    entity_identifiers_to_remove = set(acl_grants_to_remove)
    filtered_grants = []
    for existing_grant in acl_dict_copy.get('Grants', []):
      existing_grantee = existing_grant.get('Grantee', {})
      existing_grantee_identifiers = set(
          (existing_grantee.get('EmailAddress'), existing_grantee.get('ID'),
           existing_grantee.get('URI')))
      if not entity_identifiers_to_remove.intersection(
          existing_grantee_identifiers):
        filtered_grants.append(existing_grant)
    acl_dict_copy['Grants'] = filtered_grants

  return acl_dict_copy


def copy_object_metadata(source_metadata_dict, destination_metadata_dict):
  """Copies common S3 fields from one metadata dict to another."""
  if not destination_metadata_dict:
    destination_metadata_dict = {}
  if not source_metadata_dict:
    return destination_metadata_dict
  for field in _COMMON_S3_METADATA_FIELDS:
    if field in source_metadata_dict:
      destination_metadata_dict[field] = source_metadata_dict[field]
  return destination_metadata_dict


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


def _get_etag(object_dict):
  """Returns the cleaned-up etag value, if present."""
  if 'ETag' in object_dict:
    etag = object_dict.get('ETag')
  elif 'CopyObjectResult' in object_dict:
    etag = object_dict['CopyObjectResult'].get('ETag')
  else:
    etag = None

  # The S3 API returns etag wrapped in quotes in some cases.
  if etag and etag.startswith('"') and etag.endswith('"'):
    return etag.strip('"')

  return etag


def _get_md5_hash_from_etag(etag, object_url):
  """Returns base64 encoded MD5 hash, if etag is valid MD5."""
  if etag and MD5_REGEX.match(etag):
    encoded_bytes = base64.b64encode(binascii.unhexlify(etag))
    return encoded_bytes.decode(encoding='utf-8')
  else:
    log.debug(
        'Non-MD5 etag ("%s") present for object: %s.'
        ' Data integrity checks are not possible.', etag, object_url)
  return None


def _get_error_string_or_value(value):
  """Returns the error string if value is error or the value itself."""
  if isinstance(value, errors.S3ApiError):
    return str(value)
  if isinstance(value, dict) and 'ResponseMetadata' in value:
    value_copy = value.copy()
    value_copy.pop('ResponseMetadata')
    return value_copy
  return value


def get_bucket_resource_from_s3_response(bucket_dict, bucket_name):
  """Creates resource_reference.S3BucketResource from S3 API response.

  Args:
    bucket_dict (dict): Dictionary representing S3 API response.
    bucket_name (str): Bucket response is relevant to.

  Returns:
    resource_reference.S3BucketResource populated with data.
  """
  requester_pays = _get_error_string_or_value(bucket_dict.get('Payer'))
  if requester_pays == 'Requester':
    requester_pays = True
  elif requester_pays == 'BucketOwner':
    requester_pays = False

  versioning_enabled = _get_error_string_or_value(bucket_dict.get('Versioning'))
  if isinstance(versioning_enabled, dict):
    if versioning_enabled.get('Status') == 'Enabled':
      versioning_enabled = True
    else:
      versioning_enabled = None

  return s3_resource_reference.S3BucketResource(
      storage_url.CloudUrl(storage_url.ProviderPrefix.S3, bucket_name),
      acl=_get_error_string_or_value(bucket_dict.get('ACL')),
      cors_config=_get_error_string_or_value(bucket_dict.get('CORSRules')),
      lifecycle_config=_get_error_string_or_value(
          bucket_dict.get('LifecycleConfiguration')),
      logging_config=_get_error_string_or_value(
          bucket_dict.get('LoggingEnabled')),
      requester_pays=requester_pays,
      location=_get_error_string_or_value(
          bucket_dict.get('LocationConstraint')),
      metadata=bucket_dict,
      versioning_enabled=versioning_enabled,
      website_config=_get_error_string_or_value(bucket_dict.get('Website')))


def get_object_resource_from_s3_response(object_dict,
                                         bucket_name,
                                         object_name=None,
                                         acl_dict=None):
  """Creates resource_reference.S3ObjectResource from S3 API response.

  Args:
    object_dict (dict): Dictionary representing S3 API response.
    bucket_name (str): Bucket response is relevant to.
    object_name (str|None): Object if relevant to query.
    acl_dict (dict|None): Response from S3 get_object_acl API call.

  Returns:
    resource_reference.S3ObjectResource populated with data.
  """
  object_url = _get_object_url_from_s3_response(
      object_dict, bucket_name, object_name or object_dict['Key'])

  if 'Size' in object_dict:
    size = object_dict.get('Size')
  else:
    size = object_dict.get('ContentLength')

  encryption_algorithm = object_dict.get(
      'ServerSideEncryption', object_dict.get('SSECustomerAlgorithm'))
  etag = _get_etag(object_dict)

  if acl_dict:
    # Full ACL policy more detailed than predefined ACL string.
    raw_acl_data = acl_dict
  else:
    # Predefined ACL string or None.
    raw_acl_data = object_dict.get('ACL')
  if raw_acl_data:
    object_dict['ACL'] = raw_acl_data
  acl = _get_error_string_or_value(raw_acl_data)

  return s3_resource_reference.S3ObjectResource(
      object_url,
      acl=acl,
      cache_control=object_dict.get('CacheControl'),
      component_count=object_dict.get('PartsCount'),
      content_disposition=object_dict.get('ContentDisposition'),
      content_encoding=object_dict.get('ContentEncoding'),
      content_language=object_dict.get('ContentLanguage'),
      content_type=object_dict.get('ContentType'),
      custom_metadata=object_dict.get('Metadata'),
      encryption_algorithm=encryption_algorithm,
      etag=etag,
      kms_key=object_dict.get('SSEKMSKeyId'),
      md5_hash=_get_md5_hash_from_etag(etag, object_url),
      metadata=object_dict,
      size=size,
      storage_class=object_dict.get('StorageClass'),
      update_time=object_dict.get('LastModified'))


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


def get_bucket_metadata_dict_from_request_config(request_config):
  """Returns S3 bucket metadata dict fields based on RequestConfig."""
  metadata = {}

  resource_args = request_config.resource_args
  if resource_args:
    if resource_args.cors_file_path is not None:
      metadata.update(
          s3_metadata_field_converters.process_cors(
              resource_args.cors_file_path))
    if resource_args.labels_file_path is not None:
      metadata.update(
          s3_metadata_field_converters.process_labels(
              resource_args.labels_file_path))
    if resource_args.lifecycle_file_path is not None:
      metadata.update(
          s3_metadata_field_converters.process_lifecycle(
              resource_args.lifecycle_file_path))
    if resource_args.location is not None:
      metadata['LocationConstraint'] = resource_args.location
    if resource_args.requester_pays is not None:
      metadata.update(
          s3_metadata_field_converters.process_requester_pays(
              resource_args.requester_pays))
    if resource_args.versioning is not None:
      metadata.update(
          s3_metadata_field_converters.process_versioning(
              resource_args.versioning))
    if (resource_args.web_error_page is not None or
        resource_args.web_main_page_suffix is not None):
      metadata.update(
          s3_metadata_field_converters.process_website(
              resource_args.web_error_page, resource_args.web_main_page_suffix))

  return metadata


def _process_value_or_clear_flag(metadata, key, value):
  """Sets appropriate metadata based on value."""
  if value == user_request_args_factory.CLEAR:
    metadata[key] = None
  elif value is not None:
    metadata[key] = value


def update_object_metadata_dict_from_request_config(object_metadata,
                                                    request_config,
                                                    file_path=None):
  """Returns S3 object metadata dict fields based on RequestConfig.

  Args:
    object_metadata (dict): Existing object metadata.
    request_config (request_config): May contain data to add to object_metadata.
    file_path (str|None): If present, used for parsing POSIX data from a file on
      the system for the --preserve-posix flag. This flag's presence is
      indicated by the system_posix_data field on request_config.

  Returns:
    dict: Metadata for API request.
  """
  if request_config.predefined_acl_string is not None:
    object_metadata['ACL'] = translate_predefined_acl_string_to_s3(
        request_config.predefined_acl_string)

  resource_args = request_config.resource_args

  existing_metadata = object_metadata.get('Metadata', {})

  custom_metadata_dict = metadata_util.get_updated_custom_metadata(
      existing_metadata, request_config, file_path=file_path)
  if custom_metadata_dict is not None:
    object_metadata['Metadata'] = custom_metadata_dict

  if resource_args:
    _process_value_or_clear_flag(object_metadata, 'CacheControl',
                                 resource_args.cache_control)
    _process_value_or_clear_flag(object_metadata, 'ContentDisposition',
                                 resource_args.content_disposition)
    _process_value_or_clear_flag(object_metadata, 'ContentEncoding',
                                 resource_args.content_encoding)
    _process_value_or_clear_flag(object_metadata, 'ContentLanguage',
                                 resource_args.content_language)
    _process_value_or_clear_flag(object_metadata, 'ContentType',
                                 resource_args.content_type)
    _process_value_or_clear_flag(object_metadata, 'ContentMD5',
                                 resource_args.md5_hash)
    _process_value_or_clear_flag(object_metadata, 'StorageClass',
                                 resource_args.storage_class)
