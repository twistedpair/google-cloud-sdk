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
"""Code that's shared between multiple health-checks subcommands."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions


THRESHOLD_UPPER_BOUND = 10
THRESHOLD_LOWER_BOUND = 1
TIMEOUT_UPPER_BOUND_SEC = 300
TIMEOUT_LOWER_BOUND_SEC = 1
CHECK_INTERVAL_UPPER_BOUND_SEC = 300
CHECK_INTERVAL_LOWER_BOUND_SEC = 1


def AddProtocolAgnosticCreationArgs(parser, protocol_string):
  """Adds parser arguments common to creation for all protocols."""

  parser.add_argument(
      '--check-interval',
      type=arg_parsers.Duration(),
      default='5s',
      help="""\
      How often to perform a health check for an instance. For example,
      specifying ``10s'' will run the check every 10 seconds. Valid units
      for this flag are ``s'' for seconds and ``m'' for minutes.
      The default value is ``5s''.
       """)

  parser.add_argument(
      '--timeout',
      type=arg_parsers.Duration(),
      default='5s',
      help="""\
      If Google Compute Engine doesn't receive a healthy response from the
      instance by the time specified by the value of this flag, the health
      check request is considered a failure. For example, specifying ``10s''
      will cause the check to wait for 10 seconds before considering the
      request a failure.  Valid units for this flag are ``s'' for seconds and
      ``m'' for minutes.  The default value is ``5s''.
      """)

  parser.add_argument(
      '--unhealthy-threshold',
      type=int,
      default=2,
      help="""\
      The number of consecutive health check failures before a healthy
      instance is marked as unhealthy. The default is 2.
      """)

  parser.add_argument(
      '--healthy-threshold',
      type=int,
      default=2,
      help="""\
      The number of consecutive successful health checks before an
      unhealthy instance is marked as healthy. The default is 2.
      """)

  parser.add_argument(
      '--description',
      help="""\
      An optional string description for the """ + protocol_string + """ health
      check.
      """)


def AddProtocolAgnosticUpdateArgs(parser, protocol_string):
  """Adds parser arguments common to update subcommand for all protocols."""

  parser.add_argument(
      '--check-interval',
      type=arg_parsers.Duration(),
      help="""\
      How often to perform a health check for an instance. For example,
      specifying ``10s'' will run the check every 10 seconds. Valid units
      for this flag are ``s'' for seconds and ``m'' for minutes.
      """)

  parser.add_argument(
      '--timeout',
      type=arg_parsers.Duration(),
      help="""\
      If Google Compute Engine doesn't receive a healthy response from the
      instance by the time specified by the value of this flag, the health
      check request is considered a failure. For example, specifying ``10s''
      will cause the check to wait for 10 seconds before considering the
      request a failure.  Valid units for this flag are ``s'' for seconds and
      ``m'' for minutes.
      """)

  parser.add_argument(
      '--unhealthy-threshold',
      type=int,
      help="""\
      The number of consecutive health check failures before a healthy
      instance is marked as unhealthy.
      """)

  parser.add_argument(
      '--healthy-threshold',
      type=int,
      help="""\
      The number of consecutive successful health checks before an
      unhealthy instance is marked as healthy.
      """)

  parser.add_argument(
      '--description',
      help=('A textual description for the ' + protocol_string +
            ' health check. Pass in an empty string to unset.'))


def AddHttpRelatedCreationArgs(parser):
  """Adds parser arguments for creation related to HTTP."""

  _AddPortRelatedCreationArgs(parser)
  AddProxyHeaderRelatedCreateArgs(parser)

  parser.add_argument(
      '--host',
      help="""\
      The value of the host header used in this HTTP health check request.
      By default, this is empty and Google Compute Engine automatically sets
      the host header in health requests to the same external IP address as
      the forwarding rule associated with the target pool.
      """)

  parser.add_argument(
      '--request-path',
      default='/',
      help="""\
      The request path that this health check monitors. For example,
      ``/healthcheck''. The default value is ``/''.
      """)


def AddHttpRelatedResponseArg(parser):
  """Adds parser argument for HTTP response field."""

  parser.add_argument(
      '--response',
      help="""\
      When empty, status code of the response determines health. When not empty,
      presence of specified string in first 1024 characters of response body
      determines health. Only ASCII characters allowed.
      """)


def AddHttpRelatedUpdateArgs(parser):
  """Adds parser arguments for update subcommands related to HTTP."""

  _AddPortRelatedUpdateArgs(parser)
  AddProxyHeaderRelatedUpdateArgs(parser)

  parser.add_argument(
      '--host',
      help="""\
      The value of the host header used in this HTTP health check request.
      By default, this is empty and Google Compute Engine automatically sets
      the host header in health requests to the same external IP address as
      the forwarding rule associated with the target pool. Setting this to
      an empty string will clear any existing host value.
      """)

  parser.add_argument(
      '--request-path',
      help="""\
      The request path that this health check monitors. For example,
      ``/healthcheck''.
      """)


def AddTcpRelatedCreationArgs(parser):
  """Adds parser arguments for creation related to TCP."""

  _AddPortRelatedCreationArgs(parser)
  AddProxyHeaderRelatedCreateArgs(parser)
  _AddTcpRelatedArgsImpl(add_info_about_clearing=False, parser=parser)


def AddTcpRelatedUpdateArgs(parser):
  """Adds parser arguments for update subcommands related to TCP."""

  _AddPortRelatedUpdateArgs(parser)
  AddProxyHeaderRelatedUpdateArgs(parser)
  _AddTcpRelatedArgsImpl(add_info_about_clearing=True, parser=parser)


def AddUdpRelatedArgs(parser, request_and_response_required=True):
  """Adds parser arguments related to UDP."""

  parser.add_argument(
      '--port',
      type=int,
      help="""\
      The UDP port number that this health check monitors. The default is not
      set.
      """)

  parser.add_argument(
      '--port-name',
      help="""\
      The port name that this health check monitors. By default, this is
      empty. Setting this to an empty string will clear any existing
      port-name value.
      """)

  parser.add_argument(
      '--request',
      required=request_and_response_required,
      help="""\
      Application data to send in payload of an UDP packet. It is an error if
      this is empty.
      """)

  parser.add_argument(
      '--response',
      required=request_and_response_required,
      help="""\
      The bytes to match against the beginning of the response data.
      It is an error if this is empty.
      """)


def _AddPortRelatedCreationArgs(parser):
  """Adds parser create subcommand arguments --port and --port-name."""

  parser.add_argument(
      '--port',
      type=int,
      default=80,
      help="""\
      The TCP port number that this health check monitors. The default value
      is 80.
      """)

  parser.add_argument(
      '--port-name',
      help="""\
      The port name that this health check monitors. By default, this is
      empty.
      """)


def _AddPortRelatedUpdateArgs(parser):
  """Adds parser update subcommand arguments --port and --port-name."""

  parser.add_argument(
      '--port',
      type=int,
      help='The TCP port number that this health check monitors.')

  parser.add_argument(
      '--port-name',
      help="""\
      The port name that this health check monitors. By default, this is
      empty. Setting this to an empty string will clear any existing
      port-name value.
      """)


def _AddTcpRelatedArgsImpl(add_info_about_clearing, parser):
  """Adds TCP-related subcommand parser arguments."""

  request_help = """\
      An optional string of up to 1024 characters to send once the health check
      TCP connection has been established. The health checker then looks for a
      reply of the string provided in the `--response` field.

      If `--response` is not configured, the health checker does not wait for a
      response and regards the probe as successful if the TCP or SSL handshake
      was successful.
      """
  response_help = """\
      An optional string of up to 1024 characters that the health checker
      expects to receive from the instance. If the response is not received
      exactly, the health check probe fails. If `--response` is configured, but
      not `--request`, the health checker will wait for a response anyway.
      Unless your system automatically sends out a message in response to a
      successful handshake, only configure `--response` to match an explicit
      `--request`.
      """

  if add_info_about_clearing:
    request_help += """
      Setting this to an empty string will clear any existing request value.
      """
    response_help += """\
      Setting this to an empty string will clear any existing
      response value.
      """

  parser.add_argument(
      '--request',
      help=request_help)

  parser.add_argument(
      '--response',
      help=response_help)


def AddProxyHeaderRelatedCreateArgs(parser, default='NONE'):
  """Adds parser arguments for creation related to ProxyHeader."""

  parser.add_argument(
      '--proxy-header',
      choices={
          'NONE': 'No proxy header is added.',
          'PROXY_V1': r'Adds the header "PROXY UNKNOWN\r\n".',
      },
      default=default,
      help='The type of proxy protocol header to be sent to the backend.')


def AddProxyHeaderRelatedUpdateArgs(parser):
  """Adds parser arguments for update related to ProxyHeader."""

  AddProxyHeaderRelatedCreateArgs(parser, default=None)


def CheckProtocolAgnosticArgs(args):
  """Raises exception if any protocol-agnostic args are invalid."""

  if (args.check_interval is not None
      and (args.check_interval < CHECK_INTERVAL_LOWER_BOUND_SEC
           or args.check_interval > CHECK_INTERVAL_UPPER_BOUND_SEC)):
    raise exceptions.ToolException(
        '[--check-interval] must not be less than {0} second or greater '
        'than {1} seconds; received [{2}] seconds.'.format(
            CHECK_INTERVAL_LOWER_BOUND_SEC, CHECK_INTERVAL_UPPER_BOUND_SEC,
            args.check_interval))

  if (args.timeout is not None
      and (args.timeout < TIMEOUT_LOWER_BOUND_SEC
           or args.timeout > TIMEOUT_UPPER_BOUND_SEC)):
    raise exceptions.ToolException(
        '[--timeout] must not be less than {0} second or greater than {1} '
        'seconds; received: [{2}] seconds.'.format(
            TIMEOUT_LOWER_BOUND_SEC, TIMEOUT_UPPER_BOUND_SEC, args.timeout))

  if (args.healthy_threshold is not None
      and (args.healthy_threshold < THRESHOLD_LOWER_BOUND
           or args.healthy_threshold > THRESHOLD_UPPER_BOUND)):
    raise exceptions.ToolException(
        '[--healthy-threshold] must be an integer between {0} and {1}, '
        'inclusive; received: [{2}].'.format(THRESHOLD_LOWER_BOUND,
                                             THRESHOLD_UPPER_BOUND,
                                             args.healthy_threshold))

  if (args.unhealthy_threshold is not None
      and (args.unhealthy_threshold < THRESHOLD_LOWER_BOUND
           or args.unhealthy_threshold > THRESHOLD_UPPER_BOUND)):
    raise exceptions.ToolException(
        '[--unhealthy-threshold] must be an integer between {0} and {1}, '
        'inclusive; received [{2}].'.format(THRESHOLD_LOWER_BOUND,
                                            THRESHOLD_UPPER_BOUND,
                                            args.unhealthy_threshold))
