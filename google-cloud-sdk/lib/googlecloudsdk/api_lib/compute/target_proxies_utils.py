# -*- coding: utf-8 -*- #
# Copyright 2016 Google LLC. All Rights Reserved.
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
"""Code that's shared between multiple target-*-proxies subcommands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


def AddProxyHeaderRelatedCreateArgs(parser, default='NONE'):
  """Adds parser arguments for creation related to ProxyHeader."""

  parser.add_argument(
      '--proxy-header',
      choices={
          'NONE': 'No proxy header is added.',
          'PROXY_V1': (
              'Enables PROXY protocol (version 1) for passing client '
              'connection information.'
          ),
      },
      default=default,
      help='The type of proxy protocol header to be sent to the backend.',
  )


def AddProxyHeaderRelatedUpdateArgs(parser):
  """Adds parser arguments for update related to ProxyHeader."""

  AddProxyHeaderRelatedCreateArgs(parser, default=None)


def AddQuicOverrideCreateArgs(parser, default='NONE'):
  """Adds parser arguments for creation related to QuicOverride."""

  parser.add_argument(
      '--quic-override',
      choices={
          'NONE': 'Allows Google to control when QUIC is rolled out.',
          'ENABLE': 'Allows load balancer to negotiate QUIC with clients.',
          'DISABLE': 'Disallows load balancer to negotiate QUIC with clients.',
      },
      default=default,
      help=(
          'Controls whether load balancer may negotiate QUIC with clients. QUIC'
          ' is a new transport which reduces latency compared to that of TCP.'
          ' See https://www.chromium.org/quic for more details.'
      ),
  )


def AddQuicOverrideUpdateArgs(parser):
  """Adds parser arguments for update related to QuicOverride."""

  AddQuicOverrideCreateArgs(parser, default=None)


def AddTlsEarlyDataCreateArgs(parser, default=None):
  """Adds parser arguments for creation related to TlsEarlyData."""

  parser.add_argument(
      '--tls-early-data',
      choices={
          'DISABLED': (
              'TLS 1.3 Early Data is not advertised, and any (invalid) attempts'
              ' to send Early Data will be rejected.'
          ),
          'STRICT': (
              'Enables TLS 1.3 Early Data for requests with safe HTTP methods,'
              ' and HTTP requests that do not have query parameters. Requests'
              ' that send Early Data containing non-idempotent HTTP methods or'
              ' with query parameters will be rejected with a HTTP 425.'
          ),
          'PERMISSIVE': (
              'Enables TLS 1.3 Early Data for requests with safe HTTP methods'
              ' (GET, HEAD, OPTIONS, TRACE). This mode does not enforce any'
              ' other limitations for requests with Early Data. The application'
              ' owner should validate that Early Data is acceptable for a given'
              ' request path.'
          ),
      },
      default=default,
      help=(
          'TLS 1.3 Early Data ("0-RTT" or "zero round trip") allows clients to'
          ' include HTTP request data alongside a TLS handshake. This can'
          ' improve application performance, especially on networks where'
          ' connection interruptions may be common, such as on mobile. This'
          ' applies to both HTTP over TCP (ie: HTTP/1.1 and HTTP/2) and HTTP/3'
          ' over QUIC.'
      ),
  )


def AddTlsEarlyDataUpdateArgs(parser):
  """Adds parser arguments for update related to TlsEarlyData."""

  AddTlsEarlyDataCreateArgs(parser, default=None)


def AddHttpKeepAliveTimeoutSec(parser):
  """Adds the http keep alive timeout sec argument."""
  parser.add_argument(
      '--http-keep-alive-timeout-sec',
      type=arg_parsers.BoundedInt(5, 1200),
      help="""\
      Represents the maximum amount of time that a TCP connection can be idle
      between the (downstream) client and the target HTTP proxy. If an HTTP
      keepalive  timeout is not specified, the default value is 610 seconds.
      For global external Application Load Balancers, the minimum allowed
      value is 5 seconds and the maximum allowed value is 1200 seconds.
      """,
  )


def AddClearHttpKeepAliveTimeoutSec(parser):
  """Adds the http keep alive timeout sec argument."""
  parser.add_argument(
      '--clear-http-keep-alive-timeout-sec',
      action='store_true',
      default=False,
      help="""\
      Clears the previously configured HTTP keepalive timeout.
      """,
  )
