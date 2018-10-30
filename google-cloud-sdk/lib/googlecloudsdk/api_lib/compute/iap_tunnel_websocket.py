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

"""WebSocket connection class for tunnelling with Cloud IAP."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import socket
import ssl
import sys
import threading
import time

from googlecloudsdk.api_lib.compute import iap_tunnel_websocket_utils as utils
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import http
from googlecloudsdk.core import log

import websocket

CONNECT_ENDPOINT = 'connect'
TUNNEL_CLOUDPROXY_ORIGIN = 'bot:iap-tunneler'


class ConnectionCreationError(exceptions.Error):
  pass


class ErrorInfoDuringClose(exceptions.Error):
  pass


class ReceiveFromWebSocketError(exceptions.Error):
  pass


class UnexpectedConnectionCloseError(exceptions.Error):
  pass


class UnexpectedWebSocketDataError(exceptions.Error):
  pass


class WebSocketError(exceptions.Error):
  pass


class IapTunnelWebSocket(object):
  """Cloud IAP WebSocket class for tunnelling connections."""

  def __init__(self, tunnel_target, access_token, data_handler_callback,
               ignore_certs=False):
    self._tunnel_target = tunnel_target
    self._access_token = access_token
    self._data_handler_callback = data_handler_callback
    self._ignore_certs = ignore_certs
    self._ca_certs = None

    self._connect_msg_received = False
    self._connection_sid = None
    self._websocket = None
    self._websocket_errors = []
    self._websocket_thread = None

    self._total_bytes_received = 0

  def __del__(self):
    self.Close()

  def InitiateConnection(self):
    """Initiate the WebSocket connection."""
    utils.CheckPythonVersion(self._ignore_certs)
    utils.ValidateParameters(self._tunnel_target)
    self._ca_certs = utils.CheckCACertsFile(self._ignore_certs)

    self._connect_url = utils.CreateWebSocketUrl(CONNECT_ENDPOINT,
                                                 self._tunnel_target)
    headers = ['User-Agent: ' + http.MakeUserAgentString(),
               'Sec-WebSocket-Protocol: ' + utils.SUBPROTOCOL_NAME]
    if self._access_token:
      headers += ['Authorization: Bearer ' + self._access_token]
    log.info('Connecting to with URL %r', self._connect_url)
    self._websocket_errors = []
    self._connection_sid = None

    if log.GetVerbosity() == logging.DEBUG:
      websocket.enableTrace(True)
    else:
      websocket_logger = logging.getLogger('websocket')
      websocket_logger.setLevel(logging.CRITICAL)

    self._websocket = websocket.WebSocketApp(
        self._connect_url, header=headers, on_error=self._OnError,
        on_close=self._OnClose, on_data=self._OnData)
    log.info('Starting WebSocket receive thread.')
    self._websocket_thread = threading.Thread(target=self._ReceiveFromWebSocket)
    self._websocket_thread.daemon = True
    self._websocket_thread.start()

  def _IsConnected(self):
    """Returns true if the websocket is open and we received a connect msg."""
    return (self._websocket and self._websocket.sock and
            self._websocket.sock.connected and self._connect_msg_received)

  def _ReraiseLastErrorIfExists(self):
    if self._websocket_errors:
      exception_obj, tb = self._websocket_errors[-1]
      exceptions.reraise(exception_obj, tb=tb)

  def WaitForOpenOrRaiseError(self):
    """Wait for WebSocket open confirmation or any error condition."""
    log.info('Waiting for WebSocket connection.')
    while (self._websocket and
           not (self._IsConnected() or self._websocket_errors)):
      time.sleep(0.1)
    self._ReraiseLastErrorIfExists()
    if not self._websocket:
      raise ConnectionCreationError('Error while establishing WebSocket')

  def Send(self, bytes_to_send):
    """Send bytes over WebSocket connection."""
    if not self._IsConnected():
      self.WaitForOpenOrRaiseError()
    while bytes_to_send:
      bytes_to_send = self._SendData(bytes_to_send)
    self._SendAck()

  def _SendData(self, bytes_to_send):
    first_to_send = bytes_to_send[:utils.SUBPROTOCOL_MAX_DATA_FRAME_SIZE]
    bytes_to_send = bytes_to_send[utils.SUBPROTOCOL_MAX_DATA_FRAME_SIZE:]
    if first_to_send:
      send_data = utils.CreateSubprotocolDataFrame(first_to_send)
      self._SendBytes(send_data)
    return bytes_to_send

  def _SendAck(self):
    if self._total_bytes_received:
      ack_data = utils.CreateSubprotocolAckFrame(self._total_bytes_received)
      self._SendBytes(ack_data)

  def _SendBytes(self, send_data):
    self._websocket.send(send_data, opcode=websocket.ABNF.OPCODE_BINARY)

  def Close(self):
    self._connect_msg_received = False
    ws, self._websocket = self._websocket, None
    if ws:
      try:
        ws.close()
      except (EnvironmentError, socket.error, websocket.WebSocketException):
        pass
    self._ReraiseLastErrorIfExists()

  def _ReceiveFromWebSocket(self):
    """Receive data from WebSocket connection."""
    sslopt = {'cert_reqs': ssl.CERT_REQUIRED,
              'ca_certs': self._ca_certs}
    if self._ignore_certs:
      sslopt['cert_reqs'] = ssl.CERT_OPTIONAL
      sslopt['check_hostname'] = False

    try:
      proxy_info = self._tunnel_target.proxy_info
      if proxy_info:
        http_proxy_auth = None
        if proxy_info.proxy_user or proxy_info.proxy_pass:
          http_proxy_auth = (proxy_info.proxy_user, proxy_info.proxy_pass)
        self._websocket.run_forever(
            origin=TUNNEL_CLOUDPROXY_ORIGIN, sslopt=sslopt,
            http_proxy_host=proxy_info.proxy_host,
            http_proxy_port=proxy_info.proxy_port,
            http_proxy_auth=http_proxy_auth)
      else:
        self._websocket.run_forever(origin=TUNNEL_CLOUDPROXY_ORIGIN,
                                    sslopt=sslopt)
    except (EnvironmentError, socket.error, websocket.WebSocketException) as e:
      exc_info = sys.exc_info()
      self._websocket_errors.append(
          (ReceiveFromWebSocketError('%s: %s' % (type(e).__name__, str(e))),
           exc_info[2]))
      self.Close()

  def _OnError(self, unused_websocket_app, exception_obj):
    self._websocket_errors.append(
        (WebSocketError('%s: %s' %
                        (type(exception_obj).__name__, str(exception_obj))),
         None))
    self.Close()

  def _OnClose(self, unused_websocket_app, *optional_close_data):
    if optional_close_data:
      self._websocket_errors.append(
          (ErrorInfoDuringClose(repr(optional_close_data)), None))
    else:
      log.info('WebSocket connection closed.')
    self.Close()

  def _OnData(self, unused_websocket_app, binary_data, opcode, unused_finished):
    """Receive a single message from the server.

    Args:
      binary_data: str binary data of proto
      opcode: int signal value for whether data is binary or string
      unused_finished: bool whether this is the final message in a multi-part
                       sequence
    Raises:
      UnexpectedWebSocketDataError: when receive unexpected opcodes or
                                    subprotocol tags
    """
    # Even though we will only be processing BINARY messages, a bug in the
    # underlying websocket library will report the last opcode in a multi-frame
    # message instead of the first opcode - so CONT instead of BINARY.
    if opcode not in (websocket.ABNF.OPCODE_CONT, websocket.ABNF.OPCODE_BINARY):
      raise UnexpectedWebSocketDataError('Unexpected WebSocket opcode [%r].' %
                                         opcode)

    tag, bytes_left = utils.ExtractSubprotocolTag(binary_data)
    # In order of decreasing usage during connection:
    if tag == utils.SUBPROTOCOL_TAG_DATA:
      self._HandleSubprotocolData(bytes_left)
    elif tag == utils.SUBPROTOCOL_TAG_CONNECT_SUCCESS_SID:
      self._HandleSubprotocolConnectSuccessSid(bytes_left)
    else:
      log.warning('Unsupported subprotocol tag [%r], discarding the message',
                  tag)

  def _HandleSubprotocolConnectSuccessSid(self, binary_data):
    """Handle Subprotocol CONNECT_SUCCESS_SID Frame."""
    data, bytes_left = utils.ExtractSubprotocolConnectSuccessSid(binary_data)
    self._connection_sid = data
    self._connect_msg_received = True
    if bytes_left:
      log.warning(
          'Discarding %d extra bytes after processing CONNECT_SUCCESS_SID',
          len(bytes_left))

  def _HandleSubprotocolData(self, binary_data):
    """Handle Subprotocol DATA Frame."""
    if not self._IsConnected():
      raise UnexpectedWebSocketDataError('Received DATA before connected.')

    data, bytes_left = utils.ExtractSubprotocolData(binary_data)
    self._total_bytes_received += len(data)
    self._data_handler_callback(data)
    if bytes_left:
      log.warning('Discarding %d extra bytes after processing DATA',
                  len(bytes_left))
