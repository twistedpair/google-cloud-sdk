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
"""Flags for Mirroring Deployment Group commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.network_security.mirroring_deployment_groups import api
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs

DEPLOYMENT_GROUP_RESOURCE_NAME = "MIRRORING_DEPLOYMENT_GROUP"


def AddDeploymentGroupResource(release_track, parser):
  """Adds Mirroring Deployment Group resource."""
  resource_spec = concepts.ResourceSpec(
      "networksecurity.projects.locations.mirroringDeploymentGroups",
      "mirroring deployment group",
      api_version=api.GetApiVersion(release_track),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=concepts.ResourceParameterAttributeConfig(
          "location",
          "Location of the {resource}.",
          parameter_name="locationsId",
      ),
      mirroringDeploymentGroupsId=concepts.ResourceParameterAttributeConfig(
          "deployment-group-id",
          "Id of the {resource}",
          parameter_name="mirroringDeploymentGroupsId",
      ),
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=DEPLOYMENT_GROUP_RESOURCE_NAME,
      concept_spec=resource_spec,
      required=True,
      group_help="Mirroring Deployment Group.",
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddMaxWait(
    parser,
    default_max_wait,
    help_text="Time to synchronously wait for the operation to complete, after which the operation continues asynchronously. Ignored if --no-async isn't specified. See $ gcloud topic datetimes for information on time formats.",
):
  """Adds --max-wait flag."""
  parser.add_argument(
      "--max-wait",
      dest="max_wait",
      required=False,
      default=default_max_wait,
      help=help_text,
      type=arg_parsers.Duration(),
  )


def MakeGetUriFunc(release_track):
  return lambda x: api.GetEffectiveApiEndpoint(release_track) + x.name


def AddProjectArg(parser, help_text="Project ID of the deployment group"):
  parser.add_argument("--project", required=True, help=help_text)


def AddLocationArg(parser, help_text="Location of the deployment group"):
  parser.add_argument("--location", required=True, help=help_text)


def LocationAttributeConfig(default="global"):
  """Gets Google Cloud location resource attribute."""
  fallthroughs = []
  if default:
    fallthroughs.append(
        deps.Fallthrough(
            lambda: default,
            "Location of the Mirroring Deployment Group. Defaults to {}".format(
                default)))
  return concepts.ResourceParameterAttributeConfig(
      name="location",
      help_text="Location of the {resource}.",
      fallthroughs=fallthroughs
  )


def GetLocationResourceSpec():
  """Constructs and returns the Resource specification for Location."""
  return concepts.ResourceSpec(
      "networksecurity.projects.locations",
      resource_name="location",
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def AddLocationResourceArg(parser: parser_arguments.ArgumentInterceptor,
                           help_text):
  """Adds a resource argument for Google Cloud location.

  Args:
    parser: The argparse.parser to add the resource arg to.
    help_text: str, the text of the help message.
  """
  concept_parsers.ConceptParser.ForResource(
      "--location",
      GetLocationResourceSpec(),
      help_text,
      required=True,
  ).AddToParser(parser)


def AddNetworkResource(parser):
  """Adds network resource."""
  resource_spec = concepts.ResourceSpec(
      "compute.networks",
      "network",
      api_version="v1",
      project=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      network=concepts.ResourceParameterAttributeConfig(
          "network-name",
          "Name of the {resource}",
          parameter_name="network",
      ),
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name="--network",
      concept_spec=resource_spec,
      required=True,
      group_help="Mirroring Deployment Group.",
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)
