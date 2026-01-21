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

from apitools.base.py import encoding_helper
from googlecloudsdk.api_lib.storage import errors
from googlecloudsdk.api_lib.storage import metadata_util
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.command_lib.storage import errors as storage_errors


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


def parse_custom_contexts_file(file_path):
  """Parses custom contexts from a file, and validate it against the message.

  Args:
    file_path (str): Path to the file containing the custom contexts.

  Returns:
    A dictionary containing the custom contexts parsed from the file.

  Raises:
    errors.StorageBatchOperationsApiError: If the provided file is not a valid
    json/yaml file or contains invalid custom contexts.
  """
  try:
    messages = core_apis.GetMessagesModule("storagebatchoperations", "v1")
    parsed_custom_contexts = metadata_util.cached_read_yaml_json_file(file_path)

    for _, value in parsed_custom_contexts.items():
      if not isinstance(value, dict):
        raise errors.StorageBatchOperationsApiError(
            "Invalid format for specified contexts file. Each top-level"
            " value must be a dictionary."
        )
    # Convert the parsed content respect the API message. Unknown fields will
    # be ignored.
    updates = encoding_helper.DictToMessage(
        parsed_custom_contexts,
        messages.CustomContextUpdates.UpdatesValue,
    )
    return updates
  except (storage_errors.InvalidUrlError, AttributeError, TypeError) as e:
    print("error: ", e)
    raise errors.StorageBatchOperationsApiError(
        "Error while parsing the specified contexts file, please ensure that"
        " specified file exists and is valid: {}".format(e),
    )
