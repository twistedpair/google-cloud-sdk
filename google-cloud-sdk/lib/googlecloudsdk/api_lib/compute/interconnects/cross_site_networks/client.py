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
"""Cross Site Network."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class CrossSiteNetwork(object):
  """Abstracts Cross Site Network resource."""

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

  def _MakeCreateRequestTuple(
      self,
      description,
  ):
    """Make a tuple for cross site network insert request.

    Args:
      description: String that represents the description of the Cloud
        Cross Site Network resource.
    Returns:
    Insert cross site network tuple that can be used in a request.
    """
    messages = self._messages
    return (
        self._client.crossSiteNetworks,
        'Insert',
        messages.ComputeCrossSiteNetworksInsertRequest(
            project=self.project,
            crossSiteNetwork=messages.CrossSiteNetwork(
                name=self.ref.Name(),
                description=description,
            ),
        ),
    )

  def _MakePatchRequestTuple(self, **kwargs):
    """Make a tuple for cross site network patch request."""
    messages = self._messages
    return (
        self._client.crossSiteNetworks,
        'Patch',
        messages.ComputeCrossSiteNetworksPatchRequest(
            project=self.project,
            crossSiteNetwork=self.ref.Name(),
            crossSiteNetworkResource=messages.CrossSiteNetwork(
                **kwargs
            ),
        ),
    )

  def _MakeDeleteRequestTuple(self):
    return (
        self._client.crossSiteNetworks,
        'Delete',
        self._messages.ComputeCrossSiteNetworksDeleteRequest(
            project=self.project, crossSiteNetwork=self.ref.Name(),
        ),
    )

  def _MakeDescribeRequestTuple(self):
    """Make a tuple for cross site network describe request.

    Returns:
    Describe cross site network tuple that can be used in a request.
    """
    return (
        self._client.crossSiteNetworks,
        'Get',
        self._messages.ComputeCrossSiteNetworksGetRequest(
            project=self.ref.project, crossSiteNetwork=self.ref.Name()
        ),
    )

  def Create(
      self,
      description=None,
      only_generate_request=False,
  ):
    """Create a cross site network."""
    requests = [
        self._MakeCreateRequestTuple(
            description,
        )
    ]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests

  def Patch(self, only_generate_request=False, **kwargs):
    """Patch description of a cross site network."""
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
    """Describe a cross site network.

    Args:
      only_generate_request: only generate request, do not execute it.

    Returns:
    Describe cross site network tuple that can be used in a request.
    """
    requests = [self._MakeDescribeRequestTuple()]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests
