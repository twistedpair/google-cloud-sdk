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
"""Library for creating pull request related messages."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json


def CreateCommitMessage(finding_data, member_name):
  """Creates a commit message.

  Args:
    finding_data: Finding data in JSON format.
    member_name: The name of the member to be added to the commit message.

  Returns:
    A string containing the commit message.
  """
  finding_data = json.loads(finding_data)
  finding_result = finding_data["listFindingsResults"][0]
  finding_category = finding_result["finding"][
      "category"
  ]
  crm_node = finding_result["resource"]["displayName"]
  finding_name = finding_result["finding"]["name"]

  return (
      f"Fixing {finding_name} of category {finding_category} for"
      f" {member_name} in {crm_node}"
  )


def CreatePRMessage(finding_data):
  """Creates a commit message for a pull request.

  Args:
    finding_data: Finding data in JSON format.

  Returns:
    A string containing the Pull Request(PR) message.
  """
  finding_data = json.loads(finding_data)
  finding_result = finding_data["listFindingsResults"][0]
  finding_category = finding_result["finding"][
      "category"
  ]
  crm_node = finding_result["resource"]["displayName"]
  finding_name = finding_result["finding"]["name"]

  return (
      f"Fixing Finding:{finding_name} of Category:{finding_category}"
      f" in {crm_node}"
  )
