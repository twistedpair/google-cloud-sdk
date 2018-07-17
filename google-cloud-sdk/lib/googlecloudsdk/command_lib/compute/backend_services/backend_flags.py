# -*- coding: utf-8 -*- #
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

"""Flags and helpers for the compute backend-services backend commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import flags
from googlecloudsdk.core import log


def AddDescription(parser):
  parser.add_argument(
      '--description',
      help='An optional, textual description for the backend.')


def AddInstanceGroup(parser, operation_type, with_deprecated_zone=False):
  """Add arguments to define instance group."""
  parser.add_argument(
      '--instance-group',
      required=True,
      help='The name or URI of a Google Cloud Instance Group.')

  scope_parser = parser.add_mutually_exclusive_group()
  flags.AddRegionFlag(
      scope_parser,
      resource_type='instance group',
      operation_type='{0} the backend service'.format(operation_type),
      flag_prefix='instance-group',
      explanation=flags.REGION_PROPERTY_EXPLANATION_NO_DEFAULT)
  if with_deprecated_zone:
    flags.AddZoneFlag(
        scope_parser,
        resource_type='instance group',
        operation_type='{0} the backend service'.format(operation_type),
        explanation='DEPRECATED, use --instance-group-zone flag instead.')
  flags.AddZoneFlag(
      scope_parser,
      resource_type='instance group',
      operation_type='{0} the backend service'.format(operation_type),
      flag_prefix='instance-group',
      explanation=flags.ZONE_PROPERTY_EXPLANATION_NO_DEFAULT)


def WarnOnDeprecatedFlags(args):
  if getattr(args, 'zone', None):  # TODO(b/28518663).
    log.warning(
        'The --zone flag is deprecated, please use --instance-group-zone'
        ' instead. It will be removed in a future release.')


def _GetBalancingModes(supports_neg):
  """Returns the --balancing-modes flag value choices name:description dict."""
  per_rate_flags = '*--max-rate-per-instance*'
  per_connection_flags = '*--max-connections-per-instance*'
  utilization_extra_help = ''
  if supports_neg:
    per_rate_flags += '/*--max-rate-per-endpoint*'
    per_connection_flags += '*--max-max-per-endpoint*'
    utilization_extra_help = (
        'This is incompatible with --network-endpoint-group.')
  balancing_modes = {
      'RATE': """\
          Spreads load based on how many requests per second (RPS) the group
          can handle. There are two ways to specify max RPS: *--max-rate* which
          defines the max RPS for the whole group or {}, which defines the max
          RPS on a per-instance basis. Available only for HTTP-based protocols.
          """.format(per_rate_flags),
      'UTILIZATION': """\
          Relies on the CPU utilization of the instances in the group when
          balancing load. Use *--max-utilization* to set a maximum target CPU
          utilization for each instance. Use *--max-rate-per-instance* or
          *--max-rate* to optionally limit based on RPS in addition to CPU.
          You can optionally also limit based on connections (for TCP/SSL) in
          addition to CPU by setting *--max-connections* or
          *--max-connections-per-instance*. Available for all services without
          *--load-balancing-scheme INTERNAL*. {}
          """.format(utilization_extra_help),
      'CONNECTION': """\
          Spreads load based on how many concurrent connections the group
          can handle. There are two ways to specify max connections:
          *--max-connections* which defines the max number of connections
          for the whole group or {}, which
          defines the max number of connections on a per-instance basis.
          Available for all services.
          """.format(per_connection_flags),
  }
  return balancing_modes


def AddBalancingMode(parser, supports_neg=False):
  """Add balancing mode arguments."""
  parser.add_argument(
      '--balancing-mode',
      choices=_GetBalancingModes(supports_neg),
      type=lambda x: x.upper(),
      help="""\
      Defines the strategy for balancing load.""")


def AddMaxUtilization(parser):
  parser.add_argument(
      '--max-utilization',
      type=arg_parsers.BoundedFloat(lower_bound=0.0, upper_bound=1.0),
      help="""\
      The maximum average CPU utilization of the backend service.
      Acceptable values are `0.0` (0%) through `1.0` (100%). This flag can only
      be provided when the balancing mode is *UTILIZATION*.
      """)


def AddCapacityLimits(parser, supports_neg=False):
  """Add capacity thresholds arguments."""
  AddMaxUtilization(parser)
  capacity_group = parser.add_group(mutex=True)
  rate_group, connections_group = capacity_group, capacity_group
  if supports_neg:
    rate_group = capacity_group.add_group(mutex=True)
    connections_group = capacity_group.add_group(mutex=True)
    rate_group.add_argument(
        '--max-rate-per-endpoint',
        type=float,
        help="""\
        Valid only for `--network-endpoint-group`. This is used to
        calculate the capacity of the group. Can be used in any
        balancing mode except `UTILIZATION`. Maximum number of requests
        per second that can be sent to each endpoint in the network
        endpoint group.
        """)
    connections_group.add_argument(
        '--max-connections-per-endpoint',
        type=int,
        help="""\
        Valid only for `--network-endpoint-group`. The maximum number of
        simultaneous connections that a single network endpoint can
        handle. This is used to calculate the capacity of the group.
        Balancing mode must be set to CONNECTION and one of
        --max-connections, --max-connections-per-instance, or
        --max-connections-per-endpoint must be set.
        """)

  rate_group.add_argument(
      '--max-rate',
      type=int,
      help="""\
      Maximum number of requests per second that can be sent to the instance
      group. Must not be used with Autoscaled Managed Instance Groups.
      `--max-rate` and `--max-rate-per-instance` are mutually exclusive.
      However, one of them can be set even if `--balancing-mode` is set to
      `UTILIZATION`. If either `--max-rate` or `--max-rate-per-instance` is set
      and `--balancing-mode` is set to `RATE`, then only that value is
      considered when judging capacity. If either `--max-rate` or
      `--max-rate-per-instance` is set and `--balancing-mode` is set to
      `UTILIZATION`, then instances are judged to be at capacity when either the
      `UTILIZATION` or `RATE` value is reached.
      """)
  rate_group.add_argument(
      '--max-rate-per-instance',
      type=float,
      help="""\
      Maximum number of requests per second that can be sent to each instance in
      the instance group.
      `--max-rate` and `--max-rate-per-instance` are mutually exclusive.
      However, one of them can be set even if `--balancing-mode` is set to
      `UTILIZATION`. If either `--max-rate` or `--max-rate-per-instance` is set
      and `--balancing-mode` is set to `RATE`, then only that value is
      considered when judging capacity. If either `--max-rate` or
      `--max-rate-per-instance` is set and `--balancing-mode` is set to
      `UTILIZATION`, then instances are judged to be at capacity when either the
      `UTILIZATION` or `RATE` value is reached.
      """)
  connections_group.add_argument(
      '--max-connections',
      type=int,
      help=('Maximum concurrent connections that the group can handle. '
            'Valid only for TCP/SSL connections.'))
  connections_group.add_argument(
      '--max-connections-per-instance',
      type=int,
      help=('The maximum concurrent connections per instance. '
            'Valid only for TCP/SSL connections.'))


def AddCapacityScalar(parser):
  parser.add_argument(
      '--capacity-scaler',
      type=arg_parsers.BoundedFloat(lower_bound=0.0, upper_bound=1.0),
      help="""\
      A setting that applies to all balancing modes. This value is multiplied
      by the balancing mode value to set the current max usage of the instance
      group. Acceptable values are `0.0` (0%) through `1.0` (100%). Setting this
      value to `0.0` (0%) drains the backend service. Note that draining a
      backend service only prevents new connections to instances in the group.
      All existing connections are allowed to continue until they close by
      normal means.""")


def AddFailover(parser, default):
  """Adds the failover argument to the argparse."""
  parser.add_argument(
      '--failover',
      action='store_true',
      default=default,
      help="""\
      Designates whether this is a failover backend. More than one
      failover backend can be configured for a given BackendService.
      Not compatible with the --global flag""")
