# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Flags and helpers for the compute routes commands."""

from googlecloudsdk.command_lib.compute import flags as compute_flags

DEFAULT_LIST_FORMAT = """\
    table(
      name,
      network.basename(),
      destRange,
      firstof(
          nextHopInstance,
          nextHopGateway,
          nextHopIp,
          nextHopVpnTunnel,
          nextHopPeering).scope()
        :label=NEXT_HOP,
      priority
    )"""

NEXT_HOP_GATEWAY_ARG = compute_flags.ResourceArgument(
    name='--next-hop-gateway',
    resource_name='next hop gateway',
    completion_resource_id='compute.nextHopGateways',
    required=False,
    global_collection='compute.nextHopGateways',
    short_help=(
        'Specifies the gateway that should handle matching packets. '
        'Currently, the only acceptable value is '
        '`default-internet-gateway` which is a gateway operated by Google '
        'Compute Engine.'))


def RouteArgument(required=True, plural=False):
  return compute_flags.ResourceArgument(
      resource_name='route',
      completion_resource_id='compute.routes',
      plural=plural,
      required=required,
      global_collection='compute.routes')
