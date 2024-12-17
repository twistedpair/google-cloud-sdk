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

  def __init__(self, ref, compute_client=None, resources=None):
    self.ref = ref
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
      project,
      description,
  ):
    """Make a tuple for cross site network insert request.

    Args:
      project: project for the Cross Site Network resource.
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
            project=project,
            crossSiteNetwork=messages.CrossSiteNetwork(
                name=self.ref.Name(),
                description=description,
            ),
        ),
    )

  def Create(
      self,
      project,
      description=None,
      only_generate_request=False,
  ):
    """Create a cross site network."""
    requests = [
        self._MakeCreateRequestTuple(
            project,
            description,
        )
    ]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests
