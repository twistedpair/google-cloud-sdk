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
"""Interconnect Attachment."""


class InterconnectAttachment(object):
  """Abstracts Interconnect attachment resource."""

  def __init__(self, ref, compute_client=None):
    self.ref = ref
    self._compute_client = compute_client

  @property
  def _client(self):
    return self._compute_client.apitools_client

  @property
  def _messages(self):
    return self._compute_client.messages

  def _MakeCreateRequestTuple(self, description, interconnect, router):
    return (self._client.interconnectAttachments, 'Insert',
            self._messages.ComputeInterconnectAttachmentsInsertRequest(
                project=self.ref.project,
                region=self.ref.region,
                interconnectAttachment=self._messages.InterconnectAttachment(
                    name=self.ref.Name(),
                    description=description,
                    interconnect=interconnect.SelfLink(),
                    router=router.SelfLink())))

  def _MakeDescribeRequestTuple(self):
    return (self._client.interconnectAttachments, 'Get',
            self._messages.ComputeInterconnectAttachmentsGetRequest(
                project=self.ref.project,
                region=self.ref.region,
                interconnectAttachment=self.ref.Name()))

  def _MakeDeleteRequestTuple(self):
    return (self._client.interconnectAttachments, 'Delete',
            self._messages.ComputeInterconnectAttachmentsDeleteRequest(
                project=self.ref.project,
                region=self.ref.region,
                interconnectAttachment=self.ref.Name()))

  def Create(self,
             description='',
             interconnect=None,
             router=None,
             only_generate_request=False):
    """create an interconnectAttachment."""
    requests = [self._MakeCreateRequestTuple(description, interconnect, router)]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests

  def Describe(self, only_generate_request=False):
    requests = [self._MakeDescribeRequestTuple()]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests

  def Delete(self, only_generate_request=False):
    requests = [self._MakeDeleteRequestTuple()]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests
