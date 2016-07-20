# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Flags and helpers for the compute backend-services commands."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import flags as compute_flags


GLOBAL_BACKEND_SERVICE_ARG = compute_flags.ResourceArgument(
    resource_name='backend service',
    completion_resource_id='compute.backendServices',
    global_collection='compute.backendServices')


GLOBAL_MULTI_BACKEND_SERVICE_ARG = compute_flags.ResourceArgument(
    resource_name='backend service',
    completion_resource_id='compute.backendServices',
    plural=True,
    global_collection='compute.backendServices')


GLOBAL_REGIONAL_BACKEND_SERVICE_ARG = compute_flags.ResourceArgument(
    resource_name='backend service',
    completion_resource_id='compute.backendServices',
    regional_collection='compute.regionBackendServices',
    global_collection='compute.backendServices')


GLOBAL_REGIONAL_MULTI_BACKEND_SERVICE_ARG = compute_flags.ResourceArgument(
    resource_name='backend service',
    completion_resource_id='compute.backendServices',
    plural=True,
    regional_collection='compute.regionBackendServices',
    global_collection='compute.backendServices')


def AddLoadBalancingScheme(parser):
  parser.add_argument(
      '--load-balancing-scheme',
      choices=['INTERNAL', 'EXTERNAL'],
      type=lambda x: x.upper(),
      default='EXTERNAL',
      help='Specifies if this is internal or external load balancer.')


def AddConnectionDrainingTimeout(parser):
  connection_draining_timeout = parser.add_argument(
      '--connection-draining-timeout',
      type=arg_parsers.Duration(upper_bound='1h'),
      default=None,  # None => use default 'backend' value.
      help='Connection draining timeout.')
  connection_draining_timeout.detailed_help = """\
      Connection draining timeout to be used during removal of VMs from
      instance groups. This guarantees that for the specified time all existing
      connections to a VM will remain untouched, but no new connections will be
      accepted. Set timeout to zero to disable connection draining. Enable
      feature by specifying a timeout of up to one hour.
      If the flag is omitted API default value will be used.
      Valid units for this flag are `s` for seconds, `m` for minutes, and
      `h` for hours.
      """


def AddEnableCdn(parser, default):
  enable_cdn = parser.add_argument('--enable-cdn',
                                   action='store_true',
                                   default=default,
                                   help='Enable Cloud CDN.')
  enable_cdn.detailed_help = """\
      Enable Cloud CDN for the backend service. Cloud CDN can cache HTTP
      responses from a backend service at the edge of the network, close to
      users. Cloud CDN is disabled by default.
      """


def AddHealthChecks(parser):
  health_checks = parser.add_argument(
      '--health-checks',
      type=arg_parsers.ArgList(min_length=1),
      metavar='HEALTH_CHECK',
      action=arg_parsers.FloatingListValuesCatcher(),
      help=('Specifies a list of health check objects for checking the '
            'health of the backend service.'))
  health_checks.detailed_help = """\
      Specifies a list of health check objects for checking the health of
      the backend service. Health checks need not be for the same protocol
      as that of the backend service.
      """


def AddHttpHealthChecks(parser):
  http_health_checks = parser.add_argument(
      '--http-health-checks',
      type=arg_parsers.ArgList(min_length=1),
      metavar='HTTP_HEALTH_CHECK',
      action=arg_parsers.FloatingListValuesCatcher(),
      help=('Specifies a list of HTTP health check objects for checking the '
            'health of the backend service.'))
  http_health_checks.detailed_help = """\
      Specifies a list of HTTP health check objects for checking the health
      of the backend service.
      """


def AddHttpsHealthChecks(parser):
  https_health_checks = parser.add_argument(
      '--https-health-checks',
      type=arg_parsers.ArgList(min_length=1),
      metavar='HTTPS_HEALTH_CHECK',
      action=arg_parsers.FloatingListValuesCatcher(),
      help=('Specifies a list of HTTPS health check objects for checking the '
            'health of the backend service.'))
  https_health_checks.detailed_help = """\
      Specifies a list of HTTPS health check objects for checking the health
      of the backend service.
      """


def AddSessionAffinity(parser, internal_lb=False):
  """Adds session affinity flag to the argparse."""
  choices = ['CLIENT_IP', 'GENERATED_COOKIE', 'NONE']
  if internal_lb:
    choices.extend(['CLIENT_IP_PROTO', 'CLIENT_IP_PORT_PROTO'])
  session_affinity = parser.add_argument(
      '--session-affinity',
      choices=sorted(choices),
      default=None,  # Tri-valued, None => don't include property.
      type=lambda x: x.upper(),
      help='The type of session affinity to use.')
  session_affinity.detailed_help = """\
      The type of session affinity to use for this backend service.  Possible
      values are:

        * none: Session affinity is disabled.
        * client_ip: Route requests to instances based on the hash of the
          client's IP address."""
  if internal_lb:
    session_affinity.detailed_help += """
        * client_ip_proto: Connections from the same client IP with the same IP
          protocol will go to the same VM in the pool while that VM remains
          healthy. This option cannot be used for HTTP(s) load balancing.
        * client_ip_port_proto: Connections from the same client IP with the
          same IP protocol and port will go to the same VM in the backend while
          that VM remains healthy. This option cannot be used for HTTP(S) load
          balancing."""
  session_affinity.detailed_help += """
        * generated_cookie: Route requests to instances based on the contents
          of the "GCLB" cookie set by the load balancer.
      """


def AddAffinityCookieTtl(parser):
  affinity_cookie_ttl = parser.add_argument(
      '--affinity-cookie-ttl',
      type=int,
      default=None,  # Tri-valued, None => don't include property.
      help=("""If session-affinity is set to "generated_cookie", this flag sets
            the TTL, in seconds, of the resulting cookie."""))
  affinity_cookie_ttl.detailed_helpr = """\
      If session-affinity is set to "generated_cookie", this flag sets
      the TTL, in seconds, of the resulting cookie.  A setting of 0
      indicates that the cookie should be transient.
  """


def AddDescription(parser):
  parser.add_argument(
      '--description',
      help='An optional, textual description for the backend service.')


def AddTimeout(parser, default='30s'):
  timeout = parser.add_argument(
      '--timeout',
      default=default,
      type=arg_parsers.Duration(),
      help=('The amount of time to wait for a backend to respond to a '
            'request before considering the request failed.'))
  timeout.detailed_help = """\
      The amount of time to wait for a backend to respond to a request
      before considering the request failed. For example, specifying
      ``10s'' will give backends 10 seconds to respond to
      requests. Valid units for this flag are ``s'' for seconds, ``m''
      for minutes, and ``h'' for hours.
      """


def AddPortName(parser):
  """Add port and port-name flags."""
  # TODO(user): Remove port once port_name is in use. b/16486110
  parser.add_argument(
      '--port',
      type=int,
      help=('The TCP port to use when connecting to the backend. '
            '--port is being deprecated in favor of --port-name.'))

  port_name = parser.add_argument(
      '--port-name',
      help=('A user-defined port name used to resolve which port to use on '
            'each backend.'))
  port_name.detailed_help = """\
      The name of a service that has been added to an instance group
      in this backend. Instance group services map a name to a port
      number which is used by the load balancing service.
      Only one ``port-name'' may be added to a backend service, and that
      name must exist as a service on all instance groups that are a
      part of this backend service. The port number associated with the
      name may differ between instances. If you do not specify
      this flag, your instance groups must have a service named ``http''
      configured. See also
      `gcloud compute instance-groups set-named-ports --help`.
      """


def AddProtocol(parser, default='HTTP'):
  parser.add_argument(
      '--protocol',
      choices=['HTTP', 'HTTPS', 'SSL', 'TCP', 'UDP'],
      default=default,
      type=lambda x: x.upper(),
      help='The protocol for incoming requests.')
