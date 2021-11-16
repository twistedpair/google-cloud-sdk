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
"""Data Pipelines API utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import resources

_DEFAULT_API_VERSION = 'v1'


def GetMessagesModule(api_version=_DEFAULT_API_VERSION):
  return apis.GetMessagesModule('datapipelines', api_version)


def GetClientInstance(api_version=_DEFAULT_API_VERSION):
  return apis.GetClientInstance('datapipelines', api_version)


def GetPipelineURI(resource):
  pipeline = resources.REGISTRY.ParseRelativeName(
      resource.name, collection='datapipelines.pipelines')
  return pipeline.SelfLink()


class PipelinesClient(object):
  """Client for Pipelines for the Data Pipelines API."""

  def __init__(self, client=None, messages=None):
    self.client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule()
    self._service = self.client.projects_locations_pipelines

  def Describe(self, pipeline):
    """Describe a Pipeline in the given project and region.

    Args:
      pipeline: str, the name for the Pipeline being described.

    Returns:
      Described Pipeline Resource.
    """
    describe_req = self.messages.DatapipelinesProjectsLocationsPipelinesGetRequest(
        name=pipeline)
    return self._service.Get(describe_req)

  def Delete(self, pipeline):
    """Delete a Pipeline in the given project and region.

    Args:
      pipeline: str, the name for the Pipeline being described.

    Returns:
      Empty Response.
    """
    delete_req = self.messages.DatapipelinesProjectsLocationsPipelinesDeleteRequest(
        name=pipeline)
    return self._service.Delete(delete_req)

  def Stop(self, pipeline):
    """Stop a Pipeline in the given project and region.

    Args:
      pipeline: str, the name for the Pipeline being described.

    Returns:
      Pipeline resource.
    """
    stop_req = self.messages.DatapipelinesProjectsLocationsPipelinesStopRequest(
        name=pipeline)
    return self._service.Stop(stop_req)

  def Run(self, pipeline):
    """Run a Pipeline in the given project and region.

    Args:
      pipeline: str, the name for the Pipeline being described.

    Returns:
      Job resource which was created.
    """
    stop_req = self.messages.DatapipelinesProjectsLocationsPipelinesRunRequest(
        name=pipeline)
    return self._service.Run(stop_req)

  def List(self, limit=None, page_size=50, input_filter='', region=''):
    """List Pipelines for the given project and region.

    Args:
      limit: int or None, the total number of results to return.
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results).
      input_filter: string, optional filter to pass, eg:
        "type:BATCH,status:ALL", to filter out the pipelines based on staus or
        type.
      region: string, relative name to the region.

    Returns:
      Generator of matching devices.
    """
    list_req = self.messages.DatapipelinesProjectsLocationsListPipelinesRequest(
        filter=input_filter, parent=region)
    return list_pager.YieldFromList(
        self.client.projects_locations,
        list_req,
        field='pipelines',
        method='ListPipelines',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize')
