# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
from __future__ import annotations
from __future__ import division
from __future__ import unicode_literals

import json
import sys
import types
from typing import Any, Callable, Optional

from apitools.base.protorpclite import protojson
from apitools.base.py import encoding
from googlecloudsdk.api_lib.storage import gcs_iam_util
from googlecloudsdk.api_lib.storage import metadata_util
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import user_request_args_factory
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files


ModuleType = types.ModuleType
_messages = apis.GetMessagesModule('storage', 'v1')
_encryption_msg_for_configs = _messages.Bucket.EncryptionValue()


# Maps keys from the --encryption-enforcement-file JSON to API message fields.
_ENCRYPTION_ENFORCEMENT_API_KEY_BY_JSON_KEY_MAP = {
    'gmekEnforcement': 'googleManagedEncryptionEnforcementConfig',
    'cmekEnforcement': 'customerManagedEncryptionEnforcementConfig',
    'csekEnforcement': 'customerSuppliedEncryptionEnforcementConfig',
}
_ENCRYPTION_ENFORCEMENT_API_FIELD_BY_JSON_KEY_MAP = {
    'gmekEnforcement': (
        _encryption_msg_for_configs.GoogleManagedEncryptionEnforcementConfigValue
    ),
    'cmekEnforcement': (
        _encryption_msg_for_configs.CustomerManagedEncryptionEnforcementConfigValue
    ),
    'csekEnforcement': (
        _encryption_msg_for_configs.CustomerSuppliedEncryptionEnforcementConfigValue
    ),
}


def get_bucket_or_object_acl_class(is_bucket=False):
  messages = apis.GetMessagesModule('storage', 'v1')
  if is_bucket:
    acl_class = messages.BucketAccessControl
  else:
    acl_class = messages.ObjectAccessControl
  return acl_class


def process_acl_file(file_path, is_bucket=False):
  """Converts ACL file to Apitools objects."""
  acl_dict_list = metadata_util.cached_read_yaml_json_file(file_path)
  acl_class = get_bucket_or_object_acl_class(is_bucket)
  acl_messages = []
  for acl_dict in acl_dict_list:
    acl_messages.append(encoding.DictToMessage(acl_dict, acl_class))
  return acl_messages


def process_autoclass(enabled_boolean=None, terminal_storage_class=None):
  """Converts Autoclass boolean to Apitools object."""
  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.AutoclassValue(
      enabled=enabled_boolean, terminalStorageClass=terminal_storage_class
  )


def process_cors(file_path):
  """Converts CORS file to Apitools objects."""
  if file_path == user_request_args_factory.CLEAR:
    return []
  cors_dict_list = metadata_util.cached_read_yaml_json_file(file_path)
  if not cors_dict_list:
    return []

  cors_messages = []
  messages = apis.GetMessagesModule('storage', 'v1')
  for cors_dict in cors_dict_list:
    cors_messages.append(
        encoding.DictToMessage(cors_dict, messages.Bucket.CorsValueListEntry)
    )
  return cors_messages


def process_default_encryption_key(default_encryption_key):
  """Converts default_encryption_key string to Apitools object."""
  if default_encryption_key == user_request_args_factory.CLEAR:
    return None

  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.EncryptionValue(
      defaultKmsKeyName=default_encryption_key
  )


def process_encryption_enforcement_config(
    file_path: str,
    get_messages_module: Callable[
        [str, str], ModuleType
    ] = apis.GetMessagesModule,
    read_yaml_json_file: Callable[[str], dict[str, Any]] = (
        metadata_util.cached_read_yaml_json_file
    ),
) -> Optional[_messages.Bucket.EncryptionValue]:
  """Converts encryption enforcement file's contents to Apitools object.

  Args:
    file_path: Path to the encryption enforcement JSON/YAML file.
    get_messages_module: Callable for getting the API messages module.
    read_yaml_json_file: Callable for reading YAML/JSON files.

  Returns:
    Apitools Bucket.EncryptionValue object or None if no changes are present.

  Raises:
    errors.Error: If the file format is invalid.
    errors.InvalidUrlError: If the structure within the file is invalid.
  """
  if not file_path:
    return None

  try:
    enforcement_dict = read_yaml_json_file(file_path)
  except (errors.InvalidUrlError, files.MissingFileError, AttributeError) as e:
    raise errors.Error(
        f'Invalid format for file {file_path} provided for the'
        f' --encryption-enforcement-file flag.\nError: {e}'
    ) from e

  messages = get_messages_module('storage', 'v1')
  encryption_msg = messages.Bucket.EncryptionValue()
  has_changes = False

  for (
      json_key,
      msg_attr,
  ) in _ENCRYPTION_ENFORCEMENT_API_KEY_BY_JSON_KEY_MAP.items():
    if json_key not in enforcement_dict:
      continue

    has_changes = True
    config_data = enforcement_dict[json_key]
    if config_data is None:
      # Setting to None effectively clears it in the PATCH request
      setattr(encryption_msg, msg_attr, None)
    elif isinstance(config_data, dict) and 'restrictionMode' in config_data:
      config_class = _ENCRYPTION_ENFORCEMENT_API_FIELD_BY_JSON_KEY_MAP[json_key]
      try:
        restriction_mode_enum = config_class.RestrictionModeValueValuesEnum(
            config_data['restrictionMode']
        )
        # restrictionMode is the only input field
        enforcement_config = config_class(restrictionMode=restriction_mode_enum)
        setattr(encryption_msg, msg_attr, enforcement_config)
      except (TypeError, messages_util.DecodeError) as e:
        raise errors.InvalidUrlError(
            f'Invalid format in encryption enforcement file for {json_key}: {e}'
        ) from e
    else:
      raise errors.InvalidUrlError(
          f'Invalid structure for {json_key} in encryption enforcement file.'
          ' Expected an object with "restrictionMode" or null.'
      )

  return encryption_msg if has_changes else None


def process_default_storage_class(default_storage_class):
  if default_storage_class == user_request_args_factory.CLEAR:
    return None

  return default_storage_class


def process_hierarchical_namespace(enabled=None):
  """Converts Heirarchical Namespace boolean to Apitools object."""
  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.HierarchicalNamespaceValue(enabled=enabled)


def process_iam_file(file_path, custom_etag=None):
  """Converts IAM file to Apitools objects."""
  if (
      file_path == '-'
      and properties.VALUES.storage.run_by_gsutil_shim.GetBool()
  ):
    policy_dict = metadata_util.read_yaml_json_from_string(sys.stdin.read())
  else:
    policy_dict = metadata_util.cached_read_yaml_json_file(file_path)
  policy_dict['version'] = gcs_iam_util.IAM_POLICY_VERSION
  if custom_etag is not None:
    policy_dict['etag'] = custom_etag
  # Would normally encode the dict directly into a messages object, but the
  # encoding tool has issues with "bytes" field types (etag).
  policy_string = json.dumps(policy_dict)
  messages = apis.GetMessagesModule('storage', 'v1')
  policy_object = protojson.decode_message(messages.Policy, policy_string)
  return policy_object


def process_bucket_iam_configuration(
    existing_iam_metadata,
    public_access_prevention_boolean,
    uniform_bucket_level_access_boolean,
):
  """Converts user flags to Apitools IamConfigurationValue."""
  messages = apis.GetMessagesModule('storage', 'v1')
  if existing_iam_metadata:
    iam_metadata = existing_iam_metadata
  else:
    iam_metadata = messages.Bucket.IamConfigurationValue()

  if public_access_prevention_boolean is not None:
    if public_access_prevention_boolean:
      public_access_prevention_string = 'enforced'
    else:
      public_access_prevention_string = 'inherited'
    iam_metadata.publicAccessPrevention = public_access_prevention_string

  if uniform_bucket_level_access_boolean is not None:
    iam_metadata.uniformBucketLevelAccess = (
        messages.Bucket.IamConfigurationValue.UniformBucketLevelAccessValue(
            enabled=uniform_bucket_level_access_boolean
        )
    )

  return iam_metadata


def process_ip_filter(file_path):
  """Converts IP filter file to Apitools object."""
  messages = apis.GetMessagesModule('storage', 'v1')

  if file_path == user_request_args_factory.CLEAR:
    return messages.Bucket.IpFilterValue(mode='Disabled')
  ip_filter_dict = metadata_util.cached_read_yaml_json_file(file_path)
  ip_filter = ip_filter_dict.get('ip_filter_config', ip_filter_dict)
  try:
    return messages_util.DictToMessageWithErrorCheck(
        ip_filter, messages.Bucket.IpFilterValue
    )
  except messages_util.DecodeError:
    raise errors.InvalidUrlError(
        'Found invalid JSON/YAML for the IP filter rule.'
    )


def process_labels(existing_labels_object, file_path):
  """Converts labels file to Apitools objects."""
  if file_path == user_request_args_factory.CLEAR:
    return None

  if existing_labels_object:
    # The backend deletes labels whose value is None.
    new_labels_dict = {
        key: None for key in encoding.MessageToDict(existing_labels_object)
    }
  else:
    new_labels_dict = {}

  for key, value in metadata_util.cached_read_yaml_json_file(file_path).items():
    new_labels_dict[key] = value

  messages = apis.GetMessagesModule('storage', 'v1')
  labels_property_list = [
      messages.Bucket.LabelsValue.AdditionalProperty(key=key, value=value)
      for key, value in new_labels_dict.items()
  ]

  return messages.Bucket.LabelsValue(additionalProperties=labels_property_list)


def process_lifecycle(file_path):
  """Converts lifecycle file to Apitools objects."""
  if file_path == user_request_args_factory.CLEAR:
    return None
  lifecycle_dict = metadata_util.cached_read_yaml_json_file(file_path)
  if not lifecycle_dict:
    # Empty JSON dict similar to CLEAR flag.
    return None

  messages = apis.GetMessagesModule('storage', 'v1')
  if 'lifecycle' in lifecycle_dict:
    lifecycle_rules_dict = lifecycle_dict['lifecycle']
  else:
    lifecycle_rules_dict = lifecycle_dict

  try:
    return messages_util.DictToMessageWithErrorCheck(
        lifecycle_rules_dict, messages.Bucket.LifecycleValue
    )
  except messages_util.DecodeError:
    raise errors.InvalidUrlError(
        'Found invalid JSON/YAML for the lifecycle rule'
    )


def process_log_config(target_bucket, log_bucket, log_object_prefix):
  """Converts log setting to Apitools object.

  Args:
    target_bucket (str): Bucket to track with logs.
    log_bucket (str|None): Bucket to store logs in.
    log_object_prefix (str|None): Prefix for objects to create logs for.

  Returns:
    messages.Bucket.LoggingValue: Apitools log settings object.
  """
  if log_bucket in ('', None, user_request_args_factory.CLEAR):
    return None

  messages = apis.GetMessagesModule('storage', 'v1')
  logging_value = messages.Bucket.LoggingValue()
  logging_value.logBucket = storage_url.remove_scheme(log_bucket)

  if log_object_prefix == user_request_args_factory.CLEAR:
    logging_value.logObjectPrefix = None
  else:
    logging_value.logObjectPrefix = storage_url.remove_scheme(
        log_object_prefix or target_bucket
    )
  return logging_value


def process_object_retention(
    existing_retention_settings, retain_until, retention_mode
):
  """Converts individual object retention settings to Apitools object."""
  if (
      retain_until == user_request_args_factory.CLEAR
      or retention_mode == user_request_args_factory.CLEAR
      or not any([existing_retention_settings, retain_until, retention_mode])
  ):
    return None

  if existing_retention_settings is None:
    messages = apis.GetMessagesModule('storage', 'v1')
    retention_settings = messages.Object.RetentionValue()
  else:
    retention_settings = existing_retention_settings

  if retain_until:
    retention_settings.retainUntilTime = retain_until
  if retention_mode:
    retention_settings.mode = retention_mode.value

  return retention_settings


def process_placement_config(regions):
  """Converts a list of regions to Apitools object."""
  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.CustomPlacementConfigValue(dataLocations=regions)


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
      retentionPeriod=int(
          storage_util.ObjectLockRetentionDuration()
          .Parse(retention_period_string)
          .total_seconds
      )
  )


def process_soft_delete_duration(soft_delete_duration):
  """Converts retention_period int to Apitools object."""
  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.SoftDeletePolicyValue(
      retentionDurationSeconds=0
      if soft_delete_duration == user_request_args_factory.CLEAR
      else soft_delete_duration
  )


def process_versioning(versioning):
  """Converts versioning bool to Apitools objects."""
  messages = apis.GetMessagesModule('storage', 'v1')
  return messages.Bucket.VersioningValue(enabled=versioning)


def process_website(web_error_page, web_main_page_suffix):
  """Converts website strings to Apitools objects."""
  if (
      web_error_page == user_request_args_factory.CLEAR
      and web_main_page_suffix == user_request_args_factory.CLEAR
  ):
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
