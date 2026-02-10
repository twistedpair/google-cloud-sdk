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
"""Flags for Firewall Plus Endpoint commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.network_security.firewall_endpoints import activation_api
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps as deps_lib
from googlecloudsdk.calliope.concepts import multitype
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import properties


ENDPOINT_RESOURCE_NAME = "FIREWALL_ENDPOINT"
ORG_ENDPOINT_RESOURCE_COLLECTION = (
    "networksecurity.organizations.locations.firewallEndpoints"
)
PROJECT_ENDPOINT_RESOURCE_COLLECTION = (
    "networksecurity.projects.locations.firewallEndpoints"
)
BILLING_HELP_TEST = (
    "The Google Cloud project ID to use for API enablement check, quota, and"
    " endpoint uptime billing."
)


def OrgEndpointResourceSpec(api_version):
  """Returns the resource spec for an organization level firewall endpoint."""
  return concepts.ResourceSpec(
      ORG_ENDPOINT_RESOURCE_COLLECTION,
      "firewall endpoint",
      api_version=api_version,
      organizationsId=concepts.ResourceParameterAttributeConfig(
          "organization",
          "Organization ID of the {resource}.",
          parameter_name="organizationsId",
      ),
      locationsId=concepts.ResourceParameterAttributeConfig(
          "zone",
          "Zone of the {resource}.",
          parameter_name="locationsId",
      ),
      firewallEndpointsId=concepts.ResourceParameterAttributeConfig(
          "endpoint-name",
          "Name of the {resource}",
          parameter_name="firewallEndpointsId",
      ),
  )


def ProjectEndpointResourceSpec(api_version):
  """Returns the resource spec for a project level firewall endpoint."""
  return concepts.ResourceSpec(
      PROJECT_ENDPOINT_RESOURCE_COLLECTION,
      "firewall endpoint",
      api_version=api_version,
      projectsId=concepts.ResourceParameterAttributeConfig(
          name="project",
          help_text=(
              "Project ID of the Google Cloud project for the {resource}."
          ),
          fallthroughs=[
              # Do not fallthrough to the --project flag, as this will prompt
              # the user to choose between project and org scoped endpoints when
              # supplying both --organization and --project.
              deps_lib.PropertyFallthrough(properties.VALUES.core.project),
          ],
      ),
      locationsId=concepts.ResourceParameterAttributeConfig(
          "zone",
          "Zone of the {resource}.",
          parameter_name="locationsId",
      ),
      firewallEndpointsId=concepts.ResourceParameterAttributeConfig(
          "endpoint-name",
          "Name of the {resource}",
          parameter_name="firewallEndpointsId",
      ),
  )


def AddEndpointResource(release_track, parser, project_scope_supported=False):
  """Adds Firewall Plus endpoint resource."""
  api_version = activation_api.GetApiVersion(release_track)
  concept_specs = [
      OrgEndpointResourceSpec(api_version),
  ]
  if project_scope_supported:
    concept_specs.append(ProjectEndpointResourceSpec(api_version))
  resource_spec = multitype.MultitypeResourceSpec(
      "firewall endpoint",
      *concept_specs,
      allow_inactive=True,
  )
  presentation_spec = presentation_specs.MultitypeResourcePresentationSpec(
      name=ENDPOINT_RESOURCE_NAME,
      concept_spec=resource_spec,
      required=True,
      group_help="Firewall Plus.",
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
  return (
      lambda x: activation_api.GetEffectiveApiEndpoint(release_track) + x.name
  )


def AddOrganizationArg(parser, help_text="Organization of the endpoint"):
  parser.add_argument("--organization", required=True, help=help_text)


def AddDescriptionArg(parser, help_text="Description of the endpoint"):
  parser.add_argument("--description", required=False, help=help_text)


def AddTargetFirewallAttachmentArg(
    parser,
    help_text="Target firewall attachment where third party endpoint forwards traffic."
):
  parser.add_argument(
      "--target-firewall-attachment", required=False, help=help_text
  )


def AddEnableJumboFramesArg(
    parser,
    required=False,
    help_text="Enable jumbo frames for the firewall endpoint. To disable jumbo frames, use --no-enable-jumbo-frames.",
):
  parser.add_argument(
      "--enable-jumbo-frames",
      required=required,
      help=help_text,
      action="store_true",
  )


def AddZoneArg(parser, required=True, help_text="Zone of the endpoint"):
  parser.add_argument("--zone", required=required, help=help_text)


def AddBillingProjectArg(
    parser,
    required=True,
    help_text=BILLING_HELP_TEST,
):
  """Add billing project argument to parser.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
    required: bool, whether to make this argument required.
    help_text: str, help text to overwrite the generic --billing-project help
      text.
  """
  parser.add_argument(
      "--billing-project",
      required=required,
      help=help_text,
      action=actions.StoreProperty(properties.VALUES.billing.quota_project),
  )


# We use the explicit --update-billing-project flag as opposed to the existent
# --billing-project flag because otherwise there will be an ambiguity when a
# user wants to update other things, but not the billing project.
# For example, to update the labels, a billing project is still needed for API
# quota, making the ambiguous call:
# gcloud network-security firewall-endpoints update \
#     --billing-project=proj --update-labels=k1=v1
# This is a common use for other gcloud update flags as well.
def AddUpdateBillingProjectArg(
    parser,
    required=False,
    help_text=BILLING_HELP_TEST,
):
  """Add update billing project argument to parser.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
    required: bool, whether to make this argument required.
    help_text: str, help text to display on the --update-billing-project help
      text.
  """
  parser.add_argument(
      "--update-billing-project",
      required=required,
      help=help_text,
      metavar="BILLING_PROJECT",
      action=actions.StoreProperty(properties.VALUES.billing.quota_project),
  )


def AddEnableWildfireArg(
    parser,
):
  """Adds --enable-wildfire flag.

  It corresponds to the proto field:
  google.cloud.networksecurity.v1main.FirewallEndpoint.WildfireSettings.enabled

  Args:
    parser: ArgumentInterceptor, An argparse parser.
  """
  parser.add_argument(
      "--enable-wildfire",
      action="store_true",
      required=False,
      help=(
          "If set to true, enable WildFire functionality on the endpoint. Use"
          " --enable-wildfire to enable. To disable, use --no-enable-wildfire."
      ),
  )


def AddWildfireRegionArg(
    parser,
):
  """Adds --wildfire-region flag."""
  parser.add_argument(
      "--wildfire-region",
      required=False,
      help=(
          "The region WildFire submissions from this endpoint will be sent to"
          " for analysis by WildFire. Defaults to the nearest available region."
      ),
  )


def AddContentCloudRegionArg(
    parser,
):
  """Adds --content-cloud-region flag."""
  parser.add_argument(
      "--content-cloud-region",
      required=False,
      help=(
          "The content cloud region the endpoint will use. Defaults to the"
          " nearest available region."
      ),
  )


def AddWildfireLookupTimeoutArg(
    parser,
):
  """Adds --wildfire-lookup-timeout flag.

  It corresponds to the proto field:
  google.cloud.networksecurity.v1main.FirewallEndpoint.WildfireSettings
  .wildfire_realtime_lookup_duration.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
  """
  parser.add_argument(
      "--wildfire-lookup-timeout",
      type=int,
      required=False,
      help=(
          "The timeout (in milliseconds) to hold a file while the WildFire real"
          " time signature cloud performs a signature lookup."
      ),
  )


def AddWildfireLookupActionArg(
    parser,
):
  """Adds --wildfire-lookup-action flag.

  It corresponds to the proto field:
  google.cloud.networksecurity.v1main.FirewallEndpoint.WildfireSettings
  .wildfire_realtime_lookup_timeout_action.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
  """
  parser.add_argument(
      "--wildfire-lookup-action",
      choices=["ALLOW", "DENY"],
      required=False,
      help=(
          "The action to take on WildFire real time signature lookup timeout."
      ),
  )


def AddWildfireAnalysisTimeoutArg(
    parser,
):
  """Adds --wildfire-analysis-timeout flag.

  It corresponds to the proto field:
  google.cloud.networksecurity.v1main.FirewallEndpoint.WildfireSettings.WildfireInlineCloudAnalysisSettings
  .max_analysis_duration.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
  """
  parser.add_argument(
      "--wildfire-analysis-timeout",
      type=int,
      required=False,
      help=(
          "The timeout (in milliseconds) on a file being held while WildFire"
          " inline cloud analysis is performed."
      ),
  )


def AddWildfireAnalysisActionArg(
    parser,
):
  """Adds --wildfire-analysis-action flag.

  It corresponds to the proto field:
  google.cloud.networksecurity.v1main.FirewallEndpoint.WildfireSettings.WildfireInlineCloudAnalysisSettings.timeout_action.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
  """
  parser.add_argument(
      "--wildfire-analysis-action",
      choices=["ALLOW", "DENY"],
      required=False,
      help="The action to take on WildFire inline cloud analysis timeout.",
  )


def AddEnableWildfireAnalysisLoggingArg(
    parser,
):
  """Adds enable-wildfire-analysis-logging flag.

  It corresponds to the proto field:
  google.cloud.networksecurity.v1main.FirewallEndpoint.WildfireSettings.WildfireInlineCloudAnalysisSettings
  .timeout_logging_disabled.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
  """
  parser.add_argument(
      "--enable-wildfire-analysis-logging",
      action="store_true",
      required=False,
      help=(
          "Whether to disable WildFire submission log generation for files that"
          " timeout during WildFire inline cloud analysis. Defaults to false."
      ),
  )


def AddBlockPartialHttpArg(
    parser,
):
  """Adds --block-partial-http flag.

  It corresponds to the proto field:
  google.cloud.networksecurity.v1main.FirewallEndpoint.EndpointSettings
  .http_partial_response_blocked.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
  """
  parser.add_argument(
      "--block-partial-http",
      action="store_true",
      required=False,
      help=(
          "Whether the endpoint will block HTTP partial responses. Defaults to"
          " false."
      ),
  )
