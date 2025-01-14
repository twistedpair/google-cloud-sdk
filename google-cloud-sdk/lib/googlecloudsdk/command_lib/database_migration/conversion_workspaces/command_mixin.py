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
"""Mixin for conversion workspaces commands."""

import argparse
from typing import Optional

from googlecloudsdk.api_lib.database_migration import conversion_workspaces
from googlecloudsdk.api_lib.database_migration import filter_rewrite
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.generated_clients.apis.datamigration.v1 import datamigration_v1_messages as messages


class ConversionWorkspacesCommandMixin:
  """Mixin for conversion workspaces commands."""

  @property
  def client(self) -> conversion_workspaces.ConversionWorkspacesClient:
    """Return the conversion workspaces client."""
    return conversion_workspaces.ConversionWorkspacesClient(
        release_track=self.ReleaseTrack(),
    )

  def ExtractBackendFilter(self, args: argparse.Namespace) -> Optional[str]:
    """Extract the backend filter from the filter argument.

    Args:
      args: The command line arguments.

    Returns:
      The backend filter if present, None otherwise.

    Raises:
      RuntimeError: If the backend filter has already been extracted.
    """
    if not args.IsKnownAndSpecified('filter'):
      return None

    if getattr(args, 'backend_filter_extracted', False):
      raise RuntimeError(
          'Backend filter has already been extracted and can only be extracted'
          ' once.'
      )

    args.filter, backend_filter = filter_rewrite.Rewriter().Rewrite(args.filter)
    setattr(args, 'backend_filter_extracted', True)
    return backend_filter or None

  def HandleOperationResult(
      self,
      conversion_workspace_ref: resources.Resource,
      result_operation: messages.Operation,
      operation_name: str,
      sync: bool,
      has_resource: bool = True,
  ) -> Optional[messages.Operation]:
    """Handle the LRO for the conversion workspace.

    Args:
      conversion_workspace_ref: The conversion workspace reference.
      result_operation: The LRO result operation.
      operation_name: The name of the operation (capitalized and in past tense).
      sync: Whether to wait for the LRO to complete.
      has_resource: Whether the operation contaions a resource when done.

    Returns:
      The LRO status if async, None if sync.
    """
    if not sync:
      return self.client.lro.Read(
          operation=result_operation,
          project_id=conversion_workspace_ref.projectsId,
          location_id=conversion_workspace_ref.locationsId,
      )

    log.status.Print(
        'Waiting for conversion workspace'
        f' [{conversion_workspace_ref.conversionWorkspacesId}] to be'
        f' {operation_name.lower()} with [{result_operation.name}]',
    )
    self.client.lro.Wait(
        operation=result_operation,
        has_resource=has_resource,
    )
    log.status.Print(
        f'{operation_name} conversion workspace'
        f' {conversion_workspace_ref.conversionWorkspacesId} [{result_operation.name}]',
    )
