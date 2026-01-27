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
"""This module contains a generic, object-oriented deployer for Google Cloud resources."""

from typing import Any

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.command_lib.declarative_pipeline.handlers.base import GcpResourceHandler
from googlecloudsdk.core import log


def _print_padded_request(request: Any) -> None:
  """Prints a multi-line request object with consistent indentation."""
  for line in str(request).splitlines():
    log.status.Print(f"     {line}")


def deploy_gcp_resource(handler: GcpResourceHandler) -> None:
  """Deploys a GCP resource using the given handler."""
  resource_id = handler.get_resource_id()
  resource_type_name = handler.resource.type
  log.status.Print(
      f"     Checking for existing {resource_type_name}: '{resource_id}'"
  )
  try:
    existing_resource = handler.find_existing_resource()
    local_definition = handler.get_local_definition()
    if existing_resource:
      log.status.Print(
          f"     Found existing {resource_type_name}. "
          "Comparing configurations..."
      )
      changed_fields = handler.compare(existing_resource, local_definition)
      if not changed_fields:
        log.status.Print(
            f"     {resource_type_name.capitalize()} is already up-to-date."
        )
        return
      log.status.Print(
          f"     Differences found in fields: {', '.join(changed_fields)}. "
          "Patching..."
      )
      request = handler.build_update_request(
          existing_resource, local_definition, changed_fields
      )

      if handler.dry_run:
        log.status.Print(f"     [DRY RUN] Would update {resource_type_name}")
        if handler.show_requests:
          _print_padded_request(request)
      else:
        if handler.show_requests:
          log.error("--- GCP API UPDATE REQUEST ---")
          _print_padded_request(request)
        operation = handler.get_update_method()(request=request)
        _, name_to_print = handler.wait_for_operation(operation)
        log.status.Print(
            f"     Successfully updated {resource_type_name}:"
            f" {name_to_print or resource_id}"
        )
    else:
      log.status.Print(
          f"     {resource_type_name.capitalize()} not found. Creating a new"
          " one..."
      )
      request = handler.build_create_request(local_definition)

      if handler.dry_run:
        log.status.Print(f"     [DRY RUN] Would create {resource_type_name}")
        if handler.show_requests:
          _print_padded_request(request)
      else:
        if handler.show_requests:
          log.error("--- GCP API CREATE REQUEST ---")
          _print_padded_request(request)
        operation = handler.get_create_method()(request=request)
        _, name_to_print = handler.wait_for_operation(operation)
        log.status.Print(
            f"     Successfully created {resource_type_name}:"
            f" {name_to_print or resource_id}"
        )
  except (apitools_exceptions.HttpError, ValueError) as e:
    raise ValueError(
        f"Failed to deploy resource '{resource_id}' of type"
        f" '{resource_type_name}'"
    ) from e
