# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""GCS API-specific resource subclasses."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import json

from apitools.base.protorpclite import messages
from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.command_lib.storage.resources import resource_util


def _metadata_dump_recursion_helper(metadata):
  """See _get_gcs_metadata_dump docstring."""
  if not isinstance(metadata, messages.Message):
    # Recursive function down the stack may have been processing a list.
    return resource_util.convert_to_json_parsable_type(metadata)

  # Construct dictionary from Apitools object.
  formatted_dict = collections.OrderedDict()
  # Similar to Apitools messages.py Message __repr__ implementation.
  for field in sorted(metadata.all_fields(), key=lambda f: f.name):
    value = metadata.get_assigned_value(field.name)
    if isinstance(value, messages.Message):
      # Recursively handled nested Apitools objects.
      formatted_dict[field.name] = _metadata_dump_recursion_helper(value)
    elif isinstance(value, list):
      # Recursively handled lists, which may contain Apitools objects.
      # Example: ACL list.
      formatted_list = [
          _metadata_dump_recursion_helper(item) for item in value]
      if formatted_list:
        # Ignore empty lists.
        formatted_dict[field.name] = formatted_list
    elif value or resource_util.should_preserve_falsy_metadata_value(value):
      # 0, 0.0, and False are acceptables Falsy-types. Lists handled later.
      formatted_dict[field.name] = (
          resource_util.convert_to_json_parsable_type(value))
  return formatted_dict


def _get_gcs_metadata_dump(resource):
  """Formats GCS resource metadata for printing.

  Args:
    resource (GcsBucketResource|GcsObjectResource): Resource object.

  Returns:
    Formatted JSON string for printing.
  """
  return json.dumps(collections.OrderedDict([
      ('url', resource.storage_url.url_string),
      ('type', resource.TYPE_STRING),
      ('metadata', _metadata_dump_recursion_helper(resource.metadata)),
  ]), indent=2)


class GcsBucketResource(resource_reference.BucketResource):
  """API-specific subclass for handling metadata."""

  def get_metadata_dump(self):
    return _get_gcs_metadata_dump(self)


class GcsObjectResource(resource_reference.ObjectResource):
  """API-specific subclass for handling metadata."""

  def get_metadata_dump(self):
    return _get_gcs_metadata_dump(self)
