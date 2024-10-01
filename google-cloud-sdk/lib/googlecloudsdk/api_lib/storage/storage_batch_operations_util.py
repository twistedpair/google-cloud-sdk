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
from googlecloudsdk.api_lib.storage import metadata_util
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.api_lib.util import messages as messages_util


def process_prefix_list_file(prefix_list_file):
  """Converts Prefix List file to Apitools PrefixList object.

  Args:
    prefix_list_file (str): File path to the prefix list file describing
      prefixes of objects to be transformed.

  Returns:
    A PrefixList object.
  """
  messages = core_apis.GetMessagesModule("storagebatchoperations", "v1")
  # parsed_prefix_list is either a list or a dict.
  parsed_prefix_list = metadata_util.cached_read_yaml_json_file(
      prefix_list_file
  )
  if not parsed_prefix_list:
    raise errors.PreconditionFailedError(
        "Found empty JSON/YAML for prefix list. Must be a list of "
        'prefixes in the format {"bucket": BUCKET_NAME, '
        '"objectPrefix": OBJECT_PREFIX}'
    )
  if not isinstance(parsed_prefix_list, list):
    parsed_prefix_list = [parsed_prefix_list]

  prefix_list = messages.PrefixList()
  for prefix_dict in parsed_prefix_list:
    try:
      prefix_list.prefixes.append(
          messages_util.DictToMessageWithErrorCheck(
              prefix_dict, messages.Prefix
          )
      )
    except messages_util.DecodeError:
      raise errors.PreconditionFailedError(
          "Found invalid JSON/YAML for prefix list. Must be a list of "
          'prefixes in the format {"bucket": BUCKET_NAME, '
          '"objectPrefix": OBJECT_PREFIX}'
      )
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
