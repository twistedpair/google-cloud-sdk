# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""Dataproc resource handler."""

from collections.abc import Mapping
import dataclasses
from typing import Any, Tuple

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.dataproc import util as dataproc_util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.declarative_pipeline.handlers.base import GcpResourceHandler
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


@dataclasses.dataclass
class _DataprocHandle:
  """A handle providing necessary client and messages for Dataproc's `WaitForOperation`."""

  client: Any
  messages: Any


class DataprocClusterHandler(GcpResourceHandler):
  """Handler for Dataproc Cluster resources."""

  api_name = "dataproc"
  api_version = "v1"

  def wait_for_operation(
      self, operation: Any
  ) -> Tuple[Any, str]:
    """Waits for long running operation if applicable and returns result and name.

    Args:
      operation: The operation to wait for.

    Returns:
      A tuple containing the completed operation and a name to print.

    Raises:
      calliope_exceptions.ToolException: If the operation times out.
    """
    try:
      if not operation.done:
        operation = dataproc_util.WaitForOperation(
            _DataprocHandle(self.client, self.messages),
            operation,
            message="Waiting for Dataproc operation to complete:",
            timeout_s=600)
      response_dict = encoding.MessageToDict(operation.response)
      name_to_print = response_dict.get("clusterName", "?")
      return operation, name_to_print
    except waiter.TimeoutError as e:
      raise calliope_exceptions.ToolException(
          "Timed out waiting for Dataproc operation to complete.") from e

  def _get_client(self):
    universe_domain = properties.VALUES.core.universe_domain.Get()
    dataproc_endpoint = (
        f"https://{self.environment.region}-dataproc.{universe_domain}/"
    )
    properties.VALUES.api_endpoint_overrides.dataproc.Set(dataproc_endpoint)
    return super()._get_client()

  def get_resource_id(self) -> str:
    return self.resource.name

  def get_create_method(self) -> Any:
    return self.client.projects_regions_clusters.Create

  def get_update_method(self) -> Any:
    return self.client.projects_regions_clusters.Patch

  def find_existing_resource(self) -> Any:
    request = self.messages.DataprocProjectsRegionsClustersGetRequest(
        projectId=self.environment.project,
        region=self.environment.region,
        clusterName=self.get_resource_id(),
    )
    try:
      return self.client.projects_regions_clusters.Get(request)
    except apitools_exceptions.HttpNotFoundError:
      return None

  def get_local_definition(self) -> dict[str, Any]:
    definition = super().get_local_definition()
    definition["cluster_name"] = self.get_resource_id()
    return definition

  def compare(
      self, existing_resource: Any, local_definition: Mapping[str, Any]
  ) -> list[str]:
    changed_fields = []
    if self.debug:
      log.status.Print("--- Starting Dataproc comparison ---")

    def _find_diffs_recursive(local_sub_dict, existing_sub_proto, prefix=""):
      for key, local_value in local_sub_dict.items():
        current_path = f"{prefix}{key}"
        if key in ["autoDeleteTtl", "softwareConfig"]:
          if self.debug:
            log.status.Print(
                f"  - Skipping special key '{current_path}' as it cannot be"
                " compared."
            )
          continue
        existing_value = getattr(existing_sub_proto, key, None)
        if self.debug:
          log.warning(f"DEBUG: Comparing '{current_path}'")
          log.status.Print(
              f"  - Local: {local_value} (Type: {type(local_value)})"
          )
          log.status.Print(
              f"  - Existing: {existing_value} (Type: {type(existing_value)})"
          )
        if (
            key == "workerConfig"
            and not existing_value
            and local_value.get("numInstances") == 0
        ):
          if self.debug:
            log.status.Print(
                "  - Skipping workerConfig: 0 instances locally and no"
                " workerConfig remotely."
            )
          continue
        if (
            key.endswith("Uri")
            and isinstance(local_value, str)
            and isinstance(existing_value, str)
        ):
          if existing_value.endswith(local_value):
            if self.debug:
              log.status.Print("  - Values are equivalent URIs.")
            continue
        if isinstance(local_value, dict):
          if self.debug:
            log.status.Print("  - Recursing into nested object...")
          _find_diffs_recursive(
              local_value, existing_value, prefix=f"{current_path}."
          )
        elif local_value != existing_value:
          if self.debug:
            log.error(
                f"  - Difference found! Adding '{current_path}' to"
                " changed_fields."
            )
          changed_fields.append(current_path)
        else:
          if self.debug:
            log.status.Print("  - Values are identical.")

    if "config" in local_definition:
      _find_diffs_recursive(
          local_definition["config"], existing_resource.config, prefix="config."
      )
    existing_labels_dict = {}
    if existing_resource.labels:
      existing_labels_dict = {
          p.key: p.value
          for p in existing_resource.labels.additionalProperties
      }
    if "labels" in local_definition:
      labels_changed = False
      for key, value in local_definition["labels"].items():
        if (
            key not in existing_labels_dict
            or existing_labels_dict[key] != value
        ):
          labels_changed = True
          break
      if labels_changed:
        changed_fields.append("labels")

    if self.debug:
      log.status.Print("--- Finished Dataproc comparison ---")
    return changed_fields

  def build_create_request(self, definition: dict[str, Any]) -> Any:
    cluster_message = encoding.DictToMessage(definition, self.messages.Cluster)
    return self.messages.DataprocProjectsRegionsClustersCreateRequest(
        projectId=self.environment.project,
        region=self.environment.region,
        cluster=cluster_message,
    )

  def build_update_request(
      self,
      existing_resource: Any,
      definition: dict[str, Any],
      changed_fields: list[str],
  ) -> Any:
    del existing_resource  # Unused.
    cluster_message = encoding.DictToMessage(definition, self.messages.Cluster)
    return self.messages.DataprocProjectsRegionsClustersPatchRequest(
        projectId=self.environment.project,
        region=self.environment.region,
        clusterName=self.get_resource_id(),
        cluster=cluster_message,
        updateMask=",".join(changed_fields),
    )
