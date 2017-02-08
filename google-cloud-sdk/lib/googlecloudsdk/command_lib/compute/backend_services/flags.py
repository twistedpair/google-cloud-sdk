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

import argparse
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import flags as compute_flags


ZONAL_INSTANCE_GROUP_ARG = compute_flags.ResourceArgument(
    name='--instance-group',
    resource_name='instance group',
    completion_resource_id='compute.instanceGroups',
    zonal_collection='compute.instanceGroups',
    zone_explanation=compute_flags.ZONE_PROPERTY_EXPLANATION)


MULTISCOPE_INSTANCE_GROUP_ARG = compute_flags.ResourceArgument(
    name='--instance-group',
    resource_name='instance group',
    completion_resource_id='compute.instanceGroups',
    zonal_collection='compute.instanceGroups',
    regional_collection='compute.regionInstanceGroups',
    zone_explanation=compute_flags.ZONE_PROPERTY_EXPLANATION,
    region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION)


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


def BackendServiceArgumentForUrlMap(required=True):
  return compute_flags.ResourceArgument(
      resource_name='backend service',
      name='--default-service',
      required=required,
      completion_resource_id='compute.backendServices',
      global_collection='compute.backendServices',
      short_help=(
          'A backend service that will be used for requests for which this '
          'URL map has no mappings.'))


def BackendServiceArgumentForUrlMapPathMatcher(required=True):
  return compute_flags.ResourceArgument(
      resource_name='backend service',
      name='--default-service',
      required=required,
      completion_resource_id='compute.backendServices',
      global_collection='compute.backendServices',
      short_help=(
          'A backend service that will be used for requests that the path '
          'matcher cannot match.'))


def BackendServiceArgumentForTargetSslProxy(required=True):
  return compute_flags.ResourceArgument(
      resource_name='backend service',
      name='--backend-service',
      required=required,
      completion_resource_id='compute.backendServices',
      global_collection='compute.backendServices',
      short_help=('.'),
      detailed_help="""\
        A backend service that will be used for connections to the target SSL
        proxy.
        """)


def BackendServiceArgumentForTargetTcpProxy(required=True):
  return compute_flags.ResourceArgument(
      resource_name='backend service',
      name='--backend-service',
      required=required,
      completion_resource_id='compute.backendServices',
      global_collection='compute.backendServices',
      short_help=('.'),
      detailed_help="""\
        A backend service that will be used for connections to the target TCP
        proxy.
        """)


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
      help='Connection draining timeout.')
  connection_draining_timeout.detailed_help = """\
      Connection draining timeout to be used during removal of VMs from
      instance groups. This guarantees that for the specified time all existing
      connections to a VM will remain untouched, but no new connections will be
      accepted. Set timeout to zero to disable connection draining. Enable
      feature by specifying a timeout of up to one hour.
      If the flag is omitted API default value (0s) will be used.
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


def AddCacheKeyIncludeProtocol(parser, default):
  """Adds cache key include/exclude protocol flag to the argparse."""
  cache_key_include_protocol = parser.add_argument(
      '--cache-key-include-protocol',
      action='store_true',
      default=default,
      help='Enable including protocol in cache key.')
  cache_key_include_protocol.detailed_help = """\
      Enable including protocol in cache key. If enabled, http and https
      requests will be cached separately. Can only be applied for global
      resources.
      """


def AddCacheKeyIncludeHost(parser, default):
  """Adds cache key include/exclude host flag to the argparse."""
  cache_key_include_host = parser.add_argument(
      '--cache-key-include-host',
      action='store_true',
      default=default,
      help='Enable including host in cache key.')
  cache_key_include_host.detailed_help = """\
      Enable including host in cache key. If enabled, requests to different
      hosts will be cached separately. Can only be applied for global resources.
      """


def AddCacheKeyIncludeQueryString(parser, default):
  """Adds cache key include/exclude query string flag to the argparse."""
  cache_key_include_query_string = parser.add_argument(
      '--cache-key-include-query-string',
      action='store_true',
      default=default,
      help='Enable including query string in cache key.')
  update_command = default is None
  if update_command:
    cache_key_include_query_string.detailed_help = """\
        Enable including query string in cache key. If enabled, the query string
        parameters will be included according to
        --cache-key-query-string-whitelist and
        --cache-key-query-string-blacklist. If disabled, the entire query string
        will be excluded. Use "--cache-key-query-string-blacklist=" (sets the
        blacklist to the empty list) to include the entire query string. Can
        only be applied for global resources.
        """
  else:  # create command
    cache_key_include_query_string.detailed_help = """\
        Enable including query string in cache key. If enabled, the query string
        parameters will be included according to
        --cache-key-query-string-whitelist and
        --cache-key-query-string-blacklist. If neither is set, the entire query
        string will be included. If disabled, then the entire query string will
        be excluded. Can only be applied for global resources.
        """


def AddCacheKeyQueryStringList(parser):
  cache_key_query_string_list = parser.add_mutually_exclusive_group()
  cache_key_query_string_whitelist = cache_key_query_string_list.add_argument(
      '--cache-key-query-string-whitelist',
      type=arg_parsers.ArgList(min_length=1),
      metavar='QUERY_STRING',
      default=None,
      help=('Specifies a comma separated list of query string parameters'
            'to include in cache keys.'))
  cache_key_query_string_whitelist.detailed_help = """\
      Specifies a comma separated list of query string parameters to include
      in cache keys. All other parameters will be excluded. Either specify
      --cache-key-query-string-whitelist or --cache-key-query-string-blacklist,
      not both. '&' and '=' will be percent encoded and not treated as
      delimiters. Can only be applied for global resources.
      """
  cache_key_query_string_blacklist = cache_key_query_string_list.add_argument(
      '--cache-key-query-string-blacklist',
      type=arg_parsers.ArgList(),
      metavar='QUERY_STRING',
      default=None,
      help=('Specifies a comma separated list of query string parameters'
            'to exclude in cache keys.'))
  cache_key_query_string_blacklist.detailed_help = """\
      Specifies a comma separated list of query string parameters to exclude
      in cache keys. All other parameters will be included. Either specify
      --cache-key-query-string-whitelist or --cache-key-query-string-blacklist,
      not both. '&' and '=' will be percent encoded and not treated as
      delimiters. Can only be applied for global resources.
      """


def AddHealthChecks(parser):
  health_checks = parser.add_argument(
      '--health-checks',
      type=arg_parsers.ArgList(min_length=1),
      metavar='HEALTH_CHECK',
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
      help=('Specifies a list of HTTPS health check objects for checking the '
            'health of the backend service.'))
  https_health_checks.detailed_help = """\
      Specifies a list of HTTPS health check objects for checking the health
      of the backend service.
      """


def AddIap(parser):
  """Add support for --iap flag."""
  # We set this to str, but it's really an ArgDict.  See
  # backend_services_utils.GetIAP for the re-parse and rationale.
  return parser.add_argument(
      '--iap',
      metavar=('disabled|enabled,['
               'oauth2-client-id=OAUTH2-CLIENT-ID,'
               'oauth2-client-secret=OAUTH2-CLIENT-SECRET]'),
      help='Specifies a list of settings for IAP service.')


def AddSessionAffinity(parser, internal_lb=False, target_pools=False,
                       hidden=False):
  """Adds session affinity flag to the argparse."""
  choices = {
      'CLIENT_IP': (
          "Route requests to instances based on the hash of the client's IP "
          'address.'),
      'GENERATED_COOKIE': (
          'Route requests to instances based on the contents of the "GCLB" '
          'cookie set by the load balancer.'),
      'NONE': 'Session affinity is disabled.',
  }
  if internal_lb or target_pools:
    choices.update({
        'CLIENT_IP_PROTO': (
            'Connections from the same client IP with the same IP protocol will'
            'go to the same VM in the pool while that VM remains healthy. This '
            'option cannot be used for HTTP(s) load balancing.'),
    })
  if internal_lb:
    choices.update({
        'CLIENT_IP_PORT_PROTO': (
            'Connections from the same client IP with the same IP protocol and '
            'port will go to the same VM in the backend while that VM remains '
            'healthy. This option cannot be used for HTTP(S) load balancing.'),
    })
  if hidden:
    help_str = argparse.SUPPRESS
  else:
    help_str = 'The type of session affinity to use for this backend service.'
  parser.add_argument(
      '--session-affinity',
      choices=choices,
      # Tri-valued, None => don't include property.
      default='NONE' if target_pools else None,
      type=lambda x: x.upper(),
      help=help_str)


def AddAffinityCookieTtl(parser, hidden=False):
  """Adds affinity cookie Ttl flag to the argparse."""
  if hidden:
    help_str = argparse.SUPPRESS
  else:
    help_str = """If session-affinity is set to "generated_cookie", this flag
            sets the TTL, in seconds, of the resulting cookie."""
  affinity_cookie_ttl = parser.add_argument(
      '--affinity-cookie-ttl',
      type=arg_parsers.Duration(),
      default=None,  # Tri-valued, None => don't include property.
      help=help_str)
  if not hidden:
    affinity_cookie_ttl.detailed_help = """\
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
