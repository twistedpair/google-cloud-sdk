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
"""Flags for Mirroring Deployment commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.network_security.mirroring_deployments import api
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import resources

DEPLOYMENT_RESOURCE_NAME = "MIRRORING_DEPLOYMENT"
DEPLOYMENT_RESOURCE_COLLECTION = (
    "networksecurity.projects.locations.mirroringDeployments"
)
DEPLOYMENT_GROUP_RESOURCE_COLLECTION = (
    "networksecurity.projects.locations.mirroringDeploymentGroups"
)


def AddDeploymentResource(release_track, parser):
  """Adds Mirroring Deployment resource."""
  api_version = api.GetApiVersion(release_track)
  resource_spec = concepts.ResourceSpec(
      "networksecurity.projects.locations.mirroringDeployments",
      "mirroring deployment",
      api_version=api_version,
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=concepts.ResourceParameterAttributeConfig(
          "location",
          "Location of the {resource}.",
          parameter_name="locationsId",
      ),
      mirroringDeploymentsId=concepts.ResourceParameterAttributeConfig(
          "deployment-id",
          "Id of the {resource}",
          parameter_name="mirroringDeploymentsId",
      ),
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=DEPLOYMENT_RESOURCE_NAME,
      concept_spec=resource_spec,
      required=True,
      group_help="Mirroring Deployment.",
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddDescriptionArg(
    parser, help_text="Description of the mirroring deployment"
):
  """Adds a resource argument for Google Cloud description."""
  parser.add_argument("--description", required=False, help=help_text)


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
            "Location of the Mirroring Deployment. Defaults to {}".format(
                default_keyword
            ),
        )
    )

  return concepts.ResourceParameterAttributeConfig(
      name="location",
      help_text="Location of the {resource}.",
      fallthroughs=fallthroughs,
  )


def GetLocationResourceSpec(default=None):
  """Constructs and returns the Resource specification for Location."""
  return concepts.ResourceSpec(
      "networksecurity.projects.locations",
      resource_name="location",
      locationsId=LocationAttributeConfig(default=default),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def AddLocationResourceArg(
    parser: parser_arguments.ArgumentInterceptor, help_text: str, default=None
):
  """Adds a resource argument for Google Cloud location.

  Args:
    parser: The argparse.parser to add the resource arg to.
    help_text: str, the text of the help message.
    default: Optional default value for the arg.
  """
  concept_parsers.ConceptParser.ForResource(
      "--location", GetLocationResourceSpec(default=default), help_text
  ).AddToParser(parser)


def AddForwardingRuleArg(
    parser, required=True, help_text="Forwarding rule of the deployment"
):
  parser.add_argument("--forwarding-rule", required=required, help=help_text)


def RegionAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name="forwarding-rule-location",
      help_text="The Cloud region for the {resource}.",
  )


def AddForwardingRuleResource(parser):
  """Adds forwardingRule resource."""
  resource_spec = concepts.ResourceSpec(
      resource_collection="compute.forwardingRules",
      resource_name="forwardingRule",
      api_version="v1",
      project=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      region=RegionAttributeConfig(),
      forwardingRule=concepts.ResourceParameterAttributeConfig(
          "forwarding-rule-id",
          "Id of the {resource}",
          parameter_name="forwardingRuleId",
      ),
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name="--forwarding-rule",
      concept_spec=resource_spec,
      required=True,
      group_help="Mirroring Deployment Forwarding Rule.",
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddMirroringDeploymentGroupResource(release_track, parser):
  """Adds mirroring deployment group resource."""
  api_version = api.GetApiVersion(release_track)
  collection_info = resources.REGISTRY.GetCollectionInfo(
      DEPLOYMENT_GROUP_RESOURCE_COLLECTION,
      api_version=api_version,
  )
  resource_spec = concepts.ResourceSpec(
      "networksecurity.projects.locations.mirroringDeploymentGroups",
      "mirroring deployment group",
      api_version=api_version,
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=concepts.ResourceParameterAttributeConfig(
          "location",
          "Location of the {resource}.",
          parameter_name="locationsId",
          fallthroughs=[
              deps.ArgFallthrough("--location"),
              deps.FullySpecifiedAnchorFallthrough(
                  [deps.ArgFallthrough(DEPLOYMENT_RESOURCE_COLLECTION)],
                  collection_info,
                  "locationsId",
              ),
          ],
      ),
      mirroringDeploymentGroupsId=concepts.ResourceParameterAttributeConfig(
          "id",
          "Id of the {resource}",
          parameter_name="mirroringDeploymentGroupsId",
      ),
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name="--mirroring-deployment-group",
      concept_spec=resource_spec,
      required=True,
      group_help="Mirroring Deployment Group.",
      prefixes=True,
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)
