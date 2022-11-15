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
"""Tools for converting metadata fields to GCS formats."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding

from googlecloudsdk.api_lib.storage import metadata_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import user_request_args_factory
from googlecloudsdk.core.util import iso_duration


def _create_iam_metadata_if_needed(current_iam_metadata):
  """Creates Apitools IAM metadata object if ones does not already exist."""
  if current_iam_metadata:
    return current_iam_metadata
  return apis.GetMessagesModule('storage', 'v1').Bucket.IamConfigurationValue()


def process_acl_file(file_path):
  """Converts ACL file to Apitools objects."""
  acl_dict_list = metadata_util.cached_read_json_file(file_path)
  acl_messages = []
  messages = apis.GetMessagesModule('storage', 'v1')
  for acl_dict in acl_dict_list:
    acl_messages.append(
        encoding.DictToMessage(acl_dict, messages.BucketAccessControl))
  return acl_messages


def process_autoclass(enabled_boolean):
  """Converts autoclass boolean to Apitools object."""
  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.AutoclassValue(enabled=enabled_boolean)


def process_cors(file_path):
  """Converts CORS file to Apitools objects."""
  if file_path == user_request_args_factory.CLEAR:
    return []
  cors_dict_list = metadata_util.cached_read_json_file(file_path)
  if not cors_dict_list:
    return []

  cors_messages = []
  messages = apis.GetMessagesModule('storage', 'v1')
  for cors_dict in cors_dict_list:
    cors_messages.append(
        encoding.DictToMessage(cors_dict, messages.Bucket.CorsValueListEntry))
  return cors_messages


def process_default_encryption_key(default_encryption_key):
  """Converts default_encryption_key string to Apitools object."""
  if default_encryption_key == user_request_args_factory.CLEAR:
    return None

  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.EncryptionValue(
      defaultKmsKeyName=default_encryption_key)


def process_default_storage_class(default_storage_class):
  if default_storage_class == user_request_args_factory.CLEAR:
    return None

  return default_storage_class


def process_labels(file_path):
  """Converts labels file to Apitools objects."""
  if file_path == user_request_args_factory.CLEAR:
    return None

  labels_pair_list = metadata_util.get_label_pairs_from_file(file_path)
  messages = apis.GetMessagesModule('storage', 'v1')
  labels_property_list = [
      messages.Bucket.LabelsValue.AdditionalProperty(key=key, value=value)
      for key, value in labels_pair_list
  ]

  return messages.Bucket.LabelsValue(additionalProperties=labels_property_list)


def process_lifecycle(file_path):
  """Converts lifecycle file to Apitools objects."""
  if file_path == user_request_args_factory.CLEAR:
    return None
  lifecycle_dict = metadata_util.cached_read_json_file(file_path)
  if not lifecycle_dict:
    # Empty JSON dict similar to CLEAR flag.
    return None

  messages = apis.GetMessagesModule('storage', 'v1')
  if 'lifecycle' in lifecycle_dict:
    lifecycle_rules_dict = lifecycle_dict['lifecycle']
  else:
    lifecycle_rules_dict = lifecycle_dict
  return encoding.DictToMessage(lifecycle_rules_dict,
                                messages.Bucket.LifecycleValue)


def process_log_config(target_bucket, log_bucket, log_object_prefix):
  """Converts log setting to Apitools object.

  Args:
    target_bucket (str): Bucket to track with logs.
    log_bucket (str|None): Bucket to store logs in.
    log_object_prefix (str|None): Prefix for objects to create logs for.

  Returns:
    messages.Bucket.LoggingValue: Apitools log settings object.
  """
  if (log_bucket == user_request_args_factory.CLEAR and
      log_object_prefix == user_request_args_factory.CLEAR):
    return None

  messages = apis.GetMessagesModule('storage', 'v1')
  logging_value = messages.Bucket.LoggingValue()

  if log_bucket in (None, user_request_args_factory.CLEAR):
    schemeless_bucket = None
  else:
    schemeless_bucket = storage_url.remove_scheme(log_bucket)

  logging_value.logBucket = schemeless_bucket

  if log_object_prefix == user_request_args_factory.CLEAR:
    schemeless_prefix = None
  elif log_object_prefix is not None:
    schemeless_prefix = storage_url.remove_scheme(log_object_prefix)
  else:
    # Use bucket user is setting logging on as object path prefix.
    schemeless_prefix = storage_url.remove_scheme(target_bucket)

  logging_value.logObjectPrefix = schemeless_prefix
  return logging_value


def process_public_access_prevention(existing_iam_metadata,
                                     public_access_prevention_boolean):
  """Converts public_access_prevention boolean to Apitools object."""
  iam_metadata = _create_iam_metadata_if_needed(existing_iam_metadata)

  if public_access_prevention_boolean:
    public_access_prevention_string = 'enforced'
  else:
    public_access_prevention_string = 'inherited'
  iam_metadata.publicAccessPrevention = public_access_prevention_string
  return iam_metadata


def process_requester_pays(existing_billing, requester_pays):
  """Converts requester_pays boolean to Apitools object."""
  messages = apis.GetMessagesModule('storage', 'v1')
  if existing_billing:
    result_billing = existing_billing
  else:
    result_billing = messages.Bucket.BillingValue()

  result_billing.requesterPays = requester_pays
  return result_billing


def process_retention_period(retention_period_string):
  """Converts retention_period string to Apitools object."""
  if retention_period_string == user_request_args_factory.CLEAR:
    return None

  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.RetentionPolicyValue(
      retentionPeriod=int(iso_duration.Duration().Parse(
          retention_period_string).total_seconds))


def process_uniform_bucket_level_access(existing_iam_metadata,
                                        uniform_bucket_level_access):
  """Converts uniform_bucket_level_access boolean to Apitools object."""
  iam_metadata = _create_iam_metadata_if_needed(existing_iam_metadata)

  messages = apis.GetMessagesModule('storage', 'v1')
  iam_metadata.uniformBucketLevelAccess = (
      messages.Bucket.IamConfigurationValue.UniformBucketLevelAccessValue(
          enabled=uniform_bucket_level_access))
  return iam_metadata


def process_versioning(versioning):
  """Converts versioning bool to Apitools objects."""
  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.VersioningValue(enabled=versioning)


def process_website(web_error_page, web_main_page_suffix):
  """Converts website strings to Apitools objects."""
  if (web_error_page == user_request_args_factory.CLEAR and
      web_main_page_suffix == user_request_args_factory.CLEAR):
    return None

  messages = apis.GetMessagesModule('storage', 'v1')
  website_value = messages.Bucket.WebsiteValue()

  if web_error_page == user_request_args_factory.CLEAR:
    website_value.notFoundPage = None
  else:
    website_value.notFoundPage = web_error_page

  if web_main_page_suffix == user_request_args_factory.CLEAR:
    website_value.mainPageSuffix = None
  else:
    website_value.mainPageSuffix = web_main_page_suffix

  return website_value
