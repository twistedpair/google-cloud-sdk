# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Utilities Anthos GKE On-Prem resource operations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkeonprem import client
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.command_lib.container.vmware import flags
from googlecloudsdk.core import resources

MAX_LRO_POLL_INTERVAL_MS = 10000  # 10 seconds

MAX_LRO_WAIT_MS = 7200000  # 2 hours


class OperationsClient(client.ClientBase):
  """Client for operations in Anthos GKE On-Prem API resources."""

  def __init__(self, **kwargs):
    super(OperationsClient, self).__init__(**kwargs)
    self._service = self._client.projects_locations_operations

  def Wait(self, operation=None, operation_ref=None):
    """Waits for an LRO to complete.

    Args:
      operation: object, operation to wait for.
      operation_ref: operation resource argument reference.

    Returns:
      The GetOperation API response after the operation completes.
    """
    if operation:
      operation_ref = resources.REGISTRY.ParseRelativeName(
          operation.name,
          collection='gkeonprem.projects.locations.operations',
      )

    return waiter.WaitFor(
        waiter.CloudOperationPollerNoResources(self._service),
        operation_ref,
        'Waiting for operation [{}] to complete'.format(
            operation_ref.RelativeName()),
        wait_ceiling_ms=MAX_LRO_POLL_INTERVAL_MS,
        max_wait_ms=MAX_LRO_WAIT_MS)

  def List(self, args):
    """List operations."""
    list_req = self._messages.GkeonpremProjectsLocationsOperationsListRequest(
        name=self._location_name(args))
    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='operations',
        batch_size=flags.Get(args, 'page_size'),
        limit=flags.Get(args, 'limit'),
        batch_size_attribute='pageSize',
    )
