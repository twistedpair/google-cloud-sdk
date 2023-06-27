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
"""Apphub Topology API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.apphub import consts as api_lib_consts
from googlecloudsdk.api_lib.apphub import utils as api_lib_utils
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.command_lib.apphub import utils as command_lib_utils
from googlecloudsdk.core import log


class TopologyClient(object):
  """Client for topology in Apphub API."""

  def __init__(self, client=None, messages=None):
    self._generated_client = client or api_lib_utils.GetClientInstance()
    self.messages = messages or api_lib_utils.GetMessagesModule()
    self._topology_client = self._generated_client.projects_locations
    self._poller = waiter.CloudOperationPoller(
        self._topology_client,
        self._generated_client.projects_locations_operations,
    )

  def Describe(self):
    get_request = (
        self.messages.ApphubProjectsLocationsGetTopologyRequest(
            name=command_lib_utils.GetGlobalTopologyResourceRelativeName()
        )
    )
    return self._topology_client.GetTopology(get_request)

  def _UpdateHelper(self, args):
    """Helper to generate topology and update_mask fields for update_request."""
    topology = self.messages.Topology()
    update_mask = ''

    if args.enable or args.disable:
      topology.enabled = bool(args.enable)
      update_mask = api_lib_utils.AddToUpdateMask(
          update_mask,
          api_lib_consts.UpdateTopology.UPDATE_MASK_ENABLED_FIELD_NAME,
      )

    return topology, update_mask

  def Update(self, args):
    """Update topology."""
    topology, update_mask = self._UpdateHelper(args)

    if not update_mask:
      log.status.Print(api_lib_consts.UpdateTopology.EMPTY_UPDATE_HELP_TEXT)
      return

    update_request = (
        self.messages.ApphubProjectsLocationsUpdateTopologyRequest(
            name=command_lib_utils.GetGlobalTopologyResourceRelativeName(),
            topology=topology,
            updateMask=update_mask
        )
    )

    operation = self._topology_client.UpdateTopology(update_request)
    update_response = api_lib_utils.WaitForOperation(
        self._poller,
        operation,
        api_lib_consts.UpdateTopology.WAIT_FOR_UPDATE_MESSAGE,
        api_lib_consts.UpdateTopology.UPDATE_TIMELIMIT_SEC,
    )

    log.UpdatedResource(
        update_response.name, kind=api_lib_consts.Resource.TOPOLOGY
    )

    return update_response
