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

"""Utility functions for WebSocket tunnelling with Cloud IAP."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import os
import struct
import sys

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import http_proxy_types
import httplib2
import six
from six.moves.urllib import parse
import socks

URL_SCHEME = 'wss'
URL_HOST = 'tunnel.cloudproxy.app'
URL_PATH_ROOT = '/v4'

SUBPROTOCOL_NAME = 'relay.tunnel.cloudproxy.app'
SUBPROTOCOL_TAG_LEN = 2
SUBPROTOCOL_HEADER_LEN = 6
SUBPROTOCOL_MAX_DATA_FRAME_SIZE = 16 * 1024
SUBPROTOCOL_TAG_CONNECT_SUCCESS_SID = 0x01
SUBPROTOCOL_TAG_DATA = 0x04
SUPPORTED_SUBPROTOCOLS = (SUBPROTOCOL_TAG_CONNECT_SUCCESS_SID,
                          SUBPROTOCOL_TAG_DATA)

# The proxy_info field should be either None or type httplib2.ProxyInfo
IapTunnelTargetInfo = collections.namedtuple(
    'IapTunnelTarget',
    ['project', 'zone', 'instance', 'interface', 'port', 'url_override',
     'proxy_info'])


class CACertsFileUnavailable(exceptions.Error):
  pass


class InvalidWebSocketSubprotocolData(exceptions.Error):
  pass


class MissingTunnelParameter(exceptions.Error):
  pass


class PythonVersionMissingSNI(exceptions.Error):
  pass


class UnsupportedProxyType(exceptions.Error):
  pass


def ValidateParameters(tunnel_target):
  for field_name, field_value in tunnel_target._asdict().items():
    if not field_value and field_name not in ('url_override', 'proxy_info'):
      raise MissingTunnelParameter('Missing required tunnel argument: ' +
                                   field_name)
  if tunnel_target.proxy_info:
    proxy_type = tunnel_target.proxy_info.proxy_type
    if (proxy_type and proxy_type != socks.PROXY_TYPE_HTTP):
      raise UnsupportedProxyType(
          'Unsupported proxy type: ' +
          http_proxy_types.REVERSE_PROXY_TYPE_MAP[proxy_type])


def CheckCACertsFile(ignore_certs):
  """Get and check that CA cert file exists."""
  ca_certs = httplib2.CA_CERTS
  custom_ca_certs = properties.VALUES.core.custom_ca_certs_file.Get()
  if custom_ca_certs:
    ca_certs = custom_ca_certs
  if not os.path.exists(ca_certs):
    error_msg = 'Unable to locate CA certificates file.'
    log.Print(error_msg)
    error_msg += ' [%s]' % ca_certs
    if ignore_certs:
      log.info(error_msg)
    else:
      raise CACertsFileUnavailable(error_msg)
  return ca_certs


def CheckPythonVersion(ignore_certs):
  if (not ignore_certs and
      (six.PY2 and sys.version_info < (2, 7, 9) or
       six.PY3 and sys.version_info < (3, 2, 0))):
    raise PythonVersionMissingSNI(
        'Python version %d.%d.%d does not support SSL/TLS SNI needed for '
        'certificate verification on WebSocket connection.' %
        (sys.version_info.major, sys.version_info.minor,
         sys.version_info.micro))


def CreateWebSocketUrl(endpoint, tunnel_target):
  """Create URL for WebSocket connection."""
  scheme, hostname, path_root = (URL_SCHEME, URL_HOST, URL_PATH_ROOT)
  if tunnel_target.url_override:
    url_override_parts = parse.urlparse(tunnel_target.url_override)
    scheme, hostname = url_override_parts[:2]
    path_override = url_override_parts[2]
    if path_override and path_override != '/':
      path_root = path_override

  url_query_pieces = {'project': tunnel_target.project,
                      'zone': tunnel_target.zone,
                      'instance': tunnel_target.instance,
                      'interface': tunnel_target.interface,
                      'port': tunnel_target.port}
  qs = parse.urlencode(url_query_pieces)
  path = ('%s%s' % (path_root, endpoint) if path_root.endswith('/')
          else '%s/%s' % (path_root, endpoint))
  return parse.urlunparse((scheme, hostname, path, '', qs, ''))


def CreateSubprotocolDataFrame(bytes_to_send):
  return struct.pack(str('>HI%ds' % len(bytes_to_send)),
                     SUBPROTOCOL_TAG_DATA, len(bytes_to_send), bytes_to_send)


def ExtractSubprotocolData(binary_data):
  """Extract tag and data from subprotocol data frame."""
  try:
    subprotocol_tag = struct.unpack(
        str('>H'), binary_data[:SUBPROTOCOL_TAG_LEN])[0]
  except struct.error:
    log.exception('Invalid WebSocket subprotocol tag.')
    raise InvalidWebSocketSubprotocolData(
        'Invalid WebSocket subprotocol tag')

  if subprotocol_tag not in SUPPORTED_SUBPROTOCOLS:
    return subprotocol_tag, None

  try:
    data_len = struct.unpack(
        str('>I'), binary_data[SUBPROTOCOL_TAG_LEN:SUBPROTOCOL_HEADER_LEN])[0]
  except struct.error:
    log.exception('Invalid WebSocket subprotocol data length.')
    raise InvalidWebSocketSubprotocolData(
        'Invalid WebSocket subprotocol data length')

  if not data_len:
    return subprotocol_tag, None

  data = None
  if data_len:
    if data_len > SUBPROTOCOL_MAX_DATA_FRAME_SIZE:
      log.warning('Discarding unexpectedly large data frame [%r]', data_len)
    else:
      data_end = SUBPROTOCOL_HEADER_LEN + data_len
      data = struct.unpack(
          str('%ds' % data_len),
          binary_data[SUBPROTOCOL_HEADER_LEN:data_end])[0]
  return subprotocol_tag, data
