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
"""Flags for Security Profile Threat Prevention commands."""

from __future__ import absolute_import
from __future__ import annotations
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.network_security.security_profiles import sp_api
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.calliope.concepts import multitype
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

DEFAULT_ACTIONS = ["DEFAULT_ACTION", "ALLOW", "ALERT", "DENY"]
DEFAULT_PROFILE_TYPES = ["THREAT_PREVENTION"]
ORG_SECURITY_PROFILE_RESOURCE_COLLECTION = (
    "networksecurity.organizations.locations.securityProfiles"
)
PROJECT_SECURITY_PROFILE_RESOURCE_COLLECTION = (
    "networksecurity.projects.locations.securityProfiles"
)
ORG_LOCATION_RESOURCE_COLLECTION = "networksecurity.organizations.locations"
PROJECT_LOCATION_RESOURCE_COLLECTION = "networksecurity.projects.locations"
INTERCEPT_ENDPOINT_GROUP_RESOURCE_COLLECTION = (
    "networksecurity.projects.locations.interceptEndpointGroups"
)
MIRRORING_ENDPOINT_GROUP_RESOURCE_COLLECTION = (
    "networksecurity.projects.locations.mirroringEndpointGroups"
)


def AddSeverityorThreatIDorAntivirusArg(parser, required=True):
  """Adds --antivirus, --severities, or --threat-ids flag."""
  severity_threatid_antivirus_args = parser.add_group(
      mutex=True, required=required
  )
  severity_threatid_antivirus_args.add_argument(
      "--severities",
      type=arg_parsers.ArgList(),
      metavar="SEVERITY_LEVEL",
      help=(
          "List of comma-separated severities where each value in the list"
          " indicates the severity of the threat."
      ),
  )
  severity_threatid_antivirus_args.add_argument(
      "--threat-ids",
      type=arg_parsers.ArgList(),
      metavar="THREAT-ID",
      help=(
          "List of comma-separated threat identifiers where each identifier in"
          " the list is a vendor-specified Signature ID representing a threat"
          " type. "
      ),
  )
  severity_threatid_antivirus_args.add_argument(
      "--antivirus",
      type=arg_parsers.ArgList(),
      metavar="PROTOCOL",
      help=(
          "List of comma-separated protocols where each value in the list"
          " indicates the protocol of the antivirus threat."
      ),
  )


def AddActionArg(parser, actions=None, required=True):
  choices = actions or DEFAULT_ACTIONS
  parser.add_argument(
      "--action",
      required=required,
      choices=choices,
      help="Action associated with antivirus, severity, or threat-id",
  )


def AddProfileDescription(parser, required=False):
  parser.add_argument(
      "--description",
      required=required,
      help="Brief description of the security profile",
  )


def OrgSecurityProfileResourceSpec(release_track, name):
  """Constructs and returns the Resource specification for Security Profile."""
  return concepts.ResourceSpec(
      resource_collection=ORG_SECURITY_PROFILE_RESOURCE_COLLECTION,
      resource_name=name,
      api_version=sp_api.GetApiVersion(release_track),
      organizationsId=concepts.ResourceParameterAttributeConfig(
          "organization",
          "Organization ID to which the changes should apply.",
          parameter_name="organizationsId",
      ),
      locationsId=concepts.ResourceParameterAttributeConfig(
          "location",
          "location of the {resource} - Global.",
          parameter_name="locationsId",
      ),
      securityProfilesId=concepts.ResourceParameterAttributeConfig(
          name,
          "Name of the {resource}.",
          parameter_name="securityProfilesId",
      ),
  )


def ProjectSecurityProfileResourceSpec(release_track, name):
  """Constructs and returns the Resource specification for Security Profile."""
  return concepts.ResourceSpec(
      resource_collection=PROJECT_SECURITY_PROFILE_RESOURCE_COLLECTION,
      resource_name=name,
      api_version=sp_api.GetApiVersion(release_track),
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
      securityProfilesId=concepts.ResourceParameterAttributeConfig(
          name,
          "Name of the {resource}.",
          parameter_name="securityProfilesId",
      ),
  )


def AddSecurityProfileResource(
    parser, release_track, project_scope_supported=False
):
  """Adds Security Profile resource to parser."""
  name = "security_profile"
  concept_specs = [OrgSecurityProfileResourceSpec(release_track, name)]
  if project_scope_supported:
    concept_specs.append(
        ProjectSecurityProfileResourceSpec(release_track, name)
    )
  resource_spec = multitype.MultitypeResourceSpec(
      name,
      *concept_specs,
      allow_inactive=True,
  )
  presentation_spec = presentation_specs.MultitypeResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      group_help="Security Profile Name.",
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddInterceptEndpointGroupResource(
    release_track, parser, project_scope_supported=False
):
  """Adds intercept endpoint group resource."""
  api_version = sp_api.GetApiVersion(release_track)
  project_fallthroughs = [
      deps.ArgFallthrough("--project"),
      deps.PropertyFallthrough(properties.VALUES.core.project),
  ]
  location_fallthroughs = [
      deps.ArgFallthrough("--location"),
      deps.FullySpecifiedAnchorFallthrough(
          [deps.ArgFallthrough("security_profile")],
          resources.REGISTRY.GetCollectionInfo(
              ORG_SECURITY_PROFILE_RESOURCE_COLLECTION, api_version=api_version
          ),
          "locationsId",
      ),
  ]
  if project_scope_supported:
    project_fallthroughs.append(
        deps.FullySpecifiedAnchorFallthrough(
            [deps.ArgFallthrough("security_profile")],
            resources.REGISTRY.GetCollectionInfo(
                PROJECT_SECURITY_PROFILE_RESOURCE_COLLECTION,
                api_version=api_version,
            ),
            "projectsId",
        )
    )
    location_fallthroughs.append(
        deps.FullySpecifiedAnchorFallthrough(
            [deps.ArgFallthrough("security_profile")],
            resources.REGISTRY.GetCollectionInfo(
                PROJECT_SECURITY_PROFILE_RESOURCE_COLLECTION,
                api_version=api_version,
            ),
            "locationsId",
        )
    )
  resource_spec = concepts.ResourceSpec(
      INTERCEPT_ENDPOINT_GROUP_RESOURCE_COLLECTION,
      "intercept endpoint group",
      api_version=api_version,
      projectsId=concepts.ResourceParameterAttributeConfig(
          "project",
          "Project ID of the {resource}.",
          parameter_name="projectsId",
          fallthroughs=project_fallthroughs,
      ),
      locationsId=concepts.ResourceParameterAttributeConfig(
          "location",
          "Location of the {resource}.",
          parameter_name="locationsId",
          fallthroughs=location_fallthroughs,
      ),
      interceptEndpointGroupsId=concepts.ResourceParameterAttributeConfig(
          "id",
          "Id of the {resource}",
          parameter_name="interceptEndpointGroupsId",
      ),
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name="--intercept-endpoint-group",
      concept_spec=resource_spec,
      required=True,
      group_help="Intercept Endpoint Group.",
      prefixes=True,
      flag_name_overrides={"project": "--intercept-endpoint-group-project"},
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddMirroringEndpointGroupResource(
    release_track, parser, project_scope_supported=False
):
  """Adds mirroring endpoint group resource."""
  api_version = sp_api.GetApiVersion(release_track)
  project_fallthroughs = [
      deps.ArgFallthrough("--project"),
      deps.PropertyFallthrough(properties.VALUES.core.project),
  ]
  location_fallthroughs = [
      deps.ArgFallthrough("--location"),
      deps.FullySpecifiedAnchorFallthrough(
          [deps.ArgFallthrough("security_profile")],
          resources.REGISTRY.GetCollectionInfo(
              ORG_SECURITY_PROFILE_RESOURCE_COLLECTION, api_version=api_version
          ),
          "locationsId",
      ),
  ]
  if project_scope_supported:
    project_fallthroughs.append(
        deps.FullySpecifiedAnchorFallthrough(
            [deps.ArgFallthrough("security_profile")],
            resources.REGISTRY.GetCollectionInfo(
                PROJECT_SECURITY_PROFILE_RESOURCE_COLLECTION,
                api_version=api_version,
            ),
            "projectsId",
        )
    )
    location_fallthroughs.append(
        deps.FullySpecifiedAnchorFallthrough(
            [deps.ArgFallthrough("security_profile")],
            resources.REGISTRY.GetCollectionInfo(
                PROJECT_SECURITY_PROFILE_RESOURCE_COLLECTION,
                api_version=api_version,
            ),
            "locationsId",
        )
    )
  resource_spec = concepts.ResourceSpec(
      MIRRORING_ENDPOINT_GROUP_RESOURCE_COLLECTION,
      "mirroring endpoint group",
      api_version=api_version,
      projectsId=concepts.ResourceParameterAttributeConfig(
          "project",
          "Project ID of the {resource}.",
          parameter_name="projectsId",
          fallthroughs=project_fallthroughs,
      ),
      locationsId=concepts.ResourceParameterAttributeConfig(
          "location",
          "Location of the {resource}.",
          parameter_name="locationsId",
          fallthroughs=location_fallthroughs,
      ),
      mirroringEndpointGroupsId=concepts.ResourceParameterAttributeConfig(
          "id",
          "Id of the {resource}",
          parameter_name="mirroringEndpointGroupsId",
      ),
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name="--mirroring-endpoint-group",
      concept_spec=resource_spec,
      required=True,
      group_help="Mirroring Endpoint Group.",
      prefixes=True,
      flag_name_overrides={"project": "--mirroring-endpoint-group-project"},
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def MakeGetUriFunc(release_track):
  return lambda x: sp_api.GetEffectiveApiEndpoint(release_track) + x.name


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


def OrgAttributeConfig():
  """Gets Google Cloud organization resource attribute."""
  return concepts.ResourceParameterAttributeConfig(
      name="organization",
      help_text="Organization ID of the {resource}.",
  )


def GetOrgLocationResourceSpec(default=None):
  """Constructs and returns the Resource specification for org Location."""
  return concepts.ResourceSpec(
      "networksecurity.organizations.locations",
      resource_name="location",
      locationsId=LocationAttributeConfig(default=default),
      organizationsId=OrgAttributeConfig(),
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


def AddCustomMirroringDeploymentGroupsArg(
    parser: parser_arguments.ArgumentInterceptor,
    help_text: str = "List of comma-separated full names of mirroring-deployment-group resources.",
    required: bool = False,
    default: list[str] | None = None,
):
  """Adds the `mirroringDeploymentGroups` arg for CustomMirroring SPs (Broker)."""
  parser.add_argument(
      "--mirroring-deployment-groups",
      type=arg_parsers.ArgList(),
      metavar="MIRRORING_DEPLOYMENT_GROUPS",
      help=help_text,
      required=required,
      default=default,
  )
