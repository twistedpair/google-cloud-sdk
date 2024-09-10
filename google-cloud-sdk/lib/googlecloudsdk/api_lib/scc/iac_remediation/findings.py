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
"""Library for interacting with the Security Command Center Findings API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from apitools.base.py import encoding
from googlecloudsdk.api_lib.scc.iac_remediation import const
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.scc.iac_remediation import errors


def GetClient():
  """Returns the Security Command Center Findings API client."""
  return apis.GetClientInstance(const.FINDINGS_API_NAME,
                                const.FINDINGS_API_VERSION)


def GetMessages():
  """Returns the Security Command Center Findings API messages."""
  return apis.GetMessagesModule(const.FINDINGS_API_NAME,
                                const.FINDINGS_API_VERSION)


def ParseName(finding_name) -> str:
  """Parses the finding name to get the finding id.

  Args:
    finding_name: Canonical name of the finding.

  Returns:
    Finding id, if found else throws an error
  """
  pattern = r"projects/(\d+)/sources/(\d+)/locations/(\w+)/findings/(\w+)"
  match = re.search(pattern, finding_name)
  if match:
    # Finding id is the 4th group captured from the regex pattern
    return match.group(4)
  else:
    raise errors.InvalidFindingNameError(finding_name)


def MakeApiCall(finding_org_id, finding_name) -> str:
  """Makes an API call to the Security Command Center Findings API.

  Args:
    finding_org_id: Organization ID of the finding
    finding_name: Canonical name of the finding.

  Returns:
    JSON response from the API call.
  """
  client = GetClient()
  messages = GetMessages()
  finding_id = ParseName(finding_name)
  request = messages.SecuritycenterOrganizationsSourcesFindingsListRequest()
  request.filter = f"name : \"{finding_id}\" "
  request.parent = f"organizations/{finding_org_id}/sources/-"
  resp = client.organizations_sources_findings.List(request)
  json_resp = encoding.MessageToJson(resp)
  return json_resp
