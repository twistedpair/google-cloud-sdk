# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Utility file that contains helpers for the Cloud TPU Execution groups."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute.operations import poller
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.projects import util as p_util
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


class TPUNode(object):
  """Helper to create and modify TPU nodes."""

  def __init__(self, release_track):
    if release_track == base.ReleaseTrack.ALPHA:
      self._api_version = 'v1alpha1'
    elif release_track == base.ReleaseTrack.BETA:
      self._api_version = 'v1beta1'
    else:
      self._api_version = 'v1'
    self.client = apis.GetClientInstance('tpu', self._api_version)
    self.messages = apis.GetMessagesModule('tpu', self._api_version)

  def _CreateDefaultNode(self, accelerator_type, tf_version):
    node = self.messages.Node()
    node.acceleratorType = accelerator_type
    node.network = ''
    node.tensorflowVersion = tf_version
    return node

  def _GetTpuOperationRef(self, operation):
    """Get a resource reference to a long running operation."""
    return resources.REGISTRY.ParseRelativeName(
        operation.name, collection='tpu.projects.locations.operations')

  def Create(self, name, accelerator_type, tf_version, zone):
    """Create builds and issues a request to create a TPU node.

    Args:
      name: Name of the TPU Node to be created.
      accelerator_type: Slice type of TPU accelerator like 'v2-8', 'v2-32'.
      tf_version: Tensorflow Version like '1.1', '1.5'.
      zone: Zone to create the TPU Node in.
    Returns:
      A TPU Create response which needs to be polled on.
    """
    project = properties.VALUES.core.project.Get(required=True)
    request = self.messages.TpuProjectsLocationsNodesCreateRequest(
        parent='projects/{}/locations/{}'.format(project, zone),
        nodeId=name,
        node=self._CreateDefaultNode(accelerator_type, tf_version))
    operation = self.client.projects_locations_nodes.Create(request)
    return self._GetTpuOperationRef(operation)

  def WaitForOperation(self, operation_ref, message):
    operation_poller = waiter.CloudOperationPoller(
        self.client.projects_locations_nodes,
        self.client.projects_locations_operations)
    return waiter.WaitFor(operation_poller, operation_ref, message)


class Instance(object):
  """Helper to create the GCE VM required to work with the TPU Node."""

  def __init__(self, release_track):
    holder = base_classes.ComputeApiHolder(release_track)
    self.client = holder.client.apitools_client
    self.messages = holder.client.messages

  def _BuildInstanceSpec(
      self, name, zone, machine_type, disk_size, preemptible):
    """Builds an instance spec to be used for Instance creation."""

    disk = self.messages.AttachedDisk(
        boot=True,
        autoDelete=True,
        initializeParams=self.messages.AttachedDiskInitializeParams(
            sourceImage='projects/ml-images/global/images/debian-10-tf-nightly-v20200403',
            diskSizeGb=disk_size
        ))
    project_number = p_util.GetProjectNumber(
        properties.VALUES.core.project.Get(required=True))
    network_interface = self.messages.NetworkInterface(
        network='projects/{}/global/networks/default'.format(project_number),
        accessConfigs=[self.messages.AccessConfig(
            name='External NAT',
            type=self.messages.AccessConfig.TypeValueValuesEnum.ONE_TO_ONE_NAT)]
        )
    metadata = [self.messages.Metadata.ItemsValueListEntry(
        key='ctpu',
        value=name)]
    service_account = self.messages.ServiceAccount(
        email='default',
        scopes=[
            'https://www.googleapis.com/auth/devstorage.read_write',
            'https://www.googleapis.com/auth/logging.write',
            'https://www.googleapis.com/auth/monitoring.write',
            'https://www.googleapis.com/auth/cloud-platform'
        ])
    labels = self.messages.Instance.LabelsValue(additionalProperties=[
        self.messages.Instance.LabelsValue.AdditionalProperty(
            key='ctpu', value=name)
    ])

    return self.messages.Instance(
        name=name,
        metadata=self.messages.Metadata(items=metadata),
        machineType='zones/{}/machineTypes/{}'.format(zone, machine_type),
        disks=[disk],
        scheduling=self.messages.Scheduling(preemptible=preemptible),
        networkInterfaces=[network_interface],
        labels=labels,
        serviceAccounts=[service_account])

  def _GetComputeZoneOperationRef(self, operation):
    """Get a resource reference to a long running operation."""
    return resources.REGISTRY.Parse(
        operation.selfLink, collection='compute.zoneOperations')

  def Create(self, name, zone, machine_type, disk_size, preemptible):
    """Issue request to create an Instance."""
    request = self.messages.ComputeInstancesInsertRequest(
        project=properties.VALUES.core.project.Get(required=True),
        zone=zone,
        instance=self._BuildInstanceSpec(
            name, zone, machine_type, disk_size, preemptible))
    operation = self.client.instances.Insert(request)
    return self._GetComputeZoneOperationRef(operation)

  def WaitForOperation(self, operation_ref, message):
    """Wait for Instance operation to complete."""
    operation_poller = poller.Poller(self.client.instances)
    return waiter.WaitFor(operation_poller, operation_ref, message)

