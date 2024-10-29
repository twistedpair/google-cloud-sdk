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
"""Interconnect Group."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class InterconnectGroup(object):
  """Abstracts Interconnect Group resource."""

  def __init__(self, ref, project, compute_client=None, resources=None):
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

  def _MakeAdditionalProperties(self, interconnects):
    return [
        self._messages.InterconnectGroup.InterconnectsValue.AdditionalProperty(
            # The keys are arbitrary strings that only need to
            # be unique, and we use the Interconnect name.
            key=interconnect,
            value=self._messages.InterconnectGroupInterconnect(
                interconnect=self._resources.Create(
                    'compute.interconnects',
                    interconnect=interconnect,
                    project=self.ref.project,
                ).SelfLink()
            ),
        )
        for interconnect in interconnects
    ]

  def _MakeCreateRequestTuple(
      self,
      description,
      topology_capability,
      interconnects,
  ):
    """Make a tuple for interconnect group insert request.

    Args:
      description: String that represents the description of the Cloud
        Interconnect Group resource.
      topology_capability: String that represents the topology capability of the
        Cloud Interconnect Group resource.
      interconnects: List of strings that represent the names of the Cloud
        Interconnect resources that are members of the Cloud Interconnect Group
        resource.

    Returns:
    Insert interconnect group tuple that can be used in a request.
    """
    messages = self._messages
    return (
        self._client.interconnectGroups,
        'Insert',
        messages.ComputeInterconnectGroupsInsertRequest(
            project=self.project,
            interconnectGroup=messages.InterconnectGroup(
                intent=messages.InterconnectGroupIntent(
                    topologyCapability=topology_capability
                ),
                name=self.ref.Name(),
                description=description,
                interconnects=messages.InterconnectGroup.InterconnectsValue(
                    additionalProperties=self._MakeAdditionalProperties(
                        interconnects
                    )
                ),
            ),
        ),
    )

  def _MakePatchRequestTuple(
      self, topology_capability, interconnects, **kwargs
  ):
    """Make a tuple for interconnect group patch request."""
    messages = self._messages
    group_params = {
        'interconnects': messages.InterconnectGroup.InterconnectsValue(
            additionalProperties=self._MakeAdditionalProperties(interconnects)
        ),
    }
    group_params.update(kwargs)
    if topology_capability is not None:
      group_params['intent'] = messages.InterconnectGroupIntent(
          topologyCapability=topology_capability
      )
    return (
        self._client.interconnectGroups,
        'Patch',
        messages.ComputeInterconnectGroupsPatchRequest(
            project=self.project,
            interconnectGroup=self.ref.Name(),
            interconnectGroupResource=messages.InterconnectGroup(
                **group_params
            ),
        ),
    )

  def _MakeDeleteRequestTuple(self):
    return (
        self._client.interconnectGroups,
        'Delete',
        self._messages.ComputeInterconnectGroupsDeleteRequest(
            project=self.ref.project, interconnectGroup=self.ref.Name()
        ),
    )

  def _MakeDescribeRequestTuple(self):
    return (
        self._client.interconnectGroups,
        'Get',
        self._messages.ComputeInterconnectGroupsGetRequest(
            project=self.ref.project, interconnectGroup=self.ref.Name()
        ),
    )

  def Create(
      self,
      description=None,
      topology_capability=None,
      interconnects=(),
      only_generate_request=False,
  ):
    """Create an interconnect group."""
    requests = [
        self._MakeCreateRequestTuple(
            description,
            topology_capability,
            interconnects,
        )
    ]
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

  def Patch(
      self,
      topology_capability=None,
      interconnects=(),
      only_generate_request=False,
      **kwargs
  ):
    """Patch description, topology capability and member interconnects of an interconnect group."""
    requests = [
        self._MakePatchRequestTuple(
            topology_capability, interconnects, **kwargs
        )
    ]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests
