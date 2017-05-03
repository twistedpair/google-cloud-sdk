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
"""Interconnect."""

from googlecloudsdk.core.resource import resource_projector


class Interconnect(object):
  """Abstracts Interconnect resource."""

  def __init__(self, ref, compute_client=None):
    self.ref = ref
    self._compute_client = compute_client

  @property
  def _client(self):
    return self._compute_client.apitools_client

  def _MakeCreateRequestTuple(self, description, location, interconnect_type,
                              requested_link_count, link_type, admin_enabled,
                              noc_contact_email):
    return (self._client.interconnects, 'Insert',
            self._messages.ComputeInterconnectsInsertRequest(
                project=self.ref.project,
                interconnect=self._messages.Interconnect(
                    name=self.ref.Name(),
                    description=description,
                    interconnectType=interconnect_type,
                    linkType=link_type,
                    nocContactEmail=noc_contact_email,
                    requestedLinkCount=requested_link_count,
                    location=location,
                    adminEnabled=admin_enabled)))

  def _MakePatchRequestTuple(self, description, location, interconnect_type,
                             requested_link_count, link_type, admin_enabled,
                             noc_contact_email):
    return (self._client.interconnects, 'Patch',
            self._messages.ComputeInterconnectsPatchRequest(
                interconnect=self.ref.Name(),
                interconnectResource=self._messages.Interconnect(
                    name=None,
                    description=description,
                    interconnectType=interconnect_type,
                    linkType=link_type,
                    nocContactEmail=noc_contact_email,
                    requestedLinkCount=requested_link_count,
                    location=location,
                    adminEnabled=admin_enabled),
                project=self.ref.project))

  def _MakeDeleteRequestTuple(self):
    return (self._client.interconnects, 'Delete',
            self._messages.ComputeInterconnectsDeleteRequest(
                project=self.ref.project, interconnect=self.ref.Name()))

  def _MakeDescribeRequestTuple(self):
    return (self._client.interconnects, 'Get',
            self._messages.ComputeInterconnectsGetRequest(
                project=self.ref.project, interconnect=self.ref.Name()))

  @property
  def _messages(self):
    return self._compute_client.messages

  def Create(self,
             description='',
             location=None,
             interconnect_type=None,
             requested_link_count=None,
             link_type=None,
             admin_enabled=False,
             noc_contact_email=None,
             only_generate_request=False):
    """Create an interconnect."""
    requests = [
        self._MakeCreateRequestTuple(description, location, interconnect_type,
                                     requested_link_count, link_type,
                                     admin_enabled, noc_contact_email)
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
      return resource_projector.MakeSerializable(resources[0])
    return requests

  def Patch(self,
            description='',
            location=None,
            interconnect_type=None,
            requested_link_count=None,
            link_type=None,
            admin_enabled=False,
            noc_contact_email=None,
            only_generate_request=False):
    """Patch an interconnect."""
    requests = [
        self._MakePatchRequestTuple(description, location, interconnect_type,
                                    requested_link_count, link_type,
                                    admin_enabled, noc_contact_email)
    ]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests
