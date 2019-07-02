# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Packet mirroring."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class PacketMirroring(object):
  """Abstracts PacketMirroring resource."""

  def __init__(self, ref, compute_client=None):
    self.ref = ref
    self._compute_client = compute_client

  @property
  def _client(self):
    return self._compute_client.apitools_client

  @property
  def _messages(self):
    return self._compute_client.messages

  def _MakeCreateRequestTuple(self, packet_mirroring):
    return (self._client.packetMirrorings, 'Insert',
            self._messages.ComputePacketMirroringsInsertRequest(
                project=self.ref.project,
                region=self.ref.region,
                packetMirroring=packet_mirroring))

  def Create(self, packet_mirroring=None, only_generate_request=False):
    requests = [self._MakeCreateRequestTuple(packet_mirroring)]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests

  def MakeDeleteRequestTuple(self):
    return (self._client.packetMirrorings, 'Delete',
            self._messages.ComputePacketMirroringsDeleteRequest(
                region=self.ref.region,
                project=self.ref.project,
                packetMirroring=self.ref.Name()))

  def Delete(self, only_generate_request=False):
    requests = [self.MakeDeleteRequestTuple()]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests

  def _MakeDescribeRequestTuple(self):
    return (self._client.packetMirrorings, 'Get',
            self._messages.ComputePacketMirroringsGetRequest(
                region=self.ref.region,
                project=self.ref.project,
                packetMirroring=self.ref.Name()))

  def Describe(self, only_generate_request=False):
    requests = [self._MakeDescribeRequestTuple()]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests
