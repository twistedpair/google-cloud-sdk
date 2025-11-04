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
from apitools.base.py import encoding
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import yaml


_MESSAGES = apis.GetMessagesModule("compute", "alpha")


def GetMessagesModule(version="alpha"):
  return apis.GetMessagesModule("compute", version)


class NodeAffinityFileParseError(core_exceptions.Error):
  """Exception for invalid node affinity file format."""


def AddHaControllerNameArgToParser(parser, api_version=None):
  """Adds an HA Controller name resource_data argument."""
  ha_controller_data = yaml_data.ResourceYAMLData.FromPath(
      "compute.ha_controllers.ha_controller"
  )
  resource_data_spec = concepts.ResourceSpec.FromYaml(
      ha_controller_data.GetData(), is_positional=True, api_version=api_version
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name="ha_controller",
      concept_spec=resource_data_spec,
      required=True,
      group_help="Name of an HA Controller.",
  )
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def MakeZoneConfiguration(
    zone_config: list[dict[str, str]],
) -> _MESSAGES.HaController.ZoneConfigurationsValue:
  """Convert zone-configuration to the zoneConfigurations api field."""
  zone_configs_parsed: list[
      _MESSAGES.HaController.ZoneConfigurationsValue.AdditionalProperty
  ] = []

  for config in zone_config:
    if "zone" not in config:
      continue
    single_zone_config = {}
    if "reservation-affinity" in config:
      single_zone_config["reservationAffinity"] = (
          _MESSAGES.HaControllerZoneConfigurationReservationAffinity(
              consumeReservationType=_MESSAGES.HaControllerZoneConfigurationReservationAffinity.ConsumeReservationTypeValueValuesEnum(
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
    node_affinities = _GetNodeAffinities(config)
    if node_affinities:
      single_zone_config["nodeAffinities"] = node_affinities

    zone_configs_parsed.append(
        _MESSAGES.HaController.ZoneConfigurationsValue.AdditionalProperty(
            key=config["zone"],
            value=_MESSAGES.HaControllerZoneConfiguration(
                **single_zone_config
            ),
        )
    )

  res = _MESSAGES.HaController.ZoneConfigurationsValue(
      additionalProperties=zone_configs_parsed
  )
  return res


def MakeNetworkConfiguration(
    network_config: list[dict[str, str]],
) -> _MESSAGES.HaControllerNetworkingAutoConfiguration:
  """Convert network-auto-configuration args to the networkConfiguration api field."""
  network_config_parsed = {}
  if network_config and len(network_config) > 1:
    raise exceptions.InvalidArgumentException(
        "--network-auto-configuration",
        "Only one network interface can be specified."
    )
  network_config = network_config[0] if network_config else {}

  if "stack-type" in network_config:
    network_config_parsed["stackType"] = network_config["stack-type"]
  if "address" in network_config:
    network_config_parsed["ipAddress"] = network_config["address"]
  if "internal-ipv6-address" in network_config:
    network_config_parsed["ipv6Address"] = (
        network_config["internal-ipv6-address"]
    )

  return _MESSAGES.HaControllerNetworkingAutoConfiguration(
      internal=_MESSAGES.HaControllerNetworkingAutoConfigurationInternal(
          **network_config_parsed
      )
  )


def SetResourceName(unused_ref, unused_args, request):
  """Set resource_data.name to the provided haController ID.

  Args:
    unused_ref: An unused resource_data ref to the parsed resource_data.
    unused_args: The unused argparse namespace.
    request: The request to modify.

  Returns:
    The updated request.
  """
  if hasattr(request.haControllerResource, "name"):
    request.haControllerResource.name = request.haController
  return request


def _GetNodeAffinities(config: dict[str, str]) -> list[
    _MESSAGES.HaControllerZoneConfigurationNodeAffinity
]:
  """Get node affinities from the zone configuration."""
  node_affinity_operator_enum = (
      _MESSAGES.HaControllerZoneConfigurationNodeAffinity.OperatorValueValuesEnum
  )
  node_affinities = []

  if "node-affinity-file" in config:
    affinities_yaml = yaml.load(config["node-affinity-file"])
    if not affinities_yaml:  # Catch empty files/lists.
      raise NodeAffinityFileParseError(
          "No node affinity labels specified. You must specify at least one "
          "label to create a sole tenancy instance."
      )
    for affinity in affinities_yaml:
      if not affinity:  # Catches None and empty dicts
        raise NodeAffinityFileParseError("Empty list item in JSON/YAML file.")
      try:
        node_affinity = encoding.PyValueToMessage(
            _MESSAGES.HaControllerZoneConfigurationNodeAffinity,
            affinity,
        )
      except Exception as e:  # pylint: disable=broad-except
        raise NodeAffinityFileParseError(e)
      if not node_affinity.key:
        raise NodeAffinityFileParseError(
            "A key must be specified for every node affinity label."
        )
      if node_affinity.all_unrecognized_fields():
        raise NodeAffinityFileParseError(
            "Key [{0}] has invalid field formats for: {1}".format(
                node_affinity.key, node_affinity.all_unrecognized_fields()
            )
        )

      node_affinities.append(node_affinity)
  if "node-group" in config:
    node_affinities.append(
        _MESSAGES.HaControllerZoneConfigurationNodeAffinity(
            key="compute."
            + properties.VALUES.core.universe_domain.Get()
            + "/node-group-name",
            operator=node_affinity_operator_enum.IN,
            values=[config["node-group"]],
        )
    )
  if "node" in config:
    node_affinities.append(
        _MESSAGES.HaControllerZoneConfigurationNodeAffinity(
            key="compute."
            + properties.VALUES.core.universe_domain.Get()
            + "/node-name",
            operator=node_affinity_operator_enum.IN,
            values=[config["node"]],
        )
    )
  if "node-project" in config:
    node_affinities.append(
        _MESSAGES.HaControllerZoneConfigurationNodeAffinity(
            key="compute."
            + properties.VALUES.core.universe_domain.Get()
            + "/project",
            operator=node_affinity_operator_enum.IN,
            values=[config["node-project"]],
        )
    )

  return node_affinities


def EnumTypeToChoices(enum_type: messages.Enum) -> str:
  """Converts an enum type to a comma-separated list of choices."""
  return ", ".join(
      c
      for c in sorted(
          [arg_utils.EnumNameToChoice(n) for n in enum_type.names()]
      )
  )


def FixExportStructure(
    resource_data: dict[str, str]) -> dict[str, str]:
  """Changes the API structure to the export structure."""
  if "zoneConfigurations" in resource_data:
    resource_data["zoneConfiguration"] = resource_data["zoneConfigurations"]
    del resource_data["zoneConfigurations"]
  if (
      "networkingAutoConfiguration" in resource_data
      and "internal" in resource_data["networkingAutoConfiguration"]
  ):
    resource_data["networkingAutoConfiguration"] = resource_data[
        "networkingAutoConfiguration"
    ]["internal"]
  return resource_data


def FixImportStructure(
    resource_data: dict[str, str]) -> dict[str, str]:
  """Changes and completes the export structure to the API structure."""
  if "zoneConfiguration" in resource_data:
    resource_data["zoneConfigurations"] = resource_data["zoneConfiguration"]
    del resource_data["zoneConfiguration"]
  if ("networkingAutoConfiguration" in resource_data):
    resource_data["networkingAutoConfiguration"] = {"internal": resource_data[
        "networkingAutoConfiguration"
    ]}
  return resource_data
