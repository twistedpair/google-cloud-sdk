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
"""Utilities Anthos clusters on VMware operations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import resources


class OperationsClient(object):
  """Client for operations in Anthos clusters on VMware API."""

  def __init__(self, client=None):
    self.client = client or apis.GetClientInstance('gkeonprem', 'v1')
    self._service = self.client.projects_locations_operations

  def Wait(self, operation):
    """Waits for an LRO to complete.

    Args:
      operation: object, operation to wait for.

    Returns:
      The GetOperation API response after the operation completes.
    """
    operation_ref = resources.REGISTRY.ParseRelativeName(
        operation.name,
        collection='gkeonprem.projects.locations.operations',
    )

    return waiter.WaitFor(
        waiter.CloudOperationPollerNoResources(self._service),
        operation_ref,
        'Waiting for operation [{}] to complete'.format(operation.name),
    )
