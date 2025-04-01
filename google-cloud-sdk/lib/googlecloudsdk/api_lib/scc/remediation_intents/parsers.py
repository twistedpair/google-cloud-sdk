# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Module for storing the functions for parsing the tfstate files for dfifferent findings."""

import json
from typing import Sequence, Mapping, Any

from googlecloudsdk.api_lib.scc.remediation_intents import const
from googlecloudsdk.command_lib.util.apis import arg_utils


def iam_recommender_parser(
    all_resources: Sequence[Mapping[str, Any]], finding_data
) -> str:
  """Parses the terraform state file for IAM recommender findings.

  Args:
    all_resources: List of resources from the tfstate file. Resource Format:
                    {
                      "type": "google_project_iam_member",
                      "value": {
                        "member": "user:test@google.com",
                        "role": "roles/owner"
                      }
                    }
    finding_data: SCC Finding data in form of class
      (securityposture.messages.Finding).

  Returns:
    A string containing the terraform resource data blocks in structured format
    for the given finding data.
    Format: (Data block as json string + SEPARATOR ...)
    If any error occurs, returns an empty string.
  """
  data_blocks = []
  try:
    iam_bindings = arg_utils.GetFieldValueFromMessage(
        finding_data, "findingMetadata.iamBindingsList.iamBindings"
    )
    for resource in all_resources:
      # If the resource is of valid type, then check if the resource contains
      # blocks.
      is_relevant_resource = False
      if resource["type"] == "google_project_iam_member":
        for binding in iam_bindings:
          if (
              resource["value"]["member"] == binding.member
              and resource["value"]["role"] == binding.role
          ):
            is_relevant_resource = True
            break
      elif resource["type"] == "google_project_iam_binding":
        for binding in iam_bindings:
          if (
              resource["value"]["role"] == binding.role
              and (binding.member in resource["value"]["members"])
          ):
            is_relevant_resource = True
            break
      # Add resource+separator to the data blocks if it's relevant.
      if is_relevant_resource:
        data_blocks.append(json.dumps(resource, indent=2))
        data_blocks.append(const.BLOCK_SEPARATOR)
    return "".join(data_blocks)
  except (KeyError, arg_utils.InvalidFieldPathError) as _:
    return ""


def firewall_parser(
    all_resources: Sequence[Mapping[str, Any]], finding_data
) -> str:
  """Parses the terraform state file for firewall findings.

  Args:
    all_resources: List of resources from the tfstate file. Resource Format: {
      "type": "google_compute_firewall", "value": { "name": "default-allow-ssh"
      } }
    finding_data: SCC Finding data in form of class
      (securityposture.messages.Finding).

  Returns:
    A string containing the terraform resource data block in json format
    for the given finding data.
    If any error occurs, returns an empty string.
  """
  try:
    firewall_name = arg_utils.GetFieldValueFromMessage(
        finding_data, "findingMetadata.firewallRule.name"
    )
    for resource in all_resources:
      if (
          resource["type"] == "google_compute_firewall"
          and resource["value"]["name"] == firewall_name
      ):
        return json.dumps(resource, indent=2)
  except (KeyError, arg_utils.InvalidFieldPathError) as _:
    return ""
