# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Utilities for Package Rollouts Rollouts API."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.fleet.packages import util
from googlecloudsdk.api_lib.util import waiter

ROLLOUT_COLLECTION = 'configdelivery.projects.locations.fleetPackages.rollouts'


class RolloutsClient(object):
  """Client for Rollouts in Config Delivery Package Rollouts API."""

  def __init__(self, api_version, client=None, messages=None):
    self._api_version = api_version or util.DEFAULT_API_VERSION
    self.client = client or util.GetClientInstance(self._api_version)
    self.messages = messages or util.GetMessagesModule(self.client)
    self._service = self.client.projects_locations_fleetPackages_rollouts
    self.rollout_waiter = waiter.CloudOperationPollerNoResources(
        operation_service=self.client.projects_locations_operations,
        get_name_func=lambda x: x.name,
    )

  def List(self, project, location, fleet_package, limit=None, page_size=100):
    """List Rollouts of a Fleet Package.

    Args:
      project: GCP project id.
      location: Valid GCP location (e.g. us-central1).
      fleet_package: Name of parent Fleet Package.
      limit: int or None, the total number of results to return.
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results).

    Returns:
      Generator of matching devices.
    """
    list_request = self.messages.ConfigdeliveryProjectsLocationsFleetPackagesRolloutsListRequest(
        parent=f'projects/{project}/locations/{location}/fleetPackages/{fleet_package}',
        orderBy='create_time desc',
    )
    return list_pager.YieldFromList(
        self._service,
        list_request,
        field='rollouts',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize',
    )

  def Describe(self, project, location, fleet_package, rollout):
    """Describe a Rollout resource.

    Args:
      project: GCP project ID.
      location: GCP location of Fleet Package.
      fleet_package: Name of parent Fleet Package.
      rollout: Name of Rollout.

    Returns:
      Requested Rollout resource.
    """
    fully_qualified_path = f'projects/{project}/locations/{location}/fleetPackages/{fleet_package}/rollouts/{rollout}'
    describe_req = self.messages.ConfigdeliveryProjectsLocationsFleetPackagesRolloutsGetRequest(
        name=fully_qualified_path
    )
    return self._service.Get(describe_req)

  def Abort(self, project, location, fleet_package, rollout, reason=None):
    """Abort an in-progress Rollout.

    Args:
      project: GCP project ID.
      location: GCP location of Fleet Package.
      fleet_package: Name of parent Fleet Package.
      rollout: Name of Rollout.
      reason: Reason for aborting the Rollout.

    Returns:
      None.

    Raises:
      apitools.base.py.HttpError: If the request returns an HTTP error.
    """
    fully_qualified_path = f'projects/{project}/locations/{location}/fleetPackages/{fleet_package}/rollouts/{rollout}'
    abort_req = self.messages.ConfigdeliveryProjectsLocationsFleetPackagesRolloutsAbortRequest(
        name=fully_qualified_path,
        abortRolloutRequest=self.messages.AbortRolloutRequest(reason=reason),
    )
    waiter.WaitFor(
        self.rollout_waiter,
        self._service.Abort(abort_req),
        f'Aborting Rollout {rollout}',
    )

  def Resume(self, project, location, fleet_package, rollout, reason=None):
    """Resume a suspended Rollout.

    Args:
      project: GCP project ID.
      location: GCP location of Fleet Package.
      fleet_package: Name of parent Fleet Package.
      rollout: Name of Rollout.
      reason: Reason for resuming the Rollout.

    Returns:
      None.

    Raises:
      apitools.base.py.HttpError: If the request returns an HTTP error.
    """
    fully_qualified_path = f'projects/{project}/locations/{location}/fleetPackages/{fleet_package}/rollouts/{rollout}'
    resume_req = self.messages.ConfigdeliveryProjectsLocationsFleetPackagesRolloutsResumeRequest(
        name=fully_qualified_path,
        resumeRolloutRequest=self.messages.ResumeRolloutRequest(reason=reason),
    )
    waiter.WaitFor(
        self.rollout_waiter,
        self._service.Resume(resume_req),
        f'Resuming Rollout {rollout}',
    )

  def Suspend(self, project, location, fleet_package, rollout, reason=None):
    """Suspend an in-progress Rollout.

    Args:
      project: GCP project ID.
      location: GCP location of Fleet Package.
      fleet_package: Name of parent Fleet Package.
      rollout: Name of Rollout.
      reason: Reason for suspending the Rollout.

    Returns:
      None.

    Raises:
      apitools.base.py.HttpError: If the request returns an HTTP error.
    """
    fully_qualified_path = f'projects/{project}/locations/{location}/fleetPackages/{fleet_package}/rollouts/{rollout}'
    suspend_req = self.messages.ConfigdeliveryProjectsLocationsFleetPackagesRolloutsSuspendRequest(
        name=fully_qualified_path,
        suspendRolloutRequest=self.messages.SuspendRolloutRequest(
            reason=reason
        ),
    )
    waiter.WaitFor(
        self.rollout_waiter,
        self._service.Suspend(suspend_req),
        f'Suspending Rollout {rollout}',
    )
