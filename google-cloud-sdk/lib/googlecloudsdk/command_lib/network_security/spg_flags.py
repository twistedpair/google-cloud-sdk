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
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.calliope.concepts import multitype
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

_ORG_SECURITY_PROFILE_RESOURCE_COLLECTION = (
    "networksecurity.organizations.locations.securityProfiles"
)
_PROJECT_SECURITY_PROFILE_RESOURCE_COLLECTION = (
    "networksecurity.projects.locations.securityProfiles"
)
_SECURITY_PROFILE_GROUP_RESOURCE_NAME = "security_profile_group"

ORG_LOCATION_RESOURCE_COLLECTION = "networksecurity.organizations.locations"
PROJECT_LOCATION_RESOURCE_COLLECTION = "networksecurity.projects.locations"
ORG_SECURITY_PROFILE_GROUP_RESOURCE_COLLECTION = (
    "networksecurity.organizations.locations.securityProfileGroups"
)
PROJECT_SECURITY_PROFILE_GROUP_RESOURCE_COLLECTION = (
    "networksecurity.projects.locations.securityProfileGroups"
)


def AddProfileGroupDescription(parser, required=False):
  parser.add_argument(
      "--description",
      required=required,
      help="Brief description of the security profile group",
  )


def OrgSecurityProfileResourceSpec(
    api_version, resource_name, org_config, location_config
):
  """Constructs and returns the Resource specification for Security Profile Group."""
  spec = concepts.ResourceSpec(
      resource_collection=_ORG_SECURITY_PROFILE_RESOURCE_COLLECTION,
      resource_name=resource_name,
      api_version=api_version,
      organizationsId=org_config,
      locationsId=location_config,
      securityProfilesId=concepts.ResourceParameterAttributeConfig(
          "name",
          "Name of security profile {resource}.",
          parameter_name="securityProfilesId",
      ),
  )
  return spec


def ProjectSecurityProfileResourceSpec(
    api_version, resource_name, project_config, location_config
):
  """Constructs and returns the Resource specification for Security Profile Group."""
  spec = concepts.ResourceSpec(
      resource_collection=_PROJECT_SECURITY_PROFILE_RESOURCE_COLLECTION,
      resource_name=resource_name,
      api_version=api_version,
      projectsId=project_config,
      locationsId=location_config,
      securityProfilesId=concepts.ResourceParameterAttributeConfig(
          "name",
          "Name of security profile {resource}.",
          parameter_name="securityProfilesId",
      ),
  )
  return spec


def AddSecurityProfileResource(
    parser,
    release_track,
    arg_name: str,
    help_text="Path to Security Profile resource.",
    group=None,
    required=False,
    arg_aliases: List[str] = None,
    project_scope_supported=False,
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
    project_scope_supported: Whether the resource supports project scope.

  Returns:
      The resource parser.
  """
  api_version = spg_api.GetApiVersion(release_track)
  if arg_name.startswith("--"):
    arg_name = arg_name[2:]
  # Resource name should be in lower snake case.
  resource_name = arg_name.replace("-", "_")

  location_config = concepts.ResourceParameterAttributeConfig(
      "location",
      """
      Location of the {resource}.
      NOTE: Only `global` security profiles are supported.
      """,
      parameter_name="locationsId",
      fallthroughs=[
          deps.ArgFallthrough("--location"),
          deps.FullySpecifiedAnchorFallthrough(
              [deps.ArgFallthrough(_SECURITY_PROFILE_GROUP_RESOURCE_NAME)],
              resources.REGISTRY.Clone().GetCollectionInfo(
                  ORG_SECURITY_PROFILE_GROUP_RESOURCE_COLLECTION,
                  api_version,
              ),
              "locationsId",
          ),
      ],
  )
  org_config = concepts.ResourceParameterAttributeConfig(
      name="organization",
      help_text="Organization ID of the Security Profile.",
      parameter_name="organizationsId",
      fallthroughs=[
          deps.ArgFallthrough("--organization"),
          deps.FullySpecifiedAnchorFallthrough(
              [deps.ArgFallthrough(_SECURITY_PROFILE_GROUP_RESOURCE_NAME)],
              resources.REGISTRY.Clone().GetCollectionInfo(
                  ORG_SECURITY_PROFILE_GROUP_RESOURCE_COLLECTION,
                  api_version,
              ),
              "organizationsId",
          ),
      ],
  )
  if project_scope_supported:
    location_config.fallthroughs.append(
        deps.FullySpecifiedAnchorFallthrough(
            [deps.ArgFallthrough(_SECURITY_PROFILE_GROUP_RESOURCE_NAME)],
            resources.REGISTRY.GetCollectionInfo(
                PROJECT_SECURITY_PROFILE_GROUP_RESOURCE_COLLECTION,
                api_version=api_version,
            ),
            "locationsId",
        )
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
      org_config.fallthroughs.insert(
          0, deps.ArgFallthrough(org_flag_alias)
      )
      location_config.fallthroughs.insert(
          0, deps.ArgFallthrough(loc_flag_alias)
      )

  concept_specs = [
      OrgSecurityProfileResourceSpec(
          api_version, resource_name, org_config, location_config
      )
  ]
  if project_scope_supported:
    project_config = concepts.ResourceParameterAttributeConfig(
        "project",
        "Project ID of the {resource}.",
        parameter_name="projectsId",
        fallthroughs=[
            # Do not fallthrough to the --project flag, as this will prompt
            # the user to choose between project and org scoped security
            # profiles when supplying both --organization and --project.
            deps.PropertyFallthrough(properties.VALUES.core.project),
            deps.FullySpecifiedAnchorFallthrough(
                [deps.ArgFallthrough(_SECURITY_PROFILE_GROUP_RESOURCE_NAME)],
                resources.REGISTRY.GetCollectionInfo(
                    PROJECT_SECURITY_PROFILE_GROUP_RESOURCE_COLLECTION,
                    api_version=api_version,
                ),
                "projectsId",
            ),
        ],
    )
    concept_specs.append(
        ProjectSecurityProfileResourceSpec(
            api_version, resource_name, project_config, location_config
        )
    )

  resource_spec = multitype.MultitypeResourceSpec(
      resource_name,
      *concept_specs,
      allow_inactive=True,
  )
  presentation_spec = presentation_specs.MultitypeResourcePresentationSpec(
      name=f"--{arg_name}",
      concept_spec=resource_spec,
      required=required,
      group_help=help_text,
      group=group,
      prefixes=True,
      flag_name_overrides={"project": f"--{arg_name}-project"},
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def OrgSecurityProfileGroupResourceSpec(release_track):
  """Constructs and returns the Resource specification for Security Profile Group."""
  return concepts.ResourceSpec(
      resource_collection=ORG_SECURITY_PROFILE_GROUP_RESOURCE_COLLECTION,
      resource_name=_SECURITY_PROFILE_GROUP_RESOURCE_NAME,
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
          _SECURITY_PROFILE_GROUP_RESOURCE_NAME,
          "Name of security profile group {resource}.",
          parameter_name="securityProfileGroupsId",
      ),
  )


def ProjectSecurityProfileGroupResourceSpec(release_track):
  """Constructs and returns the Resource specification for Security Profile Group."""
  return concepts.ResourceSpec(
      resource_collection=PROJECT_SECURITY_PROFILE_GROUP_RESOURCE_COLLECTION,
      resource_name=_SECURITY_PROFILE_GROUP_RESOURCE_NAME,
      api_version=spg_api.GetApiVersion(release_track),
      projectsId=concepts.ResourceParameterAttributeConfig(
          "project",
          "Project ID to which the changes should apply.",
          fallthroughs=[
              # Do not fallthrough to the --project flag, as this will prompt
              # the user to choose between project and org scoped security
              # profiles when supplying both --organization and --project.
              deps.PropertyFallthrough(properties.VALUES.core.project),
          ],
      ),
      locationsId=concepts.ResourceParameterAttributeConfig(
          "location",
          "location of the {resource} - Global.",
          parameter_name="locationsId",
      ),
      securityProfileGroupsId=concepts.ResourceParameterAttributeConfig(
          _SECURITY_PROFILE_GROUP_RESOURCE_NAME,
          "Name of security profile group {resource}.",
          parameter_name="securityProfileGroupsId",
      ),
  )


def AddSecurityProfileGroupResource(
    parser, release_track, project_scope_supported=False
):
  """Adds Security Profile Group."""
  concept_specs = [OrgSecurityProfileGroupResourceSpec(release_track)]
  if project_scope_supported:
    concept_specs.append(
        ProjectSecurityProfileGroupResourceSpec(release_track)
    )
  resource_spec = multitype.MultitypeResourceSpec(
      _SECURITY_PROFILE_GROUP_RESOURCE_NAME,
      *concept_specs,
      allow_inactive=True,
  )
  presentation_spec = presentation_specs.MultitypeResourcePresentationSpec(
      name=_SECURITY_PROFILE_GROUP_RESOURCE_NAME,
      concept_spec=resource_spec,
      required=True,
      group_help="Security Profile Group Name.",
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def MakeGetUriFunc(release_track):
  return lambda x: spg_api.GetEffectiveApiEndpoint(release_track) + x.name


def LocationAttributeConfig(default=None):
  """Gets Google Cloud location resource attribute."""
  default_keyword = default
  if default == "-":
    default_keyword = "a wildcard"

  fallthroughs = []
  if default:
    fallthroughs.append(
        deps.Fallthrough(
            lambda: default,
            "Location of the resource. Defaults to {}".format(default_keyword),
        )
    )

  return concepts.ResourceParameterAttributeConfig(
      name="location",
      help_text="Location of the {resource}.",
      fallthroughs=fallthroughs,
  )


def GetOrgLocationResourceSpec(default=None):
  """Constructs and returns the Resource specification for org Location."""
  return concepts.ResourceSpec(
      "networksecurity.organizations.locations",
      resource_name="location",
      locationsId=LocationAttributeConfig(default=default),
      organizationsId=concepts.ResourceParameterAttributeConfig(
          name="organization",
          help_text="Organization ID of the {resource}.",
      ),
  )


def GetProjectLocationResourceSpec(default=None):
  """Constructs and returns the Resource specification for project Location."""
  return concepts.ResourceSpec(
      "networksecurity.projects.locations",
      resource_name="location",
      locationsId=LocationAttributeConfig(default=default),
      projectsId=concepts.ResourceParameterAttributeConfig(
          "project",
          "Project ID of the {resource}.",
          fallthroughs=[
              # Do not fallthrough to the --project flag, as this will prompt
              # the user to choose between project and org scoped security
              # profiles when supplying both --organization and --project.
              deps.PropertyFallthrough(properties.VALUES.core.project),
          ],
      ),
  )


def AddLocationResourceArg(
    parser: parser_arguments.ArgumentInterceptor,
    help_text: str,
    required: bool = False,
    default=None,
    project_scope_supported: bool = False,
):
  """Adds a resource argument for Google Cloud location.

  Args:
    parser: The argparse.parser to add the resource arg to.
    help_text: str, the text of the help message.
    required: bool, whether the argument is required.
    default: Optional default value for the arg.
    project_scope_supported: bool, whether the argument supports project scope.
  """
  concept_specs = [GetOrgLocationResourceSpec(default=default)]
  if project_scope_supported:
    concept_specs.append(
        GetProjectLocationResourceSpec(default=default)
    )
  resource_spec = multitype.MultitypeResourceSpec(
      "location",
      *concept_specs,
      allow_inactive=True,
  )
  presentation_spec = presentation_specs.MultitypeResourcePresentationSpec(
      name="--location",
      concept_spec=resource_spec,
      required=required,
      group_help=help_text,
  )
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)
