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
"""Cloud Workstations workstations API utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.api_lib.workstations.util import GetClientInstance
from googlecloudsdk.api_lib.workstations.util import GetMessagesModule
from googlecloudsdk.api_lib.workstations.util import VERSION_MAP
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import resources


class Workstations:
  """The Workstations set of Cloud Workstations API functions."""

  def __init__(self, release_track=base.ReleaseTrack.BETA):
    self.api_version = VERSION_MAP.get(release_track)
    self.client = GetClientInstance(release_track)
    self.messages = GetMessagesModule(release_track)
    self._service = self.client.projects_locations_workstationClusters_workstationConfigs_workstations

  def Start(self, args):
    """Start a workstation."""
    workstation_name = args.CONCEPTS.workstation.Parse().RelativeName()
    workstation_id = arg_utils.GetFromNamespace(
        args, 'workstation', use_defaults=True)
    start_req = self.messages.WorkstationsProjectsLocationsWorkstationClustersWorkstationConfigsWorkstationsStartRequest(
        name=workstation_name)
    op_ref = self._service.Start(start_req)

    log.status.Print(
        'Starting workstation: [{}]'.format(workstation_id))

    if args.async_:
      log.status.Print('Check operation [{}] for status.'.format(op_ref.name))
      return op_ref

    op_resource = resources.REGISTRY.ParseRelativeName(
        op_ref.name,
        collection='workstations.projects.locations.operations',
        api_version=self.api_version)
    poller = waiter.CloudOperationPoller(
        self._service, self.client.projects_locations_operations)

    waiter.WaitFor(poller, op_resource,
                   'Waiting for operation [{}] to complete'.format(op_ref.name))
    log.status.Print('Started workstation [{}].'.format(workstation_id))

  def Stop(self, args):
    """Stop a workstation."""
    workstation_name = args.CONCEPTS.workstation.Parse().RelativeName()
    workstation_id = arg_utils.GetFromNamespace(
        args, 'workstation', use_defaults=True)
    stop_req = self.messages.WorkstationsProjectsLocationsWorkstationClustersWorkstationConfigsWorkstationsStopRequest(
        name=workstation_name)
    op_ref = self._service.Stop(stop_req)

    log.status.Print(
        'Stopping workstation: [{}]'.format(workstation_id))

    if args.async_:
      log.status.Print('Check operation [{}] for status.'.format(op_ref.name))
      return op_ref

    op_resource = resources.REGISTRY.ParseRelativeName(
        op_ref.name,
        collection='workstations.projects.locations.operations',
        api_version=self.api_version)
    poller = waiter.CloudOperationPoller(
        self._service, self.client.projects_locations_operations)

    waiter.WaitFor(poller, op_resource,
                   'Waiting for operation [{}] to complete'.format(op_ref.name))
    log.status.Print('Stopped workstation [{}].'.format(workstation_id))
