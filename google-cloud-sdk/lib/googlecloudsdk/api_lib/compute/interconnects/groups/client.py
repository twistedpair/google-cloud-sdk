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

  def __init__(self, ref, project, compute_client=None):
    self.ref = ref
    self.project = project
    self._compute_client = compute_client

  @property
  def _client(self):
    return self._compute_client.apitools_client

  @property
  def _messages(self):
    return self._compute_client.messages

  def _MakeCreateRequestTuple(
      self,
      description,
      topology_capability,
  ):
    """Make a tuple for interconnect group insert request.

    Args:
      description: String that represents the description of the Cloud
        Interconnect Group resource.
      topology_capability: String that represents the topology capability of the
        Cloud Interconnect Group resource.

    Returns:
    Insert interconnect group tuple that can be used in a request.
    """
    return (
        self._client.interconnectGroups,
        'Insert',
        self._messages.ComputeInterconnectGroupsInsertRequest(
            project=self.project,
            interconnectGroup=self._messages.InterconnectGroup(
                intent=self._messages.InterconnectGroupIntent(
                    topologyCapability=topology_capability
                ),
                name=self.ref.Name(),
                description=description,
            ),
        ),
    )

  def _MakePatchRequestTuple(
      self,
      description,
      topology_capability,
  ):
    """Make a tuple for interconnect group patch request."""
    return (
        self._client.interconnectGroups,
        'Patch',
        self._messages.ComputeInterconnectGroupsPatchRequest(
            project=self.project,
            interconnectGroup=self.ref.Name(),
            interconnectGroupResource=self._messages.InterconnectGroup(
                name=self.ref.Name(),
                description=description,
                intent=self._messages.InterconnectGroupIntent(
                    topologyCapability=topology_capability
                ),
            ),
        ),
    )

  def Create(
      self,
      description='',
      topology_capability='',
      only_generate_request=False,
  ):
    """Create an interconnect group."""
    requests = [
        self._MakeCreateRequestTuple(
            description,
            topology_capability,
        )
    ]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests

  def Patch(
      self,
      description='',
      topology_capability=None,
      only_generate_request=False,
  ):
    """Patch description and topology capability of an interconnect group."""
    requests = [self._MakePatchRequestTuple(description, topology_capability)]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests
