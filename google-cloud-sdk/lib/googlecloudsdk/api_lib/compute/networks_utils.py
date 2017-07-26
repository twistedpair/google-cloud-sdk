# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Code that's shared between multiple networks subcommands."""


def GetSubnetMode(network):
  """Returns the subnet mode of the input network."""
  if getattr(network, 'IPv4Range', None) is not None:
    return 'LEGACY'
  elif getattr(network, 'autoCreateSubnetworks', False):
    return 'AUTO'
  else:
    return 'CUSTOM'


def GetBgpRoutingMode(network):
  """Returns the BGP routing mode of the input network."""
  if getattr(network, 'routingConfig', None) is not None:
    return network.routingConfig.routingMode
  else:
    return None


def _GetNetworkMode(network):
  """Takes a network resource and returns the "mode" of the network."""
  if network.get('IPv4Range', None) is not None:
    return 'legacy'
  if network.get('autoCreateSubnetworks', False):
    return 'auto'
  else:
    return 'custom'


def AddMode(items):
  for resource in items:
    resource['x_gcloud_mode'] = _GetNetworkMode(resource)
    yield resource


def CreateNetworkResourceFromArgs(messages, network_ref, network_args):
  """Creates a new network resource from flag arguments."""

  network = messages.Network(
      name=network_ref.Name(),
      description=network_args.description)

  if network_args.subnet_mode == 'LEGACY':
    network.IPv4Range = network_args.range
  else:
    network.autoCreateSubnetworks = (network_args.subnet_mode == 'AUTO')

  if network_args.bgp_routing_mode:
    network.routingConfig = messages.NetworkRoutingConfig()
    network.routingConfig.routingMode = (messages.NetworkRoutingConfig.
                                         RoutingModeValueValuesEnum(
                                             network_args.bgp_routing_mode))

  return network
