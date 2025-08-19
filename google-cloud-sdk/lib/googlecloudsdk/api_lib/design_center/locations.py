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
"""Designcenter Locations API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.design_center import utils as api_lib_utils
from googlecloudsdk.calliope import base


class LocationsClient(object):
  """Client for locations in Designcenter API."""

  def __init__(self, release_track=base.ReleaseTrack.ALPHA):
    self.client = api_lib_utils.GetClientInstance(release_track)
    self.messages = api_lib_utils.GetMessagesModule(release_track)
    self._lo_client = self.client.projects_locations

  def List(self, parent, limit=None, page_size=100):
    """List all Designcenter locations in the Project.

    Args:
      parent: str, the project in which the locations being listed.
        projects/{projectId}
      limit: int or None, the total number of results to return.
        Default value is None
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results). Default value is 100.

    Returns:
      A list of Designcenter locations that belong to the given parent.
    """
    list_req = self.messages.DesigncenterProjectsLocationsListRequest(
        name=parent)
    return list_pager.YieldFromList(
        self._lo_client,
        list_req,
        field='locations',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize',
    )

  def Describe(self, location):
    """Describe a Designcenter location.

    Args:
      location: str, the name for the Designcenter Location being described.

    Returns:
      Described Designcenter location resource.
    """
    describe_req = self.messages.DesigncenterProjectsLocationsGetRequest(
        name=location)
    return self._lo_client.Get(describe_req)
