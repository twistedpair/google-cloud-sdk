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
"""Wire Group."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class WireGroup(object):
  """Abstracts Wire Group resource."""

  def __init__(
      self,
      ref,
      project,
      cross_site_network,
      compute_client=None,
      resources=None,
  ):
    self.ref = ref
    self.project = project
    self.cross_site_network = cross_site_network
    self._compute_client = compute_client
    self._resources = resources

  @property
  def _client(self):
    return self._compute_client.apitools_client

  @property
  def _messages(self):
    return self._compute_client.messages

  def _MakeCreateRequestTuple(
      self,
      description,
      wire_group_type,
      bandwidth_unmetered,
      bandwidth_metered,
      fault_response,
      admin_enabled,
      network_service_class,
      bandwidth_allocation,
      validate_only,
  ):
    """Make a tuple for wire group insert request.

    Args:
      description: String that represents the description of the Cloud
        Wire Group resource.
      wire_group_type: type of the wire group.
      bandwidth_unmetered: amount of unmetered bandwidth for the wire group.
      bandwidth_metered: amount of metered bandwidth for the wire group.
      fault_response: fault response for the wire group.
      admin_enabled: set admin_enabled on the wire group.
      network_service_class: the network service class of the wire group.
      bandwidth_allocation: the bandwidth allocation for the wire group.
      validate_only: only validates the configuration, but doesn't create it.
    Returns:
    Insert wire group tuple that can be used in a request.
    """
    messages = self._messages
    return (
        self._client.wireGroups,
        'Insert',
        messages.ComputeWireGroupsInsertRequest(
            project=self.project,
            crossSiteNetwork=self.cross_site_network,
            wireGroup=messages.WireGroup(
                name=self.ref.Name(),
                description=description,
                wireGroupProperties=messages.WireGroupProperties(
                    type=messages.WireGroupProperties.TypeValueValuesEnum(
                        wire_group_type
                    ),
                ),
                wireProperties=messages.WireProperties(
                    bandwidthUnmetered=bandwidth_unmetered,
                    bandwidthMetered=bandwidth_metered,
                    networkServiceClass=messages.WireProperties.NetworkServiceClassValueValuesEnum(
                        network_service_class
                    ) if network_service_class else None,
                    bandwidthAllocation=messages.WireProperties.BandwidthAllocationValueValuesEnum(
                        bandwidth_allocation
                    ) if bandwidth_allocation else None,
                    faultResponse=messages.WireProperties.FaultResponseValueValuesEnum(
                        fault_response
                    ) if fault_response else None,
                ),
                adminEnabled=admin_enabled,
            ),
            validateOnly=validate_only,
        ),
    )

  def _MakePatchRequestTuple(
      self,
      description=None,
      wire_group_type=None,
      bandwidth_unmetered=None,
      bandwidth_metered=None,
      fault_response=None,
      admin_enabled=None,
      network_service_class=None,
      bandwidth_allocation=None,
      endpoints=None,
      validate_only=False,
      update_mask=None,
  ):
    """Make a tuple for wire group patch request."""
    messages = self._messages

    if update_mask is None:
      update_mask = []

    if description:
      update_mask.append('description')
    if wire_group_type:
      update_mask.append('wireGroupProperties.type')
    if bandwidth_unmetered:
      update_mask.append('wireProperties.bandwidthUnmetered')
    if bandwidth_metered:
      update_mask.append('wireProperties.bandwidthMetered')
    if network_service_class:
      update_mask.append('wireProperties.networkServiceClass')
    if bandwidth_allocation:
      update_mask.append('wireProperties.bandwidthAllocation')
    if fault_response:
      update_mask.append('wireProperties.faultResponse')
    if admin_enabled:
      update_mask.append('adminEnabled')
    if endpoints:
      update_mask.append('endpoints')

    return (
        self._client.wireGroups,
        'Patch',
        messages.ComputeWireGroupsPatchRequest(
            project=self.project,
            crossSiteNetwork=self.cross_site_network,
            wireGroup=self.ref.Name(),
            wireGroupResource=messages.WireGroup(
                description=description,
                wireGroupProperties=messages.WireGroupProperties(
                    type=messages.WireGroupProperties.TypeValueValuesEnum(
                        wire_group_type
                    ) if wire_group_type else None,
                ),
                wireProperties=messages.WireProperties(
                    bandwidthUnmetered=bandwidth_unmetered,
                    bandwidthMetered=bandwidth_metered,
                    networkServiceClass=messages.WireProperties.NetworkServiceClassValueValuesEnum(
                        network_service_class
                    ) if network_service_class else None,
                    bandwidthAllocation=messages.WireProperties.BandwidthAllocationValueValuesEnum(
                        bandwidth_allocation
                    ) if bandwidth_allocation else None,
                    faultResponse=messages.WireProperties.FaultResponseValueValuesEnum(
                        fault_response
                    ) if fault_response else None,
                ),
                adminEnabled=admin_enabled,
                endpoints=endpoints or None,
            ),
            validateOnly=validate_only if validate_only else None,
            updateMask=','.join(update_mask),
        ),
    )

  def _MakeDeleteRequestTuple(self):
    return (
        self._client.wireGroups,
        'Delete',
        self._messages.ComputeWireGroupsDeleteRequest(
            project=self.project,
            crossSiteNetwork=self.cross_site_network,
            wireGroup=self.ref.Name(),
        ),
    )

  def _MakeDescribeRequestTuple(self):
    return (
        self._client.wireGroups,
        'Get',
        self._messages.ComputeWireGroupsGetRequest(
            project=self.ref.project,
            crossSiteNetwork=self.cross_site_network,
            wireGroup=self.ref.Name(),
        ),
    )

  def Create(
      self,
      description='',
      wire_group_type=None,
      bandwidth_unmetered=None,
      bandwidth_metered=None,
      fault_response=None,
      admin_enabled=None,
      network_service_class=None,
      bandwidth_allocation=None,
      validate_only=False,
      only_generate_request=False,
  ):
    """Create a wire group."""
    requests = [
        self._MakeCreateRequestTuple(
            description,
            wire_group_type,
            bandwidth_unmetered,
            bandwidth_metered,
            fault_response,
            admin_enabled,
            network_service_class,
            bandwidth_allocation,
            validate_only
        )
    ]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests

  def Patch(self, only_generate_request=False, **kwargs):
    """Patch description of a wire group."""
    requests = [self._MakePatchRequestTuple(**kwargs)]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests

  def Delete(self, only_generate_request=False):
    requests = [self._MakeDeleteRequestTuple()]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests

  def Describe(self, only_generate_request=False):
    requests = [self._MakeDescribeRequestTuple()]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests
