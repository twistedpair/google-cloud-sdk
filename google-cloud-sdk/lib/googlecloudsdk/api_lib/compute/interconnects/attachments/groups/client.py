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
"""Interconnect Attachment Group."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class InterconnectAttachmentGroup(object):
  """Abstracts Interconnect Attachment Group resource."""

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

  def _MakeAdditionalProperties(self, attachments):
    return [
        self._messages.InterconnectAttachmentGroup.AttachmentsValue.AdditionalProperty(
            # The keys are arbitrary strings that only need to
            # be unique, and we use region/attachment name.
            key=f'{region}/{attachment}',
            value=self._messages.InterconnectAttachmentGroupAttachment(
                attachment=self._resources.Create(
                    'compute.interconnectAttachments',
                    interconnectAttachment=attachment,
                    project=self.ref.project,
                    region=region,
                ).SelfLink()
            ),
        )
        for region, attachment in attachments
    ]

  def _MakeCreateRequestTuple(
      self,
      description,
      availability_sla,
      attachments,
  ):
    """Make a tuple for interconnect attachment group insert request.

    Args:
      description: String that represents the description of the Cloud
        Interconnect Attachment Group resource.
      availability_sla: String that represents the availability SLA of the Cloud
        Interconnect Attachment Group resource.
      attachments: List of strings that represent the names of the Cloud
        Interconnect Attachment resources that are members of the Cloud
        Interconnect Attachment Group resource.

    Returns:
    Insert interconnect attachment group tuple that can be used in a request.
    """
    messages = self._messages
    return (
        self._client.interconnectAttachmentGroups,
        'Insert',
        messages.ComputeInterconnectAttachmentGroupsInsertRequest(
            project=self.project,
            interconnectAttachmentGroup=messages.InterconnectAttachmentGroup(
                intent=messages.InterconnectAttachmentGroupIntent(
                    availabilitySla=availability_sla
                ),
                name=self.ref.Name(),
                description=description,
                attachments=messages.InterconnectAttachmentGroup.AttachmentsValue(
                    additionalProperties=self._MakeAdditionalProperties(
                        attachments
                    )
                ),
            ),
        ),
    )

  def _MakePatchRequestTuple(self, description, availability_sla, attachments):
    """Make a tuple for interconnect attachment group patch request."""
    messages = self._messages
    group_params = {
        'attachments': messages.InterconnectAttachmentGroup.AttachmentsValue(
            additionalProperties=self._MakeAdditionalProperties(attachments)
        ),
    }
    if description is not None:
      group_params['description'] = description
    if availability_sla is not None:
      group_params['intent'] = messages.InterconnectAttachmentGroupIntent(
          availabilitySla=availability_sla
      )
    return (
        self._client.interconnectAttachmentGroups,
        'Patch',
        messages.ComputeInterconnectAttachmentGroupsPatchRequest(
            project=self.project,
            interconnectAttachmentGroup=self.ref.Name(),
            interconnectAttachmentGroupResource=messages.InterconnectAttachmentGroup(
                **group_params
            ),
        ),
    )

  def _MakeDeleteRequestTuple(self):
    return (
        self._client.interconnectAttachmentGroups,
        'Delete',
        self._messages.ComputeInterconnectAttachmentGroupsDeleteRequest(
            project=self.ref.project,
            interconnectAttachmentGroup=self.ref.Name(),
        ),
    )

  def _MakeDescribeRequestTuple(self):
    return (
        self._client.interconnectAttachmentGroups,
        'Get',
        self._messages.ComputeInterconnectAttachmentGroupsGetRequest(
            project=self.ref.project,
            interconnectAttachmentGroup=self.ref.Name(),
        ),
    )

  def _MakeGetOperationalStatusRequestTuple(self):
    return (
        self._client.interconnectAttachmentGroups,
        'GetOperationalStatus',
        self._messages.ComputeInterconnectAttachmentGroupsGetOperationalStatusRequest(
            project=self.ref.project,
            interconnectAttachmentGroup=self.ref.Name(),
        ),
    )

  def Create(
      self,
      description=None,
      availability_sla=None,
      attachments=(),
      only_generate_request=False,
  ):
    """Create an interconnect attachment group."""
    requests = [
        self._MakeCreateRequestTuple(
            description,
            availability_sla,
            attachments,
        )
    ]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests

  def Patch(
      self,
      description=None,
      availability_sla=None,
      attachments=(),
      only_generate_request=False,
  ):
    """Patch an interconnect attachment group."""
    requests = [
        self._MakePatchRequestTuple(description, availability_sla, attachments)
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

  def GetOperationalStatus(self, only_generate_request=False):
    requests = [self._MakeGetOperationalStatusRequestTuple()]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests
