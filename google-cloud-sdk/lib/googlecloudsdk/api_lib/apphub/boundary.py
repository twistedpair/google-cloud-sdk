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
"""Apphub Boundary API."""

from googlecloudsdk.api_lib.apphub import consts as api_lib_consts
from googlecloudsdk.api_lib.apphub import utils as api_lib_utils
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import exceptions


class BoundaryClient(object):
  """Client for boundaries in the App Hub API."""

  def __init__(self, release_track):
    self._client = api_lib_utils.GetClientInstance(release_track)
    self._messages = api_lib_utils.GetMessagesModule(release_track)
    self._service = self._client.projects_locations
    self._poller = waiter.CloudOperationPoller(
        self._service, self._client.projects_locations_operations
    )

  def Describe(self, boundary_name):
    """Gets a Boundary resource."""
    request = self._messages.ApphubProjectsLocationsGetBoundaryRequest(
        name=boundary_name
    )
    return self._service.GetBoundary(request)

  def Update(self, boundary_name, args):
    """Updates a Boundary resource."""
    update_mask = []
    boundary = self._messages.Boundary()

    if args.IsSpecified('crm_node'):
      update_mask.append('crm_node')
      if args.crm_node:  # Check if the provided value is non-empty
        boundary.crmNode = args.crm_node

    if not update_mask:
      raise exceptions.ToolException(
          'Must specify at least one field to update.'
      )

    request = self._messages.ApphubProjectsLocationsUpdateBoundaryRequest(
        name=boundary_name,
        boundary=boundary,
        updateMask=','.join(update_mask),
        requestId=args.request_id,
    )

    operation = self._service.UpdateBoundary(request)

    if args.async_:
      return operation

    # The WaitForOperation helper polls the LRO until it's done, which is a
    # standard pattern in the App Hub gcloud implementation.
    return api_lib_utils.WaitForOperation(
        self._poller,
        operation,
        api_lib_consts.UpdateBoundary.WAIT_FOR_UPDATE_MESSAGE,
        api_lib_consts.UpdateBoundary.UPDATE_TIMELIMIT_SEC,
    )
