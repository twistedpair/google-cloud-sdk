# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Cloud Functions (2nd gen) API Client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.functions.v2 import util
from googlecloudsdk.core import properties


class FunctionsClient(object):
  """Client for Cloud Functions (2nd gen) API."""

  def __init__(self, release_track):
    self.client = util.GetClientInstance(release_track)
    self.messages = util.GetMessagesModule(release_track)

  def ListRegions(self):
    """Lists GCF gen2 regions.

    Returns:
      Iterable[cloudfunctions_v2alpha.Location], Generator of available GCF gen2
        regions.
    """
    project = properties.VALUES.core.project.GetOrFail()
    request = self.messages.CloudfunctionsProjectsLocationsListRequest(
        name='projects/' + project
    )
    return list_pager.YieldFromList(
        service=self.client.projects_locations,
        request=request,
        field='locations',
        batch_size_attribute='pageSize',
    )

  def ListRuntimes(self, region):
    """Lists available GCF Gen 2 Runtimes in a region.

    Args:
      region: str, The region targeted to list runtimes in.

    Returns:
      v2alpha|v2beta.ListRuntimesResponse, The list runtimes request
    """
    project = properties.VALUES.core.project.GetOrFail()

    # v2alpha|v2beta.CloudfunctionsProjectsLocationsRuntimesListRequest
    request = self.messages.CloudfunctionsProjectsLocationsRuntimesListRequest(
        parent='projects/{project}/locations/{region}'.format(
            project=project, region=region
        )
    )

    return self.client.projects_locations_runtimes.List(request)
