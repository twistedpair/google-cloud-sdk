# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Tunnel TCP traffic over Cloud IAP WebSocket connection."""

from googlecloudsdk.api_lib.compute import iap_tunnel_websocket_utils
from googlecloudsdk.command_lib.compute import iap_tunnel
from googlecloudsdk.core import http_proxy

# This has no effect for Cloud Run targets, but is a required parameter for
# IAP-TCP.
DEFAULT_PORT = 22


class CloudRunIAPWebsocketTunnelHelper(iap_tunnel.IAPWebsocketTunnelHelper):
  """Helper for starting a Cloud Run IAP WebSocket tunnel."""

  def __init__(self, args):
    args.iap_tunnel_url_override = None
    args.iap_tunnel_insecure_disable_websocket_cert_check = None
    self._cloud_run_args = iap_tunnel_websocket_utils.CloudRunArgs(
        project_number=args.project_number,
        workload_type=args.workload_type,
        deployment_name=args.deployment_name,
        instance_id=getattr(args, 'instance', None),
        container_id=getattr(args, 'container', None),
    )
    self._ignore_certs = False
    super(CloudRunIAPWebsocketTunnelHelper, self).__init__(
        args,
        project=args.project_id,
        zone=None,
        instance=None,
        interface=None,
        port=DEFAULT_PORT,
        region=args.region,
        network=None,
        host=None,
        dest_group=None,
    )

  def _GetTunnelTargetInfo(self):
    """Overrides the parent method to build a target for Cloud Run."""
    proxy_info = http_proxy.GetHttpProxyInfo()
    if callable(proxy_info):
      proxy_info = proxy_info(method='https')
    return iap_tunnel_websocket_utils.IapTunnelTargetInfo(
        cloud_run_args=self._cloud_run_args,
        project=self._project,
        region=self._region,
        port=self._port,
        url_override=self._iap_tunnel_url_override,
        proxy_info=proxy_info,
        zone=self._zone,
        instance=self._instance,
        interface=self._interface,
        network=self._network,
        host=self._host,
        dest_group=self._dest_group,
    )
