# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import socket
import threading

from googlecloudsdk.api_lib.compute import iap_tunnel_websocket
from googlecloudsdk.api_lib.compute import iap_tunnel_websocket_utils as utils
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import http_proxy
from googlecloudsdk.core import log
from googlecloudsdk.core.credentials import store


class UnableToOpenPortError(exceptions.Error):
  pass


def _CloseLocalConnectionCallback(local_conn):
  # For test WebSocket connections, there is not a local socket connection.
  if local_conn:
    try:
      local_conn.close()
    except EnvironmentError:
      pass


def _GetAccessTokenCallback(creds):
  if not creds:
    return None
  store.Refresh(creds)
  return creds.access_token


def _SendLocalDataCallback(local_conn, data):
  # For test WebSocket connections, there is not a local socket connection.
  if local_conn:
    local_conn.send(data)


class BaseIapTunnelHelper(object):
  """Base helper class for starting IAP tunnel."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--iap-tunnel-url-override',
        hidden=True,
        help=('Allows for overriding the connection endpoint for integration '
              'testing.'))
    parser.add_argument(
        '--iap-tunnel-insecure-disable-websocket-cert-check',
        default=False,
        action='store_true',
        hidden=True,
        help='Disables checking certificates on the WebSocket connection.')

  def __init__(self, args, project, zone, instance, interface, port, local_host,
               local_port):
    self._project = project
    self._zone = zone
    self._instance = instance
    self._interface = interface
    self._port = port
    self._local_host = local_host
    self._local_port = local_port
    self._iap_tunnel_url_override = args.iap_tunnel_url_override
    self._ignore_certs = args.iap_tunnel_insecure_disable_websocket_cert_check
    self._shutdown = False

  def _InitiateWebSocketConnection(self, local_conn, get_access_token_callback):
    tunnel_target = self._GetTunnelTargetInfo()
    new_websocket = iap_tunnel_websocket.IapTunnelWebSocket(
        tunnel_target, get_access_token_callback,
        functools.partial(_SendLocalDataCallback, local_conn),
        functools.partial(_CloseLocalConnectionCallback, local_conn),
        ignore_certs=self._ignore_certs)
    new_websocket.InitiateConnection()
    return new_websocket

  def _GetTunnelTargetInfo(self):
    proxy_info = http_proxy.GetHttpProxyInfo()
    if callable(proxy_info):
      proxy_info = proxy_info(method='https')
    return utils.IapTunnelTargetInfo(project=self._project,
                                     zone=self._zone,
                                     instance=self._instance,
                                     interface=self._interface,
                                     port=self._port,
                                     url_override=self._iap_tunnel_url_override,
                                     proxy_info=proxy_info)

  def _OpenLocalTcpSocket(self):
    """Attempt to open a local socket listening on specified host and port."""
    s = None
    for res in socket.getaddrinfo(
        self._local_host, self._local_port, socket.AF_UNSPEC,
        socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
      af, socktype, proto, unused_canonname, socket_address = res
      try:
        s = socket.socket(af, socktype, proto)
      except socket.error:
        s = None
        continue
      try:
        s.bind(socket_address)
        s.listen(1)
        break
      except EnvironmentError:
        try:
          s.close()
        except socket.error:
          pass
        s = None
        continue

    if s is None:
      raise UnableToOpenPortError('Unable to open socket on port [%d].' %
                                  self._local_port)

    log.Print('Listening on port [%d].' % self._local_port)
    return s

  def _RunReceiveLocalData(self, conn, socket_address):
    """Receive data from provided local connection and send over WebSocket."""
    websocket_conn = None
    try:
      websocket_conn = self._InitiateWebSocketConnection(
          conn,
          functools.partial(_GetAccessTokenCallback, store.LoadIfEnabled()))
      while not self._shutdown:
        data = conn.recv(utils.SUBPROTOCOL_MAX_DATA_FRAME_SIZE)
        if not data:
          break
        websocket_conn.Send(data)
    except EnvironmentError as e:
      log.info('Socket error [%s] while receiving from client.', str(e))
    except:  # pylint: disable=bare-except
      log.exception('Error while receiving from client.')
    finally:
      if self._shutdown:
        log.info('Terminating connection to [%r].', socket_address)
      else:
        log.info('Client closed connection from [%r].', socket_address)
      try:
        conn.close()
      except EnvironmentError:
        pass
      try:
        if websocket_conn:
          websocket_conn.Close()
      except (EnvironmentError, exceptions.Error):
        pass


class IapTunnelProxyServerHelper(BaseIapTunnelHelper):
  """Proxy server helper listens on a port for new local connections."""

  def StartProxyServer(self):
    """Start accepting connections."""
    self._TestConnection()
    self._server_socket = self._OpenLocalTcpSocket()

    self._connections = []
    try:
      with execution_utils.RaisesKeyboardInterrupt():
        while True:
          self._connections.append(self._AcceptNewConnection())
    except KeyboardInterrupt:
      log.info('Keyboard interrupt received.')
    finally:
      self._CloseServerSocket()

    self._shutdown = True
    self._CloseClientConnections()
    log.Print('Server shutdown complete.')

  def _TestConnection(self):
    log.Print('Testing if can connect.')
    websocket_conn = self._InitiateWebSocketConnection(
        None, functools.partial(_GetAccessTokenCallback, store.LoadIfEnabled()))
    websocket_conn.Close()

  def _AcceptNewConnection(self):
    """Accept a new socket connection and start a new WebSocket tunnel."""
    conn, socket_address = self._server_socket.accept()
    log.info('New connection from [%r]', socket_address)
    new_thread = threading.Thread(target=self._RunReceiveLocalData,
                                  args=(conn, socket_address))
    new_thread.daemon = True
    new_thread.start()
    return new_thread, conn

  def _CloseServerSocket(self):
    log.info('Stopping server.')
    try:
      self._server_socket.close()
    except EnvironmentError:
      pass

  def _CloseClientConnections(self):
    """Close client connections that seem to still be open."""
    if self._connections:
      close_count = 0
      for client_thread, conn in self._connections:
        if client_thread.isAlive():
          close_count += 1
          try:
            conn.close()
          except EnvironmentError:
            pass
      if close_count:
        log.Print('Closed [%d] local connection(s).' % close_count)
