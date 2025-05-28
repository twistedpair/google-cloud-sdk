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

  def MakeInterconnectGroupsCreateMembersInterconnectInput(
      self,
      facility: str = None,
      description: str = None,
      name: str = None,
      link_type: str = None,
      requested_link_count: int = 1,
      interconnect_type: str = None,
      admin_enabled: bool = True,
      noc_contact_email: str = None,
      customer_name: str = None,
      remote_location: str = None,
      requested_features: str = None,
  ):
    """Make an InterconnectGroupsCreateMembersInterconnectInput."""
    return self._messages.InterconnectGroupsCreateMembersInterconnectInput(
        facility=facility,
        description=description,
        name=name,
        linkType=link_type,
        requestedLinkCount=requested_link_count,
        interconnectType=interconnect_type,
        adminEnabled=admin_enabled,
        nocContactEmail=noc_contact_email,
        customerName=customer_name,
        remoteLocation=remote_location,
        requestedFeatures=requested_features,
    )

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
      self, topology_capability, interconnects, update_mask, **kwargs
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
            updateMask=update_mask,
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

  def _MakeGetOperationalStatusRequestTuple(self):
    return (
        self._client.interconnectGroups,
        'GetOperationalStatus',
        self._messages.ComputeInterconnectGroupsGetOperationalStatusRequest(
            project=self.ref.project, interconnectGroup=self.ref.Name()
        ),
    )

  def _MakeCreateMembersRequestTuple(
      self,
      intent_mismatch_behavior,
      template_interconnect,
      member_interconnects,
  ):
    messages = self._messages
    return (
        self._client.interconnectGroups,
        'CreateMembers',
        messages.ComputeInterconnectGroupsCreateMembersRequest(
            project=self.ref.project,
            interconnectGroupsCreateMembersRequest=messages.InterconnectGroupsCreateMembersRequest(
                request=messages.InterconnectGroupsCreateMembers(
                    intentMismatchBehavior=intent_mismatch_behavior,
                    templateInterconnect=template_interconnect,
                    interconnects=member_interconnects,
                ),
            ),
            interconnectGroup=self.ref.Name(),
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
      update_mask='',
      only_generate_request=False,
      **kwargs
  ):
    """Patch description, topology capability and member interconnects of an interconnect group."""
    requests = [
        self._MakePatchRequestTuple(
            topology_capability, interconnects, update_mask, **kwargs
        )
    ]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests

  def GetOperationalStatus(self, only_generate_request=False):
    requests = [self._MakeGetOperationalStatusRequestTuple()]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests

  def CreateMembers(
      self,
      intent_mismatch_behavior=None,
      template_interconnect=None,
      member_interconnects=(),
  ):
    """Create member interconnects in an interconnect group."""
    requests = [
        self._MakeCreateMembersRequestTuple(
            intent_mismatch_behavior,
            template_interconnect,
            member_interconnects,
        )
    ]
    resources = self._compute_client.MakeRequests(requests)
    return resources[0]
