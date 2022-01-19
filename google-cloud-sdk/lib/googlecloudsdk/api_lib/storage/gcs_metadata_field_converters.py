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

from googlecloudsdk.api_lib.storage import metadata_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core.util import iso_duration
from googlecloudsdk.core.util import times


def process_cors(file_path):
  """Converts CORS file to Apitools objects."""
  # Expected JSON file format:
  # List[Dict<
  #   max_age_seconds: int | None,
  #   method: List[str] | None,
  #   origin: List[str] | None,
  #   response_header: List[str] | None>]
  cors_dict_list = metadata_util.cached_read_json_file(file_path)
  cors_messages = []
  messages = apis.GetMessagesModule('storage', 'v1')

  for cors_dict in cors_dict_list:
    cors_messages.append(
        messages.Bucket.CorsValueListEntry(
            maxAgeSeconds=cors_dict.get('max_age_seconds'),
            method=cors_dict.get('method', []),
            origin=cors_dict.get('origin', []),
            responseHeader=cors_dict.get('response_header', [])))
  return cors_messages


def process_default_encryption_key(default_encryption_key):
  """Converts default_encryption_key string to Apitools object."""
  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.EncryptionValue(
      defaultKmsKeyName=default_encryption_key)


def process_labels(file_path):
  """Converts labels file to Apitools objects."""
  messages = apis.GetMessagesModule('storage', 'v1')
  labels_pair_list = metadata_util.get_label_pairs_from_file(file_path)
  labels_property_list = [
      messages.Bucket.LabelsValue.AdditionalProperty(key=key, value=value)
      for key, value in labels_pair_list
  ]

  return messages.Bucket.LabelsValue(additionalProperties=labels_property_list)


def _parse_date_from_lifecycle_condition(lifecycle_rule, field):
  date_string = lifecycle_rule['condition'].get(field)
  if date_string:
    return times.ParseDateTime(date_string).date()
  return None


def process_lifecycle(file_path):
  """Converts lifecycle file to Apitools objects."""
  messages = apis.GetMessagesModule('storage', 'v1')
  # Expected JSON file format:
  # [{
  #   "action": {
  #     "storage_class": str|None
  #     "type": str
  #   },
  #   "": {
  #     "age": int|None
  #     (See rest of fields below in implementation.)
  #   }
  # }, ... ]
  json_lifecycle_rules = metadata_util.cached_read_json_file(file_path)

  apitools_lifecycle_rules = []
  for lifecycle_rule in json_lifecycle_rules:
    action = (
        messages.Bucket.LifecycleValue.RuleValueListEntry.ActionValue(
            storageClass=lifecycle_rule['action'].get('storage_class'),
            type=lifecycle_rule['action'].get('type')))

    condition = (
        messages.Bucket.LifecycleValue.RuleValueListEntry.ConditionValue(
            age=lifecycle_rule['condition'].get('age'),
            createdBefore=_parse_date_from_lifecycle_condition(
                lifecycle_rule, 'created_before'),
            customTimeBefore=_parse_date_from_lifecycle_condition(
                lifecycle_rule, 'custom_time_before'),
            daysSinceCustomTime=lifecycle_rule['condition'].get(
                'days_since_custom_time'),
            daysSinceNoncurrentTime=lifecycle_rule['condition'].get(
                'days_since_noncurrent_time'),
            isLive=lifecycle_rule['condition'].get('is_live'),
            matchesPattern=lifecycle_rule['condition'].get('matches_pattern'),
            matchesStorageClass=lifecycle_rule['condition'].get(
                'matches_storage_class', []),
            noncurrentTimeBefore=_parse_date_from_lifecycle_condition(
                lifecycle_rule, 'noncurrent_time_before'),
            numNewerVersions=lifecycle_rule['condition'].get(
                'num_newer_versions'),
        ))
    apitools_lifecycle_rules.append(
        messages.Bucket.LifecycleValue.RuleValueListEntry(
            action=action, condition=condition))

  return messages.Bucket.LifecycleValue(rule=apitools_lifecycle_rules)


def process_retention_period(retention_period_string):
  """Converts retention_period string to Apitools object."""
  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.RetentionPolicyValue(
      retentionPeriod=int(iso_duration.Duration().Parse(
          retention_period_string).total_seconds))


def process_uniform_bucket_level_access(existing_iam_metadata,
                                        uniform_bucket_level_access):
  """Converts uniform_bucket_level_access boolean to Apitools object."""
  messages = apis.GetMessagesModule('storage', 'v1')
  if existing_iam_metadata:
    result_iam_metadata = existing_iam_metadata
  else:
    result_iam_metadata = messages.Bucket.IamConfigurationValue()

  result_iam_metadata.uniformBucketLevelAccess = (
      messages.Bucket.IamConfigurationValue.UniformBucketLevelAccessValue(
          enabled=uniform_bucket_level_access))
  return result_iam_metadata


def process_versioning(versioning):
  """Converts versioning bool to Apitools objects."""
  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.VersioningValue(enabled=versioning)


def process_website(web_error_page, web_main_page_suffix):
  """Converts website strings to Apitools objects."""
  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.WebsiteValue(
      mainPageSuffix=web_main_page_suffix, notFoundPage=web_error_page)
