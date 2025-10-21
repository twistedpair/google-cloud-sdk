# -*- coding: utf-8 -*- #
#
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
"""Common utility functions for Developer Connect Insights Configs Discover App Hub."""
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.apphub import utils as api_lib_utils
from googlecloudsdk.calliope import base


class DiscoveredApphubClient(object):
  """Client for workloads and services in App Hub API."""

  def __init__(self):
    release_track = base.ReleaseTrack.GA
    self.client = api_lib_utils.GetClientInstance(release_track)
    self.messages = api_lib_utils.GetMessagesModule(release_track)
    self._app_workloads_client = (
        self.client.projects_locations_applications_workloads
    )
    self._app_services_client = (
        self.client.projects_locations_applications_services
    )

  def list_workloads(
      self,
      parent,
      limit=None,
      page_size=100,
  ):
    """List application workloads in the Projects/Location.

    Args:
      parent: str,
        projects/{projectId}/locations/{location}/applications/{application}
      limit: int or None, the total number of results to return. Default value
        is None
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results). Default value is 100.

    Returns:
      Generator of matching application workloads.
    """
    list_req = (
        self.messages.ApphubProjectsLocationsApplicationsWorkloadsListRequest(
            parent=parent
        )
    )
    return list_pager.YieldFromList(
        self._app_workloads_client,
        list_req,
        field='workloads',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize',
    )

  def list_services(
      self,
      parent,
      limit=None,
      page_size=100,
  ):
    """List application services in the Projects/Location.

    Args:
      parent: str,
        projects/{projectId}/locations/{location}/applications/{application}
      limit: int or None, the total number of results to return. Default value
        is None
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results). Default value is 100.

    Returns:
      Generator of matching application services.
    """
    list_req = (
        self.messages.ApphubProjectsLocationsApplicationsServicesListRequest(
            parent=parent
        )
    )
    return list_pager.YieldFromList(
        self._app_services_client,
        list_req,
        field='services',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize',
    )
