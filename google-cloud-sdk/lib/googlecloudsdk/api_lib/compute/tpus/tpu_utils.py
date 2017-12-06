# Copyright 2017 Google Inc. All Rights Reserved.
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
"""API Utilities for gcloud tpus commands."""
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis


def GetMessagesModule(version='v1alpha1'):
  return apis.GetMessagesModule('tpu', version)


def GetClientInstance(version='v1alpha1', no_http=False):
  return apis.GetClientInstance('tpu', version, no_http=no_http)


class TpusClient(object):
  """Client for TPU service in the Cloud TPU API."""

  def __init__(self, version='v1alpha1'):
    self.client = GetClientInstance(version)
    self.messages = self.client.MESSAGES_MODULE

  def Get(self, node_ref):
    return self.client.projects_locations_nodes.Get(
        self.messages.TpuProjectsLocationsNodesGetRequest(
            name=node_ref.RelativeName()))

  def Delete(self, node_ref):
    return self.client.projects_locations_nodes.Delete(
        self.messages.TpuProjectsLocationsNodesDeleteRequest(
            name=node_ref.RelativeName()))

  def Reset(self, node_ref):
    return self.client.projects_locations_nodes.Reset(
        self.messages.TpuProjectsLocationsNodesResetRequest(
            name=node_ref.RelativeName()))

  def List(self, location_ref, page_size, limit):
    return list_pager.YieldFromList(
        self.client.projects_locations_nodes,
        self.messages.TpuProjectsLocationsNodesListRequest(
            parent=location_ref.RelativeName()),
        field='nodes',
        limit=limit,
        batch_size=page_size,
        batch_size_attribute='pageSize')

  def GetOperation(self, operation_ref):
    return self.client.projects_locations_operations.Get(
        self.messages.TpuProjectsLocationsOperationsGetRequest(
            name=operation_ref.RelativeName()))

  def Create(self, node, parent_ref, name):
    return self.client.projects_locations_nodes.Create(
        self.messages.TpuProjectsLocationsNodesCreateRequest(
            node=node,
            nodeId=name,
            parent=parent_ref.RelativeName()))
