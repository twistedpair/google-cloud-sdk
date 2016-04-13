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
"""Code that's shared between multiple backend-services subcommands."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags


def BalancingModes(backend):
  return sorted(backend.BalancingModeValueValuesEnum.to_dict())


def ProtocolOptions(backend_service):
  return sorted(backend_service.ProtocolValueValuesEnum.to_dict())


def AddUpdatableArgs(parser,
                     compute_messages,
                     default_protocol='HTTP',
                     default_timeout='30s'):
  """Adds top-level backend service arguments that can be updated."""
  parser.add_argument(
      '--description',
      help='An optional, textual description for the backend service.')

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

  timeout = parser.add_argument(
      '--timeout',
      default=default_timeout,
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

  parser.add_argument(
      '--protocol',
      choices=ProtocolOptions(compute_messages.BackendService),
      default=default_protocol,
      type=lambda x: x.upper(),
      help='The protocol for incoming requests.')


def AddUpdatableBackendArgs(parser, compute_messages, multizonal=False):
  """Adds arguments for manipulating backends in a backend service."""
  parser.add_argument(
      '--description',
      help='An optional, textual description for the backend.')

  g = parser.add_mutually_exclusive_group(required=True)

  g.add_argument(
      '--group',
      help=('The name of the legacy instance group '
            '(deprecated resourceViews API) that will receive the traffic. '
            'Use --instance-group flag instead.'))

  g.add_argument(
      '--instance-group',
      help=('The name or URI of a Google Cloud Instance Group that can receive'
            ' traffic.'))

  scope_parser = parser
  if multizonal:
    scope_parser = parser.add_mutually_exclusive_group()
    flags.AddRegionFlag(
        scope_parser,
        resource_type='instance group',
        operation_type='add to the backend service')
  flags.AddZoneFlag(
      scope_parser,
      resource_type='instance group',
      operation_type='add to the backend service')

  balancing_mode = parser.add_argument(
      '--balancing-mode',
      choices=BalancingModes(compute_messages.Backend),
      type=lambda x: x.upper(),
      help='Defines the strategy for balancing load.')
  balancing_mode.detailed_help = """\
      Defines the strategy for balancing load. ``UTILIZATION'' will
      rely on the CPU utilization of the instances in the group when
      balancing load. When using ``UTILIZATION'',
      ``--max-utilization'' can be used to set a maximum target CPU
      utilization for each instance. ``RATE'' will spread load based on
      how many requests per second (RPS) the group can handle. There
      are two ways to specify max RPS: ``--max-rate'' which defines
      the max RPS for the whole group or ``--max-rate-per-instance'',
      which defines the max RPS on a per-instance basis.

      In ``UTILIZATION'', you can optionally limit based on RPS in
      addition to CPU by setting either ``--max-rate-per-instance'' or
      ``--max-rate''.
      """

  max_utilization = parser.add_argument(
      '--max-utilization',
      type=float,
      help=('The target CPU utilization of the group as a '
            'float in the range [0.0, 1.0].'))
  max_utilization.detailed_help = """\
      The target CPU utilization for the group as a float in the range
      [0.0, 1.0]. This flag can only be provided when the balancing
      mode is ``UTILIZATION''.
      """

  rate_group = parser.add_mutually_exclusive_group()

  rate_group.add_argument(
      '--max-rate',
      type=int,
      help='Maximum requests per second (RPS) that the group can handle.')

  rate_group.add_argument(
      '--max-rate-per-instance',
      type=float,
      help='The maximum per-instance requests per second (RPS).')

  capacity_scaler = parser.add_argument(
      '--capacity-scaler',
      type=float,
      help=('A float in the range [0, 1.0] that scales the maximum '
            'parameters for the group (e.g., max rate).'))
  capacity_scaler.detailed_help = """\
      A float in the range [0, 1.0] that scales the maximum
      parameters for the group (e.g., max rate). A value of 0.0 will
      cause no requests to be sent to the group (i.e., it adds the
      group in a ``drained'' state). The default is 1.0.
      """


def GetHealthChecks(args, resource_parser):
  """Returns health check URIs from arguments."""
  health_check_refs = []

  if args.http_health_checks:
    health_check_refs.extend(resource_parser.CreateGlobalReferences(
        args.http_health_checks, resource_type='httpHealthChecks'))

  if getattr(args, 'https_health_checks', None):
    health_check_refs.extend(resource_parser.CreateGlobalReferences(
        args.https_health_checks, resource_type='httpsHealthChecks'))

  if getattr(args, 'health_checks', None):
    if health_check_refs:
      raise exceptions.ToolException(
          'Mixing --health-checks with --http-health-checks or with '
          '--https-health-checks is not supported.')
    else:
      health_check_refs.extend(resource_parser.CreateGlobalReferences(
          args.health_checks, resource_type='healthChecks'))

  return [health_check_ref.SelfLink() for health_check_ref in health_check_refs]
