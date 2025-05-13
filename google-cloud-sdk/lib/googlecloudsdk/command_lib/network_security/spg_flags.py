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
"""Flags for Security Profile Group commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import List

from googlecloudsdk.api_lib.network_security.security_profile_groups import spg_api
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import resources

_SECURITY_PROFILE_RESOURCE_COLLECTION = (
    "networksecurity.organizations.locations.securityProfiles"
)
_SECURITY_PROFILE_GROUP_RESOURCE_COLLECTION = (
    "networksecurity.organizations.locations.securityProfileGroups"
)
_THREAT_PREVENTION_PROFILE_RESOURCE_NAME = "--threat-prevention-profile"
_SECURITY_PROFILE_GROUP_RESOURCE_NAME = "SECURITY_PROFILE_GROUP"


def AddProfileGroupDescription(parser, required=False):
  parser.add_argument(
      "--description",
      required=required,
      help="Brief description of the security profile group",
  )


def AddSecurityProfileResource(
    parser,
    release_track,
    arg_name: str,
    help_text="Path to Security Profile resource.",
    group=None,
    required=False,
    arg_aliases: List[str] = None,
):
  """Adds Security Profile resource.

  Args:
    parser: The parser for the command.
    release_track: The release track for the command.
    arg_name: The name used for the arg, e.g. "--threat-prevention-profile" or
      "--custom-mirroring-profile".
    help_text: The help text for the resource.
    group: The group that the resource is an argument of.
    required: Whether the resource is required.
    arg_aliases: The list of aliases for the arg, for backwards compatibility.
      Sub-flags named {alias}-organization and {alias}-location will be added to
      the parser and used as fallthrough args for the resource.

  Returns:
      The resource parser.
  """
  api_version = spg_api.GetApiVersion(release_track)
  collection_info = resources.REGISTRY.Clone().GetCollectionInfo(
      _SECURITY_PROFILE_GROUP_RESOURCE_COLLECTION, api_version
  )
  if arg_name.startswith("--"):
    arg_name = arg_name[2:]

  organization_resource_spec = concepts.ResourceParameterAttributeConfig(
      "organization",
      "Organization ID of the Security Profile.",
      parameter_name="organizationsId",
      fallthroughs=[
          deps.ArgFallthrough("--organization"),
          deps.FullySpecifiedAnchorFallthrough(
              [
                  deps.ArgFallthrough(
                      _SECURITY_PROFILE_GROUP_RESOURCE_COLLECTION
                  )
              ],
              collection_info,
              "organizationsId",
          ),
      ],
  )

  location_resource_spec = concepts.ResourceParameterAttributeConfig(
      "location",
      """
      Location of the {resource}.
      NOTE: Only `global` security profiles are supported.
      """,
      parameter_name="locationsId",
      fallthroughs=[
          deps.ArgFallthrough("--location"),
          deps.FullySpecifiedAnchorFallthrough(
              [
                  deps.ArgFallthrough(
                      _SECURITY_PROFILE_GROUP_RESOURCE_COLLECTION
                  )
              ],
              collection_info,
              "locationsId",
          ),
      ],
  )

  profile_id_resource_spec = concepts.ResourceParameterAttributeConfig(
      "name",
      "Name of security profile {resource}.",
      parameter_name="securityProfilesId",
  )

  if arg_aliases:
    for arg_alias in arg_aliases:
      org_flag_alias = f"--{arg_alias}-organization"
      loc_flag_alias = f"--{arg_alias}-location"
      parser.add_argument(
          org_flag_alias,
          required=False,
          hidden=True,
          help="Flag to preserve backward compatibility.",
      )
      parser.add_argument(
          loc_flag_alias,
          required=False,
          hidden=True,
          help="Flag to preserve backward compatibility.",
      )
      # Insert at beginning of fallthroughs, otherwise the fallthrough that
      # takes the value from the SPG resource will be used.
      organization_resource_spec.fallthroughs.insert(
          0, deps.ArgFallthrough(org_flag_alias)
      )
      location_resource_spec.fallthroughs.insert(
          0, deps.ArgFallthrough(loc_flag_alias)
      )

  resource_spec = concepts.ResourceSpec(
      _SECURITY_PROFILE_RESOURCE_COLLECTION,
      "Security Profile",
      api_version=api_version,
      organizationsId=organization_resource_spec,
      locationsId=location_resource_spec,
      securityProfilesId=profile_id_resource_spec,
  )

  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=f"--{arg_name}",
      concept_spec=resource_spec,
      required=required,
      group_help=help_text,
      group=group,
      prefixes=True,
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddSecurityProfileGroupResource(parser, release_track):
  """Adds Security Profile Group."""
  name = _SECURITY_PROFILE_GROUP_RESOURCE_NAME
  resource_spec = concepts.ResourceSpec(
      resource_collection=_SECURITY_PROFILE_GROUP_RESOURCE_COLLECTION,
      resource_name="security_profile_group",
      api_version=spg_api.GetApiVersion(release_track),
      organizationsId=concepts.ResourceParameterAttributeConfig(
          "organization",
          "Organization ID of Security Profile Group",
          parameter_name="organizationsId",
      ),
      locationsId=concepts.ResourceParameterAttributeConfig(
          "location",
          "location of the {resource} - Global.",
          parameter_name="locationsId",
      ),
      securityProfileGroupsId=concepts.ResourceParameterAttributeConfig(
          "security_profile_group",
          "Name of security profile group {resource}.",
          parameter_name="securityProfileGroupsId",
      ),
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      group_help="Security Profile Group Name.",
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)
