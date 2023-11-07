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
"""Apphub Discovered Workloads API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.apphub import utils as api_lib_utils


class DiscoveredWorkloadsClient(object):
  """Client for workloads in apphub API."""

  def __init__(self, client=None, messages=None):
    self.client = client or api_lib_utils.GetClientInstance()
    self.messages = messages or api_lib_utils.GetMessagesModule()
    self._dis_workloads_client = (
        self.client.projects_locations_discoveredWorkloads
    )

  def Describe(self, discovered_workload):
    """Describe a Discovered Workload in the Project/location.

    Args:
      discovered_workload: str, the name for the discovered workload being
        described.

    Returns:
      Described discovered workload Resource.
    """
    describe_req = (
        self.messages.ApphubProjectsLocationsDiscoveredWorkloadsGetRequest(
            name=discovered_workload
        )
    )
    return self._dis_workloads_client.Get(describe_req)

  def List(
      self,
      parent,
      limit=None,
      page_size=100,
  ):
    """List discovered workloads in the Projects/Location.

    Args:
      parent: str, projects/{projectId}/locations/{location}
      limit: int or None, the total number of results to return. Default value
        is None
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results). Default value is 100.

    Returns:
      Generator of matching discovered workloads.
    """
    list_req = (
        self.messages.ApphubProjectsLocationsDiscoveredWorkloadsListRequest(
            parent=parent
        )
    )
    return list_pager.YieldFromList(
        self._dis_workloads_client,
        list_req,
        field='discoveredWorkloads',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize',
    )

  def FindUnregistered(
      self,
      parent,
      limit=None,
      page_size=100,
  ):
    """List unregistered discovered workloads in the Projects/Location.

    Args:
      parent: str, projects/{projectId}/locations/{location}
      limit: int or None, the total number of results to return. Default value
        is None
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results). Default value is 100.

    Returns:
      Generator of matching discovered workloads.
    """
    find_unregistered_req = self.messages.ApphubProjectsLocationsDiscoveredWorkloadsFindUnregisteredRequest(
        parent=parent
    )
    return list_pager.YieldFromList(
        self._dis_workloads_client,
        find_unregistered_req,
        method='FindUnregistered',
        field='discoveredWorkloads',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize',
    )
