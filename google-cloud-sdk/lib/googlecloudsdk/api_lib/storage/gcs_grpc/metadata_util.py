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
"""Utility functions for normalizing gRPC messages."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime

from cloudsdk.google.protobuf import json_format
from googlecloudsdk.command_lib.storage import hash_util
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.resources import gcs_resource_reference
from googlecloudsdk.command_lib.util import crc32c


GRPC_URL_BUCKET_OFFSET = len('projects/_/buckets/')


def _convert_repeated_message_to_dict(message):
  """Converts a sequence of proto messages to a dict."""
  if not message:
    return
  # TODO(b/262768337) Use message_to_dict translation once it's fixed
  # pylint: disable=protected-access
  return [json_format.MessageToDict(i._pb) for i in message]
  # pylint: enable=protected-access


def _convert_proto_to_datetime(proto_datetime):
  """Converts the proto.datetime_helpers.DatetimeWithNanoseconds to datetime."""
  if not proto_datetime:
    return
  return datetime.datetime.fromtimestamp(
      proto_datetime.timestamp(), proto_datetime.tzinfo)


def _get_value_or_none(value):
  """Returns None if value is falsy, else the value itself.

  Unlike Apitools messages, gRPC messages do not return None for fields that
  are not set. It will instead be set to a falsy value.

  Args:
    value (proto.Message): The proto message.

  Returns:
    None if the value is falsy, else the value itself.
  """
  if value:
    return value
  return None


def get_object_resource_from_grpc_object(grpc_object):
  """Returns the GCSObjectResource based off of the gRPC Object."""
  if grpc_object.generation is not None:
    # Generation may be 0 integer, which is valid although falsy.
    generation = str(grpc_object.generation)
  else:
    generation = None
  url = storage_url.CloudUrl(
      scheme=storage_url.ProviderPrefix.GCS,
      # bucket is of the form projects/_/buckets/<bucket_name>
      bucket_name=grpc_object.bucket[GRPC_URL_BUCKET_OFFSET:],
      object_name=grpc_object.name,
      generation=generation)

  if (grpc_object.customer_encryption and
      grpc_object.customer_encryption.key_sha256_bytes):
    decryption_key_hash_sha256 = hash_util.get_base64_string(
        grpc_object.customer_encryption.key_sha256_bytes)
    encryption_algorithm = grpc_object.customer_encryption.encryption_algorithm
  else:
    decryption_key_hash_sha256 = encryption_algorithm = None

  if grpc_object.checksums.crc32c is not None:
    # crc32c can be 0, so check for None value specifically.
    crc32c_hash = crc32c.get_crc32c_hash_string_from_checksum(
        grpc_object.checksums.crc32c)
  else:
    crc32c_hash = None

  if grpc_object.checksums.md5_hash:
    md5_hash = hash_util.get_base64_string(grpc_object.checksums.md5_hash)
  else:
    md5_hash = None

  return gcs_resource_reference.GcsObjectResource(
      url,
      acl=_convert_repeated_message_to_dict(grpc_object.acl),
      cache_control=_get_value_or_none(grpc_object.cache_control),
      component_count=_get_value_or_none(grpc_object.component_count),
      content_disposition=_get_value_or_none(grpc_object.content_disposition),
      content_encoding=_get_value_or_none(grpc_object.content_encoding),
      content_language=_get_value_or_none(grpc_object.content_language),
      content_type=_get_value_or_none(grpc_object.content_type),
      crc32c_hash=crc32c_hash,
      creation_time=_convert_proto_to_datetime(grpc_object.create_time),
      custom_fields=_get_value_or_none(grpc_object.metadata),
      custom_time=_convert_proto_to_datetime(grpc_object.custom_time),
      decryption_key_hash_sha256=decryption_key_hash_sha256,
      encryption_algorithm=encryption_algorithm,
      etag=_get_value_or_none(grpc_object.etag),
      event_based_hold=(grpc_object.event_based_hold
                        if grpc_object.event_based_hold else None),
      kms_key=_get_value_or_none(grpc_object.kms_key),
      md5_hash=md5_hash,
      metadata=grpc_object,
      metageneration=grpc_object.metageneration,
      noncurrent_time=_convert_proto_to_datetime(grpc_object.delete_time),
      retention_expiration=_convert_proto_to_datetime(
          grpc_object.retention_expire_time),
      size=grpc_object.size,
      storage_class=_get_value_or_none(grpc_object.storage_class),
      storage_class_update_time=_convert_proto_to_datetime(
          grpc_object.update_storage_class_time),
      temporary_hold=(grpc_object.temporary_hold
                      if grpc_object.temporary_hold else None),
      update_time=_convert_proto_to_datetime(grpc_object.update_time))
