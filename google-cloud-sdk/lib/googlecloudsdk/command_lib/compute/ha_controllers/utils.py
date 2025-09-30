# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Flags for the compute ha-controllers commands."""

from apitools.base.protorpclite import messages
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import properties
from googlecloudsdk.generated_clients.apis.compute.alpha import compute_alpha_messages


def AddHaControllerNameArgToParser(parser, api_version=None):
  """Adds an HA Controller name resource argument."""
  ha_controller_data = yaml_data.ResourceYAMLData.FromPath(
      "compute.ha_controllers.ha_controller"
  )
  resource_spec = concepts.ResourceSpec.FromYaml(
      ha_controller_data.GetData(), is_positional=True, api_version=api_version
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name="ha_controller",
      concept_spec=resource_spec,
      required=True,
      group_help="Name of an HA Controller.",
  )
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def MakeZoneConfiguration(
    zone_config: list[dict[str, str]],
) -> compute_alpha_messages.HaController.ZoneConfigurationsValue:
  """Convert zone-configuration to the zoneConfigurations api field."""
  zone_configs_parsed: list[
      compute_alpha_messages.HaController.ZoneConfigurationsValue.AdditionalProperty
  ] = []

  for config in zone_config:
    if "zone" not in config:
      continue
    single_zone_config = {}
    if "reservation-affinity" in config:
      single_zone_config["reservationAffinity"] = (
          compute_alpha_messages.HaControllerZoneConfigurationReservationAffinity(
              consumeReservationType=compute_alpha_messages.HaControllerZoneConfigurationReservationAffinity.ConsumeReservationTypeValueValuesEnum(
                  config["reservation-affinity"],
              )
          )
      )
      if "reservation" in config:
        single_zone_config["reservationAffinity"].key = (
            "compute."
            + properties.VALUES.core.universe_domain.Get()
            + "/reservation-name"
        )
        single_zone_config["reservationAffinity"].values = [
            config["reservation"]
        ]
    if "node-affinity" in config:
      single_zone_config["nodeAffinity"] = (
          compute_alpha_messages.HaControllerZoneConfigurationNodeAffinity(
              operator=config["node-affinity"],
          )
      )
    zone_configs_parsed.append(
        compute_alpha_messages.HaController.ZoneConfigurationsValue.AdditionalProperty(
            key=config["zone"],
            value=compute_alpha_messages.HaControllerZoneConfiguration(
                **single_zone_config
            ),
        )
    )

  res = compute_alpha_messages.HaController.ZoneConfigurationsValue(
      additionalProperties=zone_configs_parsed
  )
  return res


def SetResourceName(unused_ref, unused_args, request):
  """Set resource.name to the provided haController ID.

  Args:
    unused_ref: An unused resource ref to the parsed resource.
    unused_args: The unused argparse namespace.
    request: The request to modify.

  Returns:
    The updated request.
  """
  if hasattr(request.haControllerResource, "name"):
    request.haControllerResource.name = request.haController
  return request


def EnumTypeToChoices(enum_type: messages.Enum) -> str:
  """Converts an enum type to a comma-separated list of choices."""
  return ", ".join(
      c
      for c in sorted(
          [arg_utils.EnumNameToChoice(n) for n in enum_type.names()]
      )
  )
