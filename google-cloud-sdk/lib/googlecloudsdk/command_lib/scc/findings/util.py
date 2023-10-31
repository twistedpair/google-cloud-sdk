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
"""Shared utility functions for Cloud SCC findings commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re

from googlecloudsdk.command_lib.scc import errors
from googlecloudsdk.command_lib.scc import util
from googlecloudsdk.generated_clients.apis.securitycenter.v1 import securitycenter_v1_messages as messages


def ValidateMutexOnFindingAndSourceAndOrganization(args):
  """Validates that only a full resource name or split arguments are provided."""
  if "/" in args.finding and (
      args.organization is not None or args.source is not None
  ):
    raise errors.InvalidSCCInputError(
        "Only provide a full resource name "
        "(organizations/123/sources/456/findings/789) or an --organization flag"
        " and --sources flag, not both."
    )


def GetFindingNameForParent(args):
  """Returns relative resource name for a finding name."""
  resource_pattern = re.compile(
      "(organizations|projects|folders)/.*/sources/[0-9-]+/findings/[a-zA-Z0-9]+$"
  )
  id_pattern = re.compile("^[a-zA-Z0-9]+$")
  if not resource_pattern.match(args.finding) and not id_pattern.match(
      args.finding
  ):
    raise errors.InvalidSCCInputError(
        "Finding must match either the full resource name or only the "
        "finding id."
    )
  if resource_pattern.match(args.finding):
    # Handle finding id as full resource name
    return args.finding
  return GetSourceNameForParent(args) + "/findings/" + args.finding


def GetSourceNameForParent(args):
  """Returns relative resource name for a source."""
  resource_pattern = re.compile(
      "(organizations|projects|folders)/.*/sources/[0-9-]+"
  )
  id_pattern = re.compile("[0-9-]+")
  if not resource_pattern.match(args.source) and not id_pattern.match(
      args.source
  ):
    raise errors.InvalidSCCInputError(
        "The source must either be the full resource "
        "name or the numeric source ID."
    )
  if resource_pattern.match(args.source):
    # Handle full resource name
    return args.source
  return util.GetParentFromPositionalArguments(args) + "/sources/" + args.source


def GetSourceParentFromResourceName(resource_name):
  resource_pattern = re.compile(
      "(organizations|projects|folders)/.*/sources/[0-9]+"
  )
  if not resource_pattern.match(resource_name):
    raise errors.InvalidSCCInputError(
        "When providing a full resource path, it must also include "
        "the organization, project, or folder prefix."
    )
  list_source_components = resource_name.split("/")
  return (
      GetParentFromResourceName(resource_name)
      + "/"
      + list_source_components[2]
      + "/"
      + list_source_components[3]
  )


def GetFindingIdFromName(finding_name):
  """Gets a finding id from the full resource name."""
  resource_pattern = re.compile(
      "(organizations|projects|folders)/.*/sources/[0-9-]+/findings/[a-zA-Z0-9]+$"
  )
  if not resource_pattern.match(finding_name):
    raise errors.InvalidSCCInputError(
        "When providing a full resource path, it must include the pattern "
        "organizations/[0-9]+/sources/[0-9-]+/findings/[a-zA-Z0-9]+."
    )
  list_finding_components = finding_name.split("/")
  return list_finding_components[len(list_finding_components) - 1]


def GetParentFromResourceName(resource_name):
  resource_pattern = re.compile("(organizations|projects|folders)/.*")
  if not resource_pattern.match(resource_name):
    raise errors.InvalidSCCInputError(
        "When providing a full resource path, it must also include the pattern "
        "the organization, project, or folder prefix."
    )
  list_organization_components = resource_name.split("/")
  return list_organization_components[0] + "/" + list_organization_components[1]


def ConvertStateInput(state):
  """Convert state input to messages.Finding.StateValueValuesEnum object."""
  if state:
    state = state.upper()
  unspecified_state = messages.Finding.StateValueValuesEnum.STATE_UNSPECIFIED
  state_dict = {
      "ACTIVE": messages.Finding.StateValueValuesEnum.ACTIVE,
      "INACTIVE": messages.Finding.StateValueValuesEnum.INACTIVE,
      "STATE_UNSPECIFIED": unspecified_state,
  }
  return state_dict.get(state, unspecified_state)


def ValidateAndGetParent(args):
  """Validates parent."""
  if args.organization is not None:  # Validates organization.
    if "/" in args.organization:
      pattern = re.compile("^organizations/[0-9]{1,19}$")
      if not pattern.match(args.organization):
        raise errors.InvalidSCCInputError(
            "When providing a full resource path, it must include the pattern "
            "'^organizations/[0-9]{1,19}$'."
        )
      else:
        return args.organization
    else:
      pattern = re.compile("^[0-9]{1,19}$")
      if not pattern.match(args.organization):
        raise errors.InvalidSCCInputError(
            "Organization does not match the pattern '^[0-9]{1,19}$'."
        )
      else:
        return "organizations/" + args.organization

  if args.folder is not None:  # Validates folder.
    if "/" in args.folder:
      pattern = re.compile("^folders/.*$")
      if not pattern.match(args.folder):
        raise errors.InvalidSCCInputError(
            "When providing a full resource path, it must include the pattern "
            "'^folders/.*$'."
        )
      else:
        return args.folder
    else:
      return "folders/" + args.folder

  if args.project is not None:  # Validates project.
    if "/" in args.project:
      pattern = re.compile("^projects/.*$")
      if not pattern.match(args.project):
        raise errors.InvalidSCCInputError(
            "When providing a full resource path, it must include the pattern "
            "'^projects/.*$'."
        )
      else:
        return args.project
    else:
      return "projects/" + args.project


def ValidateMutexOnSourceAndParent(args):
  """Validates that only a full resource name or split arguments are provided."""
  if "/" in args.source and args.parent is not None:
    raise errors.InvalidSCCInputError(
        "Only provide a full resource name "
        "(organizations/123/sources/456) or a --parent flag, not both."
    )


def ExtractSecurityMarksFromResponse(response, args):
  """Returns security marks from finding response."""
  del args
  list_finding_response = list(response)
  if len(list_finding_response) > 1:
    raise errors.InvalidSCCInputError(
        "ListFindingResponse must only return one finding since it is "
        "filtered by Finding Name.")
  for finding_result in list_finding_response:
    return finding_result.finding.securityMarks


def ValidateSourceAndFindingIdIfParentProvided(args):
  """Validates that source and finding id are provided if parent is provided."""
  if args.source is None:
    raise errors.InvalidSCCInputError("--source flag must be provided.")
  if "/" in args.finding:
    raise errors.InvalidSCCInputError(
        "Finding id must be provided, instead of the full resource name."
    )
