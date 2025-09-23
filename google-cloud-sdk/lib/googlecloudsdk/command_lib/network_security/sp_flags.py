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
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs

DEFAULT_ACTIONS = ["DEFAULT_ACTION", "ALLOW", "ALERT", "DENY"]
DEFAULT_PROFILE_TYPES = ["THREAT_PREVENTION"]


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


def AddSecurityProfileResource(parser, release_track):
  """Adds Security Profile Threat Prevention type."""
  name = "security_profile"
  resource_spec = concepts.ResourceSpec(
      resource_collection=(
          "networksecurity.organizations.locations.securityProfiles"
      ),
      resource_name="security_profile",
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
          "security_profile",
          "Name of the {resource}.",
          parameter_name="securityProfilesId",
      ),
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      group_help="Security Profile Name.",
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


def GetLocationResourceSpec(default=None):
  """Constructs and returns the Resource specification for Location."""
  return concepts.ResourceSpec(
      "networksecurity.organizations.locations",
      resource_name="location",
      locationsId=LocationAttributeConfig(default=default),
      organizationsId=OrgAttributeConfig(),
  )


def AddLocationResourceArg(
    parser: parser_arguments.ArgumentInterceptor,
    help_text: str,
    required: bool = False,
    default=None,
):
  """Adds a resource argument for Google Cloud location.

  Args:
    parser: The argparse.parser to add the resource arg to.
    help_text: str, the text of the help message.
    required: bool, whether the argument is required.
    default: Optional default value for the arg.
  """
  concept_parsers.ConceptParser.ForResource(
      name="--location",
      resource_spec=GetLocationResourceSpec(default=default),
      group_help=help_text,
      required=required,
  ).AddToParser(parser)


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
