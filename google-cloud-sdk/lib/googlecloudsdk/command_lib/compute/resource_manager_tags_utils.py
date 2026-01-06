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
"""Code that's shared between multiple org firewall policies subcommands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.command_lib.resource_manager import tag_utils

# Regex explained:
# [0-9]+/[a-zA-Z0-9][^\"\\\\'/]* - namespaced format for tag key
# [0-9]+ - org id or project number
# [a-zA-Z0-9] - starts with an alphanumeric character
# [^\"\\\\'/]* - followed by any number of characters except single quote,
#                double quote, forward slash and backslash
NAMESPACED_TAG_KEY_PATTERN = r"[0-9]+/[a-zA-Z0-9][^\"\\\\'/]*"
NAMESPACED_TAG_KEY_REGEX = re.compile(NAMESPACED_TAG_KEY_PATTERN)

SHORT_NAME_VALUE_PATTERN = r"[a-zA-Z0-9][^\"\\'/]*"

NAMESPACED_TAG_VALUE_PATTERN = (
    f"({NAMESPACED_TAG_KEY_PATTERN})" + "/" + f"({SHORT_NAME_VALUE_PATTERN})"
)
NAMESPACED_TAG_VALUE_REGEX = re.compile(NAMESPACED_TAG_VALUE_PATTERN)
NUMERIC_TAG_VALUE_REGEX = re.compile(r"tagValues/[0-9]+")


def GetResourceManagerTags(resource_manager_tags):
  """Returns a map of resource manager tags, translating namespaced tags if needed.

  Args:
    resource_manager_tags: Map of resource manager tag key value pairs with
      either namespaced or numeric format.

  Returns:
    Map of resource manager tag key value pairs with either namespaced or
    numeric format.
  """

  ret_resource_manager_tags = {}
  for key, value in resource_manager_tags.items():
    # If the tag value is in namespaced format, extract the namespaced
    # key and short name value from it to pass to the API.
    namespaced_tag_value_match = NAMESPACED_TAG_VALUE_REGEX.fullmatch(value)
    if namespaced_tag_value_match:
      key = namespaced_tag_value_match.group(1)
      value = namespaced_tag_value_match.group(2)
    elif NAMESPACED_TAG_KEY_REGEX.fullmatch(
        key
    ) and NUMERIC_TAG_VALUE_REGEX.fullmatch(value):
      # If the tag key is in namespaced format, but the value is numeric,
      # translate the key to numeric format to pass to the API.
      key = tag_utils.GetNamespacedResource(key, tag_utils.TAG_KEYS).name
    ret_resource_manager_tags[key] = value

  return ret_resource_manager_tags
