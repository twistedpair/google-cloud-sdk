# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Tools for processing input for Storage Batch Operations."""

import re

from googlecloudsdk.api_lib.storage import errors
from googlecloudsdk.api_lib.util import apis as core_apis


def process_included_object_prefixes(included_object_prefixes):
  """Converts a list of prefixes to Apitools PrefixList object.

  Args:
    included_object_prefixes (list[str]): list of prefixes.

  Returns:
    A PrefixList object.
  """
  messages = core_apis.GetMessagesModule("storagebatchoperations", "v1")
  prefix_list = messages.PrefixList()
  for prefix in included_object_prefixes:
    prefix_list.includedObjectPrefixes.append(prefix.strip())
  return prefix_list


def get_job_id_and_parent_string_from_resource_name(resource_name):
  match = re.search(r"(projects/.*/locations/.*)/jobs/(.*)", resource_name)
  if match:
    return match.group(1), match.group(2)
  else:
    raise errors.StorageBatchOperationsApiError(
        "Resource name invalid. Please make sure project, location, and job ID"
        " are all provided."
    )
