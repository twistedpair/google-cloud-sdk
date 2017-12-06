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
"""CLI Utilities for cloud tpu commands."""
from googlecloudsdk.api_lib.compute.tpus import tpu_utils as api_util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

TPU_NODE_COLLECTION = 'tpu.projects.locations.nodes'
TPU_LOCATION_COLLECTION = 'tpu.projects.locations'
TPU_OPERATION_COLLECTION = 'tpu.projects.locations.operations'
# Note: the URI segment which contains the zone is at position -3
LIST_FORMAT = """
     table(
            name.basename(),
            name.segment(-3):label=ZONE,
            acceleratorType.basename():label=ACCELERATOR_TYPE,
            format('{0}:{1}',ipAddress,port):label=NETWORK_ENDPOINT,
            network.basename():label=NETWORK,
            cidrBlock:label=RANGE,
            state:label=STATUS
         )
"""


class TpuOperationsPoller(waiter.CloudOperationPoller):
  """Poller for Cloud TPU operations API.

  This is necessary because the core operations library doesn't directly support
  simple_uri.
  """

  def __init__(self, client):
    self.client = client
    super(TpuOperationsPoller, self).__init__(
        self.client.client.projects_locations_operations,
        self.client.client.projects_locations_operations)

  def Poll(self, operation_ref):
    return self.client.GetOperation(operation_ref)

  def GetResult(self, operation):
    """Override."""
    return operation


def Describe(tpu_node, zone=None):
  """Invoke TPU Get API."""
  zone = zone or properties.VALUES.compute.zone.GetOrFail
  tpu_api_client = api_util.TpusClient('v1alpha1')
  node_ref = resources.REGISTRY.Parse(
      tpu_node,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
          'locationsId': zone},
      collection=TPU_NODE_COLLECTION)

  return tpu_api_client.Get(node_ref)


def Delete(tpu_node, zone=None):
  """Invoke TPU Delete API."""
  zone = zone or properties.VALUES.compute.zone.GetOrFail
  tpu_api_client = api_util.TpusClient('v1alpha1')
  node_ref = resources.REGISTRY.Parse(
      tpu_node,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
          'locationsId': zone},
      collection=TPU_NODE_COLLECTION)

  return WaitForOperation(tpu_api_client.Delete(node_ref), zone)


def Reset(tpu_node, zone):
  """Invoke TPU Reset API."""
  zone = zone or properties.VALUES.compute.zone.GetOrFail
  tpu_api_client = api_util.TpusClient('v1alpha1')
  node_ref = resources.REGISTRY.Parse(
      tpu_node,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
          'locationsId': zone},
      collection=TPU_NODE_COLLECTION)

  return WaitForOperation(tpu_api_client.Reset(node_ref), zone)


def List(page_size, limit, zone=None):
  """Invoke TPU List API."""
  zone = zone or properties.VALUES.compute.zone.GetOrFail()
  tpu_api_client = api_util.TpusClient('v1alpha1')
  location_ref = resources.REGISTRY.Parse(
      zone,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
          'locationsId': zone},
      collection=TPU_LOCATION_COLLECTION)

  return tpu_api_client.List(location_ref, page_size, limit)


def WaitForOperation(operation, zone):
  """Wait for the specified tpu operation."""
  wait_message = 'Waiting for [{0}] to finish'.format(operation.name)
  tpu_api_client = api_util.TpusClient('v1alpha1')
  poller = TpuOperationsPoller(tpu_api_client)
  operation_ref = resources.REGISTRY.Parse(
      operation.name,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
          'locationsId': zone},
      collection=TPU_OPERATION_COLLECTION)
  return waiter.WaitFor(poller, operation_ref, wait_message)


def Create(name,
           cidr_range,
           description=None,
           network='default',
           accelerator_type=None,
           version=None,
           zone=None):
  """Invoke TPU Create API and return created resource."""
  tpu_api_client = api_util.TpusClient('v1alpha1')
  zone = zone or properties.VALUES.compute.zone.GetOrFail()
  node_msg = tpu_api_client.messages.Node(cidrBlock=cidr_range,
                                          network=network,
                                          acceleratorType=accelerator_type,
                                          tensorflowVersion=version,
                                          description=description)

  parent_ref = resources.REGISTRY.Parse(
      zone,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail},
      collection=TPU_LOCATION_COLLECTION)
  return WaitForOperation(tpu_api_client.Create(node_msg, parent_ref, name),
                          zone)
