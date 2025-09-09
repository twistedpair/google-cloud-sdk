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
"""DesignCenter SharedTemplates API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.design_center import utils as api_lib_utils
from googlecloudsdk.calliope import base


class SharedTemplatesClient(object):
  """Client for SharedTemplates in DesignCenter API."""

  def __init__(self, release_track=base.ReleaseTrack.ALPHA):
    self.client = api_lib_utils.GetClientInstance(release_track)
    self.messages = api_lib_utils.GetMessagesModule(release_track)
    self._st_client = self.client.projects_locations_spaces_sharedTemplates

  def List(self, parent, limit=None, page_size=100):
    """List all DesignCenter SharedTemplates under a space.

    Args:
      parent: str, the full resource name of the parent space. e.g.,
        projects/{p}/locations/{l}/spaces/{s}
      limit: int or None, the total number of results to return. Default value
        is None
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results). Default value is 100.

    Returns:
      A list of DesignCenter SharedTemplates that belong to the given parent.
    """
    list_req = (
        self.messages.DesigncenterProjectsLocationsSpacesSharedTemplatesListRequest(
            parent=parent
        )
    )
    return list_pager.YieldFromList(
        self._st_client,
        list_req,
        field='sharedTemplates',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize',
    )

  def Describe(self, name):
    """Describe a DesignCenter SharedTemplate under a space.

    Args:
      name: str, the full resource name of the SharedTemplate.
        e.g., projects/{p}/locations/{l}/spaces/{s}/sharedTemplates/{st}

    Returns:
      Described DesignCenter SharedTemplate resource.
    """
    describe_req = self.messages.DesigncenterProjectsLocationsSpacesSharedTemplatesGetRequest(
        name=name)
    return self._st_client.Get(describe_req)
