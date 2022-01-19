# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Flags for IDS commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.ids import ids_api
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs


def AddDescriptionArg(parser):
  parser.add_argument(
      "--description", required=False, help="Description of the endpoint.")


DEFAULT_SEVERITIES = ["INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


def AddSeverityArg(parser, required=True, severity_levels=None):
  choices = severity_levels or DEFAULT_SEVERITIES
  parser.add_argument(
      "--severity",
      required=required,
      choices=choices,
      help="The minimum severity of threats to report on.")


def AddNetworkArg(parser,
                  required=True,
                  help_text="The name of the VPC network to monitor"):
  parser.add_argument("--network", required=required, help=help_text)


def AddZoneArg(parser, required=True, help_text="The zone of the endpoint"):
  parser.add_argument("--zone", required=required, default="-", help=help_text)


def AddTrafficLogsArg(
    parser,
    help_text="Whether to enable traffic logs on the endpoint. Enabling "
    "traffic logs can generate a large number of logs which can "
    "increase costs in Cloud Logging."):
  parser.add_argument(
      "--enable-traffic-logs",
      dest="enable_traffic_logs",
      required=False,
      default=False,
      help=help_text,
      action="store_true")


def AddEndpointResource(parser):
  name = "endpoint"
  resource_spec = concepts.ResourceSpec(
      "ids.projects.locations.endpoints",
      "endpoint",
      endpointId=concepts.ResourceParameterAttributeConfig(
          "endpoint", "The name of the {resource}"),
      locationId=concepts.ResourceParameterAttributeConfig(
          "zone", "The zone of the {resource}.", parameter_name="locationId"),
      projectId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      group_help="endpoint.")
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddMaxWait(parser,
               default_max_wait,
               help_text="Time to synchronously wait for the operation to "
               "complete, after which the operation continues asynchronously. "
               "Ignored if --no-async isn't specified. "
               "See $ gcloud topic datetimes for information on time formats."):
  parser.add_argument(
      "--max-wait",
      dest="max_wait",
      required=False,
      default=default_max_wait,
      help=help_text,
      type=arg_parsers.Duration())


def MakeGetUriFunc(release_track):
  return lambda x: ids_api.GetEffectiveApiEndpoint(release_track) + x.name
