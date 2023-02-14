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
"""Utilities for simulation commands."""
import json

from googlecloudsdk.api_lib.network_management.simulation import Messages
from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import yaml


class InvalidFileError(exceptions.Error):
  """Error if a file is not valid JSON."""


class InvalidInputError(exceptions.Error):
  """Error if the user supplied is not valid."""


def GetSimulationApiVersionFromArgs(args):
  """Return API version based on args.

  Args:
    args: The argparse namespace.

  Returns:
    API version (e.g. v1alpha or v1beta).
  """

  release_track = args.calliope_command.ReleaseTrack()
  if release_track == base.ReleaseTrack.ALPHA:
    return "v1alpha1"

  raise exceptions.InternalError("Unsupported release track.")


def PrepareSimulationChanges(
    proposed_changes_file,
    api_version,
    file_format,
    simulation_type,
    original_config_file=None,
):
  """Given a json containing the resources which are to be updated, it return a list of config changes.

  Args:
    proposed_changes_file: File path containing the proposed changes
    api_version: API Version
    file_format: Format of the file
    simulation_type: Type of simulation
    original_config_file: Original config changes file provided in case of GCP
      config

  Returns:
    List of config changes in the format accepted by API
  """

  if file_format == "gcp":
    if not original_config_file:
      return InvalidInputError("Original config changes file not provided.")
    return ParseGCPSimulationConfigChangesFile(
        proposed_changes_file,
        api_version,
        simulation_type,
        original_config_file,
    )

  raise InputInputError("Invalid file-format.")


def MapResourceType(resource_type):
  if resource_type == "compute#firewall":
    return "compute.googleapis.com/Firewall"

  raise InvalidInputError(
      "Only Firewall resources are supported. Instead found {}".format(
          resource_type
      )
  )


def MapSimulationTypeToRequest(
    api_version, config_changes_list, simulation_type
):
  """Parse and map the appropriate simulation type to request."""
  if not config_changes_list:
    print("No new changes to simulate.")
    exit()
  if simulation_type == "shadowed-firewall":
    return Messages(api_version).Simulation(
        configChanges=config_changes_list,
        shadowedFirewallSimulationData=Messages(
            api_version
        ).ShadowedFirewallSimulationData(),
    )

  if simulation_type == "connectivity-test":
    return Messages(api_version).Simulation(
        configChanges=config_changes_list,
        connectivityTestSimulationData=Messages(
            api_version
        ).ConnectivityTestSimulationData(),
    )

  raise InvalidInputError("Invalid simulation-type.")


def AddSelfLinkGCPResource(proposed_resource_config):
  if "name" not in proposed_resource_config:
    raise InvalidInputError("`name` key missing in one of resource(s) config.")

  name = proposed_resource_config["name"]
  project_id = properties.VALUES.core.project.Get()
  proposed_resource_config["selfLink"] = (
      "projects/{}/global/firewalls/{}".format(project_id, name)
  )


def ParseGCPSimulationConfigChangesFile(
    proposed_changes_file, api_version, simulation_type, original_config_file
):
  """Parse and convert the config changes file into API Format."""
  try:
    proposed_resources_config = yaml.load_path(proposed_changes_file)
  except yaml.YAMLParseError as unused_ref:
    raise InvalidFileError(
        "Error parsing config changes file: [{}]".format(proposed_changes_file)
    )

  try:
    original_resources_config = yaml.load_path(original_config_file)
  except yaml.YAMLParseError as unused_ref:
    raise InvalidFileError(
        "Error parsing the original config file: [{}]".format(
            original_config_file
        )
    )

  original_config_resource_list = []
  update_resource_list = []
  config_changes_list = []

  for original_resource_config in original_resources_config:
    if "kind" not in original_resource_config:
      raise InvalidInputError(
          "`kind` key missing in one of resource(s) config."
      )
    if "selfLink" not in original_resource_config:
      raise InvalidInputError(
          "`selfLink` missing in one of original resource(s) config."
      )
    original_config_resource_list.append(original_resource_config["selfLink"])

  for proposed_resource_config in proposed_resources_config:
    if "kind" not in proposed_resource_config:
      raise InvalidInputError(
          "`kind` key missing in one of resource(s) config."
      )

    if "direction" not in proposed_resource_config:
      # If direction is not specified in resource type,
      # default direction is INGRESS
      # (https://cloud.google.com/vpc/docs/using-firewalls#gcloud)
      proposed_resource_config["direction"] = "INGRESS"
    update_type = IdentifyChangeUpdateType(
        proposed_resource_config,
        original_config_resource_list,
        api_version,
        update_resource_list,
    )

    config_change = Messages(api_version).ConfigChange(
        updateType=update_type,
        assetType=MapResourceType(proposed_resource_config["kind"]),
        proposedConfigBody=json.dumps(proposed_resource_config, sort_keys=True),
    )
    config_changes_list.append(config_change)

  enum = Messages(api_version).ConfigChange.UpdateTypeValueValuesEnum
  for original_resource_config in original_resources_config:
    original_self_link = original_resource_config["selfLink"]
    if original_self_link not in update_resource_list:
      resource_config = {"selfLink": original_self_link}
      config_change = Messages(api_version).ConfigChange(
          updateType=enum.DELETE,
          assetType=MapResourceType(original_resource_config["kind"]),
          proposedConfigBody=json.dumps(resource_config, sort_keys=True),
      )
      config_changes_list.append(config_change)

  return MapSimulationTypeToRequest(
      api_version, config_changes_list, simulation_type
  )


def IdentifyChangeUpdateType(
    proposed_resource_config,
    original_resource_config_list,
    api_version,
    update_resource_list,
):
  """Given a proposed resource config, it returns the update type."""
  enum = Messages(api_version).ConfigChange.UpdateTypeValueValuesEnum
  if "selfLink" in proposed_resource_config:
    self_link = proposed_resource_config["selfLink"]
    if self_link in original_resource_config_list:
      update_resource_list.append(self_link)
      return enum.UPDATE
  else:
    AddSelfLinkGCPResource(proposed_resource_config)
    return enum.INSERT
