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
"""S3 API-specific resource subclasses."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import json

from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.command_lib.storage.resources import resource_util


def _metadata_dump_recursion_helper(metadata):
  """See _get_s3_metadata_dump docstring."""
  # Recursive function down the stack may have been processing a list.
  if not isinstance(metadata, list) and not isinstance(metadata, dict):
    return resource_util.convert_to_json_parsable_type(metadata)

  # Sort by key to make sure dictionary always prints in correct order.
  formatted_dict = collections.OrderedDict(sorted(metadata.items()))
  for key, value in formatted_dict.items():
    if isinstance(value, dict):
      # Recursively handle dictionaries.
      formatted_dict[key] = _metadata_dump_recursion_helper(value)
    elif isinstance(value, list):
      # Recursively handled lists, which may contain more dicts, like ACLs.
      formatted_list = [_metadata_dump_recursion_helper(item) for item in value]
      if formatted_list:
        # Ignore empty lists.
        formatted_dict[key] = formatted_list
    elif value or resource_util.should_preserve_falsy_metadata_value(value):
      formatted_dict[key] = resource_util.convert_to_json_parsable_type(value)

  return formatted_dict


def _get_s3_metadata_dump(resource):
  """Formats S3 resource metadata for printing.

  Args:
    resource (S3BucketResource|S3ObjectResource): Resource object.

  Returns:
    Formatted JSON string for printing.
  """
  return json.dumps(collections.OrderedDict([
      ('url', resource.storage_url.url_string),
      ('type', resource.TYPE_STRING),
      ('metadata', _metadata_dump_recursion_helper(resource.metadata)),
  ]), indent=2)


class S3BucketResource(resource_reference.BucketResource):
  """API-specific subclass for handling metadata."""

  def get_metadata_dump(self):
    return _get_s3_metadata_dump(self)


class S3ObjectResource(resource_reference.ObjectResource):
  """API-specific subclass for handling metadata."""

  def get_metadata_dump(self):
    return _get_s3_metadata_dump(self)
