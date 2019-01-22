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
import select
import socket
import threading

from googlecloudsdk.api_lib.compute import iap_tunnel_websocket
from googlecloudsdk.api_lib.compute import iap_tunnel_websocket_utils as utils
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import http_proxy
from googlecloudsdk.core import log
from googlecloudsdk.core.credentials import store
import portpicker


class LocalPortUnavailableError(exceptions.Error):
  pass


class UnableToOpenPortError(exceptions.Error):
  pass


def _AddBaseArgs(parser):
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


def AddConnectionHelperArgs(parser, tunnel_through_iap_scope):
  _AddBaseArgs(parser)
  tunnel_through_iap_scope.add_argument(
      '--tunnel-through-iap',
      action='store_true',
      help="""\
      Tunnel the ssh connection through the Cloud Identity-Aware Proxy.
      """)


def AddProxyServerHelperArgs(parser):
  _AddBaseArgs(parser)


def DetermineLocalPort(port_arg=0):
  if not port_arg:
    port_arg = portpicker.pick_unused_port()
  if not portpicker.is_port_free(port_arg):
    raise LocalPortUnavailableError('Local port [%d] is not available.' %
                                    port_arg)
  return port_arg


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


class _BaseIapTunnelHelper(object):
  """Base helper class for starting IAP tunnel."""

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
    self._socket_address = None

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
      af, socktype, proto, unused_canonname, self._socket_address = res
      try:
        s = socket.socket(af, socktype, proto)
      except socket.error:
        s = None
        continue
      try:
        s.bind(self._socket_address)
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


class IapTunnelProxyServerHelper(_BaseIapTunnelHelper):
  """Proxy server helper listens on a port for new local connections."""

  def __init__(self, args, project, zone, instance, interface, port, local_host,
               local_port):
    super(IapTunnelProxyServerHelper, self).__init__(
        args, project, zone, instance, interface, port, local_host, local_port)
    self._server_socket = None
    self._connections = []

  def __del__(self):
    self._CloseServerSocket()

  def StartProxyServer(self):
    """Start accepting connections."""
    self._TestConnection()
    self._server_socket = self._OpenLocalTcpSocket()
    log.out.Print('Listening on port [%d].' % self._local_port)

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
    # Python socket accept() on Windows does not get interrupted by ctrl-C
    # To work around that, use select() with a timeout before the accept()
    # which allows for the ctrl-C to be noticed and abort the process as
    # expected.
    ready_sockets = [()]
    while not ready_sockets[0]:
      # 0.2 second timeout
      ready_sockets = select.select((self._server_socket,), (), (), 0.2)

    conn, socket_address = self._server_socket.accept()
    log.info('New connection from [%r]', socket_address)
    new_thread = threading.Thread(target=self._HandleNewConnection,
                                  args=(conn, socket_address))
    new_thread.daemon = True
    new_thread.start()
    return new_thread, conn

  def _CloseServerSocket(self):
    log.debug('Stopping server.')
    try:
      if self._server_socket:
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

  def _HandleNewConnection(self, conn, socket_address):
    try:
      self._RunReceiveLocalData(conn, socket_address)
    except EnvironmentError as e:
      log.info('Socket error [%s] while receiving from client.', str(e))
    except:  # pylint: disable=bare-except
      log.exception('Error while receiving from client.')


# TODO(b/119212951): Investigate alternatives to opening a local port like
#                    ssh_config ProxyCommand and PuTTY plink.exe
# TODO(b/119622656): Implement as context manager
class IapTunnelConnectionHelper(_BaseIapTunnelHelper):
  """Facilitates connections by opening a port and connecting through IAP."""

  def __init__(self, args, project, zone, instance, interface, port):
    local_port = DetermineLocalPort()
    super(IapTunnelConnectionHelper, self).__init__(
        args, project, zone, instance, interface, port, 'localhost', local_port)
    self._server_socket = None
    self._listen_thread = None

  def __del__(self):
    self._CloseServerSocket()

  def StartListener(self, accept_multiple_connections=False):
    """Start a server socket and listener thread."""
    self._server_socket = self._OpenLocalTcpSocket()
    self._listen_thread = threading.Thread(
        target=functools.partial(self._ListenAndConnect,
                                 accept_multiple_connections))
    self._listen_thread.daemon = True
    self._listen_thread.start()

  def StopListener(self):
    self._CloseServerSocket()
    self._shutdown = True

  def GetLocalPort(self):
    return self._socket_address[1] if self._socket_address else None

  def _AcceptAndHandleNewConnection(self):
    """Accept and handle one connection."""
    conn = None
    try:
      conn, client_socket_address = self._server_socket.accept()
      try:
        self._RunReceiveLocalData(conn, client_socket_address)
      except Exception as e:  # pylint: disable=broad-except
        if isinstance(e, EnvironmentError):
          log.debug('Socket error [%s] while receiving from client.',
                    str(e))
        else:
          log.debug('Error while receiving from client.', exc_info=True)
        raise
    finally:
      try:
        if conn:
          conn.close()
      except EnvironmentError:
        pass

  def _CloseServerSocket(self):
    log.debug('Stopping server.')
    try:
      if self._server_socket:
        self._server_socket.close()
    except EnvironmentError:
      pass

  def _ListenAndConnect(self, accept_multiple_connections):
    """Listen for connection and connect WebSocket IAP Tunnel."""
    try:
      if accept_multiple_connections:
        while not self._shutdown:
          try:
            self._AcceptAndHandleNewConnection()
          except:  # pylint: disable=bare-except
            pass
      else:
        self._AcceptAndHandleNewConnection()
    finally:
      self._CloseServerSocket()
