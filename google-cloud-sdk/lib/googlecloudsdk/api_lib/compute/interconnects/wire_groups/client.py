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
      compute_client=None,
      resources=None,
  ):
    self.ref = ref
    self.project = project
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
      cross_site_network,
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
      cross_site_network: cross site network to create the wiregroup under.
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
            crossSiteNetwork=cross_site_network,
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

  def Create(
      self,
      description='',
      cross_site_network=None,
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
            cross_site_network,
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
