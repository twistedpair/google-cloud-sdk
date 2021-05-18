# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""CLI Utilities for Cloud TPU VM commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import sys

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import files

import six


class IPAddresses():
  """Worker is a holder for the worker IP addresses."""

  def __init__(self, ip_address, internal_address):
    self.ip_address = ip_address
    self.internal_address = internal_address


def ParseWorkerFlag(worker_flag, network_endpoints, use_internal_ips):
  """Parses the --worker flag into a dict of worker indexes to IP addresses."""
  n_vms = len(network_endpoints)
  if six.text_type(worker_flag).upper() == 'ALL':
    indexes = list(range(n_vms))
  else:
    indexes = set()
    ranges = worker_flag.split(',')
    for r in ranges:
      if not r:
        continue
      if '-' in r:
        bounds = r.split('-')
        if len(bounds) != 2 or not bounds[0] or not bounds[1]:
          raise exceptions.InvalidArgumentException(
              '--worker', 'found malformed range "{}".'.format(r))
        start, end = int(bounds[0]), int(bounds[1])
        if start >= end:
          raise exceptions.InvalidArgumentException(
              '--worker', 'found malformed range "{}".'.format(r))
        indexes.update(range(start, end + 1))
      else:
        try:
          indexes.add(int(r))
        except ValueError:
          raise exceptions.InvalidArgumentException(
              '--worker', 'unable to parse worker ID {}. Please only use'
              'numbers.'.format(r))

  if not indexes:
    raise exceptions.InvalidArgumentException(
        '--worker', 'no worker specified, or none were parsed from the '
        'argument value.')

  mx = max(indexes)
  if mx >= n_vms:
    raise exceptions.InvalidArgumentException(
        '--worker', 'worker index {} is larger than the valid worker indexes '
        'on this TPU VM. Please only use indexes in the range [0, {}], '
        'inclusive.'.format(mx, n_vms-1))

  # Get the VMs' IP addresses.
  worker_ips = {}
  for worker in indexes:
    internal_address = network_endpoints[worker].ipAddress
    if (not use_internal_ips and network_endpoints[worker].accessConfig
        and network_endpoints[worker].accessConfig.externalIp):
      ip_address = network_endpoints[worker].accessConfig.externalIp
    else:
      ip_address = internal_address
    worker_ips[worker] = IPAddresses(ip_address, internal_address)
  return worker_ips


def InvertBoolean(boolean):
  """Inverts the boolean value passed in."""
  return not boolean


def ReadMetadataFromFile(metadata_from_file):
  """Reads the metadata values from the files.

  Args:
    metadata_from_file: dict of metadata keys to filenames.

  Returns:
    A dict of metadata keys to values.
  """
  metadata = {}
  for key, file_path in six.iteritems(metadata_from_file):
    metadata[key] = files.ReadFileContents(file_path)
  return metadata


def GetMessagesModule(version='v2alpha1'):
  return apis.GetMessagesModule('tpu', version)


def StartRequestHook(ref, args, request):
  """Declarative request hook for TPU Start command."""
  del ref
  del args
  start_request = GetMessagesModule().StartNodeRequest()
  request.startNodeRequest = start_request
  return request


def StopRequestHook(ref, args, request):
  """Declarative request hook for TPU Stop command."""
  del ref
  del args
  stop_request = GetMessagesModule().StopNodeRequest()
  request.stopNodeRequest = stop_request
  return request


def IsTPUVMNode(node):
  api_version = six.text_type(node.apiVersion).upper()
  return (not api_version.startswith('V1')
          and api_version != 'API_VERSION_UNSPECIFIED')


def FilterTPUVMNodes(response, args):
  """Removes Cloud TPU V1 API nodes from the 'list' output.

  Used with 'compute tpus tpu-vm list'.

  Args:
    response: response to ListNodes.
    args: the arguments for the list command.

  Returns:
    A response with only TPU VM (non-V1 API) nodes.
  """
  del args
  return list(six.moves.filter(IsTPUVMNode, response))


def CheckTPUVMNode(response, args):
  """Verifies that the node is a TPU VM node.

  If it is not a TPU VM node, exit with an error instead.

  Args:
    response: response to GetNode.
    args: the arguments for the list command.

  Returns:
    The response to GetNode if the node is TPU VM.
  """
  del args
  if IsTPUVMNode(response):
    return response
  log.err.Print('ERROR: Please use "gcloud compute tpus describe" for Cloud TPU'
                ' nodes that are not TPU VM.')
  sys.exit(1)


class TPUNode(object):
  """Helper to create and modify TPU nodes."""

  def __init__(self):
    self._api_version = 'v2alpha1'
    self.client = apis.GetClientInstance('tpu', self._api_version)
    self.messages = apis.GetMessagesModule('tpu', self._api_version)

  def GetMessages(self):
    return self.messages

  def Get(self, name, zone):
    """Retrieves the TPU node in the given zone."""
    project = properties.VALUES.core.project.Get(required=True)
    fully_qualified_node_name_ref = resources.REGISTRY.Parse(
        name,
        params={
            'locationsId': zone,
            'projectsId': project
        },
        collection='tpu.projects.locations.nodes',
        )
    request = self.messages.TpuProjectsLocationsNodesGetRequest(
        name=fully_qualified_node_name_ref.RelativeName())
    return self.client.projects_locations_nodes.Get(request)

  def GetGuestAttributes(self, name, zone):
    """Retrives the Guest Attributes for the nodes."""
    project = properties.VALUES.core.project.Get(required=True)
    fully_qualified_node_name_ref = resources.REGISTRY.Parse(
        name,
        params={
            'locationsId': zone,
            'projectsId': project
        },
        collection='tpu.projects.locations.nodes',
        )
    request = self.messages.TpuProjectsLocationsNodesGetGuestAttributesRequest(
        name=fully_qualified_node_name_ref.RelativeName())
    return self.client.projects_locations_nodes.GetGuestAttributes(request)

  def UpdateNode(self, name, zone, node, update_mask):
    """Updates the TPU node in the given zone."""
    project = properties.VALUES.core.project.Get(required=True)
    fully_qualified_node_name_ref = resources.REGISTRY.Parse(
        name,
        params={
            'locationsId': zone,
            'projectsId': project
        },
        collection='tpu.projects.locations.nodes',
        )
    request = self.messages.TpuProjectsLocationsNodesPatchRequest(
        name=fully_qualified_node_name_ref.RelativeName(),
        node=node,
        updateMask=update_mask)
    return self.client.projects_locations_nodes.Patch(request)

  def UpdateMetadataKey(self, metadata, key, value):
    """Updates a key in the TPU metadata object.

    If the key does not exist, it is added.

    Args:
      metadata: tpu.messages.Node.MetadataValue, the TPU's metadata.
      key: str, the key to be updated.
      value: str, the new value for the key.

    Returns:
      The updated metadata.
    """
    # If the metadata is empty, return a new metadata object with just the key.
    if metadata is None or metadata.additionalProperties is None:
      return self.messages.Node.MetadataValue(
          additionalProperties=[
              self.messages.Node.MetadataValue.AdditionalProperty(
                  key=key, value=value)])

    item = None
    for x in metadata.additionalProperties:
      if x.key == key:
        item = x
        break
    if item is not None:
      item.value = value
    else:
      # The key is not in the metadata, so append it.
      metadata.additionalProperties.append(
          self.messages.Node.MetadataValue.AdditionalProperty(
              key=key, value=value))
    return metadata
