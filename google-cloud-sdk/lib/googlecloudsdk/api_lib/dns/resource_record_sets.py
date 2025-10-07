# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Helper methods for record-sets."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import dataclasses
import re
from typing import Any, Collection, Mapping

from dns import rdatatype
from googlecloudsdk.api_lib.dns import import_util
from googlecloudsdk.api_lib.dns import record_types
from googlecloudsdk.api_lib.dns import util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources
import ipaddr


class UnsupportedRecordType(exceptions.Error):
  """Unsupported record-set type."""


class ForwardingRuleWithoutHealthCheck(exceptions.Error):
  """Forwarding rules specified without enabling health check."""


class HealthCheckWithoutForwardingRule(exceptions.Error):
  """Health check enabled but no forwarding rules present."""


class ExternalEndpointsWithoutHealthCheck(exceptions.Error):
  """External endpoints specified without enabling health check."""


class HealthCheckWithoutExternalEndpoints(exceptions.Error):
  """Health check enabled but no external endpoints present."""


class ForwardingRuleNotFound(exceptions.Error):
  """Either the forwarding rule doesn't exist, or multiple forwarding rules present with the same name - across different regions."""


class UnsupportedLoadBalancingScheme(exceptions.Error):
  """Unsupported load balancing scheme."""


class EitherWeightOrLocationSpecified(exceptions.Error):
  """The Routing policy item should have either weight or location specified depending on the routing policy type."""


class HealthCheckOnlyWithRoutingPolicyItem(exceptions.Error):
  """The internet health check flag should be set only with routing policy item and not the routing policy data."""


class HealthCheckOnlyWithExternalEndpoints(exceptions.Error):
  """The internet health check flag should be set iff thre are external endpoints."""


class HealthCheckOnlyForARecordType(exceptions.Error):
  """The health check flags should be set only for A/AAAA record type."""


@dataclasses.dataclass(frozen=True)
class RoutingPolicyItem:
  """A routing policy item."""
  item_key: str
  routing_policy_data: 'RoutingPolicyData'


@dataclasses.dataclass(frozen=True)
class RoutingPolicyData:
  """A routing policy data.

  Includes the rrdata, health checked public ips, and health checked internal
  load balancers.
  """
  rrdatas: Collection[str]
  health_checked_ips: Collection[str]
  internal_load_balancers: Collection[str]


def _TryParseRRTypeFromString(type_str):
  """Tries to parse the rrtype wire value from the given string.

  Args:
    type_str: The record type as a string (e.g. "A", "MX"...).

  Raises:
    UnsupportedRecordType: If given record-set type is not supported

  Returns:
    The wire value rrtype as an int or rdatatype enum.
  """
  rd_type = rdatatype.from_text(type_str)
  if rd_type not in record_types.SUPPORTED_TYPES:
    raise UnsupportedRecordType('Unsupported record-set type [%s]' % type_str)
  return rd_type


def GetLoadBalancerTarget(forwarding_rule, api_version, project):
  """Creates and returns a LoadBalancerTarget for the given forwarding rule name.

  Args:
    forwarding_rule: The name of the forwarding rule followed by '@' followed by
      the scope of the forwarding rule.
    api_version: [str], the api version to use for creating the RecordSet.
    project: The GCP project where the forwarding_rule exists.

  Raises:
    ForwardingRuleNotFound: Either the forwarding rule doesn't exist, or
      multiple forwarding rules present with the same name - across different
      regions.
    UnsupportedLoadBalancingScheme: The requested load balancer uses a load
      balancing scheme that is not supported by Cloud DNS Policy Manager.

  Returns:
    LoadBalancerTarget, the load balancer target for the given forwarding rule.
  """
  compute_client = apis.GetClientInstance('compute', 'v1')
  compute_messages = apis.GetMessagesModule('compute', 'v1')
  dns_messages = apis.GetMessagesModule('dns', api_version)
  load_balancer_target = apis.GetMessagesModule(
      'dns', api_version).RRSetRoutingPolicyLoadBalancerTarget()
  load_balancer_target.project = project
  load_balancer_type = ''
  if len(forwarding_rule.split('@')) == 2:
    name, scope = forwarding_rule.split('@')
    if scope == 'global':
      config = compute_client.globalForwardingRules.Get(
          compute_messages.ComputeGlobalForwardingRulesGetRequest(
              project=project, forwardingRule=name
          )
      )
    else:
      load_balancer_target.region = scope
      config = compute_client.forwardingRules.Get(
          compute_messages.ComputeForwardingRulesGetRequest(
              project=project, forwardingRule=name, region=scope
          )
      )
    if config is None:
      raise ForwardingRuleNotFound(
          "Either the forwarding rule doesn't exist, or multiple forwarding "
          'rules are present with the same name - across different regions.'
      )
  else:
    try:
      config = GetLoadBalancerConfigFromUrl(
          compute_client, compute_messages, forwarding_rule
      )
      project_match = re.match(r'.*/projects/([^/]+)/.*', config.selfLink)
      load_balancer_target.project = project_match.group(1)
      if config.region:
        # region returned in the response is the url of the form:
        # https://www.googleapis.com/compute/v1/projects/project/regions/region
        region_match = re.match(r'.*/regions/(.*)$', config.region)
        load_balancer_target.region = region_match.group(1)
    except (
        resources.WrongResourceCollectionException,
        resources.RequiredFieldOmittedException,
    ):
      # This means the forwarding rule was specified as just a name.
      regions = [
          item.name for item in compute_client.regions.List(
              compute_messages.ComputeRegionsListRequest(project=project)).items
      ]
      configs = []
      for region in regions:
        configs.extend(
            compute_client.forwardingRules.List(
                compute_messages.ComputeForwardingRulesListRequest(
                    filter=('name = %s' % forwarding_rule),
                    project=project,
                    region=region)).items)
      configs.extend(
          compute_client.globalForwardingRules.List(
              compute_messages.ComputeGlobalForwardingRulesListRequest(
                  filter='name = %s' % forwarding_rule, project=project
              )
          ).items
      )
      if not configs:
        raise ForwardingRuleNotFound('The forwarding rule %s was not found.' %
                                     forwarding_rule)
      if len(configs) > 1:
        raise ForwardingRuleNotFound(
            'There are multiple forwarding rules present with the same name '
            'across different regions. Specify the intended region along with '
            'the rule in the format: forwardingrulename@region.'
        )
      config = configs[0]
      if config.region:
        # region returned in the response is the url of the form:
        # https://www.googleapis.com/compute/v1/projects/project/regions/region
        region_match = re.match(r'.*/regions/(.*)$', config.region)
        load_balancer_target.region = region_match.group(1)
  # L4 ILBs will have a backend service and load_balancing_scheme=INTERNAL.
  if (
      config.loadBalancingScheme
      == compute_messages.ForwardingRule.LoadBalancingSchemeValueValuesEnum(
          'INTERNAL'
      )
  ):
    if config.backendService:
      load_balancer_type = 'regionalL4ilb'
    else:
      raise UnsupportedLoadBalancingScheme(
          'Network Passthrough Internal Load Balancers must have a backend'
          ' service.'
      )
  # L7 ILBs will have a HTTPx proxy and load_balancing_scheme=INTERNAL_MANAGED.
  elif (
      config.loadBalancingScheme
      == compute_messages.ForwardingRule.LoadBalancingSchemeValueValuesEnum(
          'INTERNAL_MANAGED'
      )
      and (
          '/targetHttpProxies/' in config.target
          or '/targetHttpsProxies/' in config.target
      )
  ):
    if '/regions/' in config.target:
      load_balancer_type = 'regionalL7ilb'
    else:
      load_balancer_type = 'globalL7ilb'

  load_balancer_target.ipAddress = config.IPAddress
  compute_tcp_enum = compute_messages.ForwardingRule.IPProtocolValueValuesEnum(
      'TCP'
  )
  ip_protocol = 'tcp' if config.IPProtocol == compute_tcp_enum else 'udp'
  load_balancer_target.networkUrl = config.network
  if config.allPorts:
    load_balancer_target.port = '80'  # Any random port
  elif not config.ports:
    load_balancer_target.port = config.portRange.split('-')[0]
  else:
    load_balancer_target.port = config.ports[0]
  if api_version in ['dev', 'v2']:
    load_balancer_type = util.CamelCaseToSnakeCase(load_balancer_type)
    ip_protocol = util.CamelCaseToSnakeCase(ip_protocol)

  load_balancer_target.ipProtocol = dns_messages.RRSetRoutingPolicyLoadBalancerTarget.IpProtocolValueValuesEnum(
      ip_protocol
  )
  if load_balancer_type:
    load_balancer_target.loadBalancerType = dns_messages.RRSetRoutingPolicyLoadBalancerTarget.LoadBalancerTypeValueValuesEnum(
        load_balancer_type
    )
  return load_balancer_target


def GetLoadBalancerConfigFromUrl(
    compute_client, compute_messages, forwarding_rule
):
  """Attempts to fetch the configuration for the given forwarding rule.

  If forwarding_rule is not the self_link for a forwarding rule,
  one of resources.RequiredFieldOmittedException or
  resources.RequiredFieldOmittedException will be thrown, which must be handled
  by the caller.

  Args:
    compute_client: The configured GCE client for this invocation
    compute_messages: The configured GCE API protobufs for this invocation
    forwarding_rule: The (presumed) selfLink for a GCE forwarding rule

  Returns:
    ForwardingRule, the forwarding rule configuration specified by
    forwarding_rule
  """
  try:
    resource = resources.REGISTRY.Parse(
        forwarding_rule, collection='compute.forwardingRules'
    ).AsDict()
    return compute_client.forwardingRules.Get(
        compute_messages.ComputeForwardingRulesGetRequest(
            project=resource['project'],
            region=resource['region'],
            forwardingRule=resource['forwardingRule'],
        )
    )
  except (
      resources.WrongResourceCollectionException,
      resources.RequiredFieldOmittedException,
  ):
    resource = resources.REGISTRY.Parse(
        forwarding_rule, collection='compute.globalForwardingRules'
    ).AsDict()
    return compute_client.globalForwardingRules.Get(
        compute_messages.ComputeGlobalForwardingRulesGetRequest(
            project=resource['project'],
            forwardingRule=resource['forwardingRule'],
        )
    )


def GetHealthCheckSelfLink(health_check: str, project: str):
  """Returns the self link for the given health check."""
  return resources.REGISTRY.Parse(
      health_check,
      collection='compute.healthChecks',
      params={'project': project},
  ).SelfLink()


def IsIPv4(ip: str) -> bool:
  """Returns True if ip is an IPv4."""
  try:
    ipaddr.IPv4Address(ip)
    return True
  except ValueError:
    return False


def IsIPv6(ip: str) -> bool:
  """Returns True if ip is an IPv6."""
  try:
    ipaddr.IPv6Address(ip)
    return True
  except ValueError:
    return False


def SplitItemByDelimiter(
    item: Mapping[str, Any], key: str, delimiter: str
) -> Collection[str]:
  """Splits an item by a delimiter."""
  return (
      item.get(key).split(delimiter)
      if item.get(key)
      else []
  )


def ParseRoutingPolicy(
    args: arg_parsers.ArgDict,
    item: Mapping[str, Any],
    quoted_text: bool,
) -> RoutingPolicyItem:
  """Parses the routing policy from the given args.

  Args:
    args: The arguments to use to parse the routing policy.
    item: The routing policy item to parse.
    quoted_text: [bool], whether to quote the rrdatas.

  Returns:
  RoutingPolicyItem, containing the parsed routing policy.
    item_key: The value of the routing policy.
    rrdatas: The rrdatas for the routing policy.
    health_checked_ips: The health checked ips for the routing policy.
    internal_load_balancers: The internal load balancers for the routing policy
    item.

  Raises:
    EitherWeightOrLocationSpecified: The Routing policy item should have either
      weight or location specified depending on the routing policy type.
    ForwardingRuleWithoutHealthCheck: Forwarding rules specified without
    enabling health check.
    ExternalEndpointsWithoutHealthCheck: External endpoints specified without
    enabling health check.
    HealthCheckOnlyWithExternalEndpoints: The internet health check flag should
    be
      set iff thre are external endpoints.
  """
  routing_policy_type = args.routing_policy_type
  key = ''
  is_routing_policy_item = False
  rrtype_supports_health_checking = args.type == 'A' or args.type == 'AAAA'
  if routing_policy_type == 'WRR':
    key = 'weight'
    is_routing_policy_item = args.IsSpecified('routing_policy_item')
    if is_routing_policy_item and item.get('location') is not None:
      raise EitherWeightOrLocationSpecified(
          'Weighted round robin routing policies should only specify the item'
          ' weight.'
      )
  elif routing_policy_type == 'GEO':
    key = 'location'
    is_routing_policy_item = args.IsSpecified('routing_policy_item')
    if is_routing_policy_item and item.get('weight') is not None:
      raise EitherWeightOrLocationSpecified(
          'Geolocation routing policies should only specify the item location.'
      )
  elif routing_policy_type == 'FAILOVER':
    is_routing_policy_item = args.IsSpecified('routing_policy_backup_item')
    key = 'location'
    # Failover is only valid for A/AAAA
    rrtype_supports_health_checking = True

  if is_routing_policy_item:
    item_key = item.get(key)
    routing_policy_data = ParseRoutingPolicyItem(
        item, rrtype_supports_health_checking
    )
  else:
    item_key = item['key']
    routing_policy_data = ParseRoutingPolicyData(
        item['values'], rrtype_supports_health_checking
    )
  rrdatas = routing_policy_data.rrdatas
  health_checked_ips = routing_policy_data.health_checked_ips
  internal_load_balancers = routing_policy_data.internal_load_balancers
  if quoted_text:
    for i, datum in enumerate(rrdatas):
      rrdatas[i] = import_util.QuotedText(datum)

  # Validate the lists
  # Public Policy
  if health_checked_ips and not args.health_check:
    raise ExternalEndpointsWithoutHealthCheck(
        'Specifying external_endpoints enables health checking. '
        'If this is intended, set --health-check.'
    )

  if (
      hasattr(args, 'health_check')
      and args.health_check
      and internal_load_balancers
  ):
    raise HealthCheckOnlyWithExternalEndpoints(
        '--health-check cannot be specified alongside internal load balancers.'
    )

  # Private Policy
  if internal_load_balancers and not args.enable_health_checking:
    raise ForwardingRuleWithoutHealthCheck(
        'Specifying a forwarding rule enables health checking. '
        'If this is intended, set --enable-health-checking.'
    )

  if args.enable_health_checking and health_checked_ips:
    raise HealthCheckOnlyWithExternalEndpoints(
        'When --enable-health-checking is specified you cannot specify'
        ' health checked ips.'
    )
  return RoutingPolicyItem(
      item_key, routing_policy_data
  )


def ParseRoutingPolicyItem(
    item: Mapping[str, Any], rrtype_supports_health_checking: bool
) -> RoutingPolicyData:
  """Parses the routing policy item from the given item.

  Args:
    item: The routing policy item to parse.
    rrtype_supports_health_checking: [bool], Is the record type A or AAAA.

  Returns:
    rrdatas: The rrdatas for the routing policy item.
    health_checked_ips: The health checked ips for the routing policy item.
    internal_load_balancers: The internal load balancers for the routing policy
    item.
  """
  health_checked_ips = SplitItemByDelimiter(item, 'external_endpoints', ';')
  for ip in health_checked_ips:
    if not IsIpAddress(ip):
      raise arg_parsers.ArgumentTypeError(
          'Each health checked IP should be an IP address.'
      )
  internal_load_balancers = SplitItemByDelimiter(
      item, 'internal_load_balancers', ';'
  )
  for lb in internal_load_balancers:
    if not IsForwardingRule(lb):
      raise arg_parsers.ArgumentTypeError(
          'Each internal load balancer should be in the format of'
          ' forwarding rule name optionally followed by its scope.'
      )

  rrdatas = SplitItemByDelimiter(item, 'rrdatas', ';')
  if not rrtype_supports_health_checking:
    if internal_load_balancers or health_checked_ips:
      raise arg_parsers.ArgumentTypeError(
          'Routing policy items for this record type can only specify rrdatas.'
      )
  else:
    for rdata in rrdatas:
      if not IsIpAddress(rdata):
        raise arg_parsers.ArgumentTypeError(
            'Each rrdata should be an IP address.'
        )
  return RoutingPolicyData(rrdatas, health_checked_ips, internal_load_balancers)


def ParseRoutingPolicyData(
    data: str, rrtype_supports_health_checking: bool
) -> RoutingPolicyData:
  """Parses the routing policy data from the given data.

  Args:
    data: The routing policy data to parse.
    rrtype_supports_health_checking: [bool], Is the record type A or AAAA.
  Returns:
    rrdatas: The rrdatas for the routing policy data.
    health_checked_ips: The health checked ips for the routing policy data.
    Currently empty.
    internal_load_balancers: The internal load balancers for the routing policy
    data.
  """
  rrdatas = []
  internal_load_balancers = []
  for val in data.split(','):
    if IsIpAddress(val):
      rrdatas.append(val)
    elif IsForwardingRule(val):
      internal_load_balancers.append(val)
    # For A/AAAA, we only support IP address or a forwarding rule name.
    elif rrtype_supports_health_checking:
      raise arg_parsers.ArgumentTypeError(
          'Each policy rdata item should either be an IP address or a'
          ' forwarding rule name optionally followed by its scope.'
      )
    else:
      # We merge the rrdatas and internal load balancers later on.
      internal_load_balancers.append(val)
  if not rrtype_supports_health_checking:
    # merge the rrdaras and internal load balancers.
    rrdatas += internal_load_balancers
    internal_load_balancers = []
  # Return empty health_checked_ips for now.
  return RoutingPolicyData(rrdatas, [], internal_load_balancers)


def IsForwardingRule(forwarding_rule: str) -> bool:
  """Returns True if forwarding_rule is a forwarding rule."""
  return len(forwarding_rule.split('@')) == 2 or (
      len(forwarding_rule.split('@')) == 1 and not IsIpAddress(forwarding_rule)
  )


def IsIpAddress(ip: str) -> bool:
  """Returns True if IP is an IPv4 or IPv6."""
  return len(ip.split('@')) == 1 and (IsIPv4(ip) or IsIPv6(ip))


def CreateRecordSetFromArgs(
    args,
    project,
    api_version='v1',
):
  """Creates and returns a record-set from the given args.

  Args:
    args: The arguments to use to create the record-set.
    project: The GCP project where these resources are to be created.
    api_version: [str], the api version to use for creating the RecordSet.
  Raises:
    UnsupportedRecordType: If given record-set type is not supported
    ForwardingRuleWithoutHealthCheck: If forwarding rules are specified without
      enabling health check.
    ForwardingRuleNotFound: Either the forwarding rule doesn't exist, or
      multiple forwarding rules present with the same name - across different
      regions.
    HealthCheckWithoutForwardingRule: Health check enabled but no forwarding
      rules present.
    ExternalEndpointsWithoutHealthCheck: External endpoints specified without
      enabling health check.
    HealthCheckWithoutExternalEndpoints: Health check enabled but no external
      endpoints present.
    EitherWeightOrLocationSpecified: The Routing policy item should have either
      weight or location specified depending on the routing policy type.
    HealthCheckOnlyWithRoutingPolicyItem: The internet health check flag should
    be
      set only with routing policy item and not the routing policy data.
    HealthCheckOnlyWithExternalEndpoints: The internet health check flag should
    be
      set iff thre are external endpoints.
    HealthCheckOnlyForARecordType: The health check flags should be set only for
      A/AAAA record type.

  Returns:
    ResourceRecordSet, the record-set created from the given args.
  """
  messages = apis.GetMessagesModule('dns', api_version)
  if args.type in record_types.CLOUD_DNS_EXTENDED_TYPES:
    # Extended records are internal to Cloud DNS, so don't have wire values.
    rd_type = rdatatype.NONE
  else:
    rd_type = _TryParseRRTypeFromString(args.type)

  record_set = messages.ResourceRecordSet()
  # Need to assign kind to default value for useful equals comparisons.
  record_set.kind = record_set.kind
  record_set.name = util.AppendTrailingDot(args.name)
  record_set.ttl = args.ttl
  record_set.type = args.type
  includes_forwarding_rules = False
  includes_external_endpoints = False

  if args.type != 'A' and args.type != 'AAAA':
    if (hasattr(args, 'health_check') and args.health_check) or (
        hasattr(args, 'enable_health_checking') and args.enable_health_checking
    ):
      raise HealthCheckOnlyForARecordType(
          '--health-check or --enable-health-checking can only be set for'
          ' A/AAAA record type.'
      )

  if args.rrdatas:
    record_set.rrdatas = args.rrdatas
    if rd_type is rdatatype.TXT or rd_type is rdatatype.SPF:
      record_set.rrdatas = [
          import_util.QuotedText(datum) for datum in args.rrdatas
      ]

  elif args.routing_policy_type == 'WRR' or args.routing_policy_type == 'GEO':
    if args.routing_policy_type == 'WRR':
      record_set.routingPolicy = messages.RRSetRoutingPolicy(
          wrr=messages.RRSetRoutingPolicyWrrPolicy(items=[])
      )
    else:
      record_set.routingPolicy = messages.RRSetRoutingPolicy(
          geo=messages.RRSetRoutingPolicyGeoPolicy(items=[])
      )
      if args.enable_geo_fencing:
        record_set.routingPolicy.geo.enableFencing = args.enable_geo_fencing

    if hasattr(args, 'health_check') and args.health_check:
      if args.IsSpecified('routing_policy_data'):
        raise HealthCheckOnlyWithRoutingPolicyItem(
            '--health-check can only be set alongside --routing-policy-item.'
        )
    items = (
        args.routing_policy_item
        if args.IsSpecified('routing_policy_item')
        else args.routing_policy_data
    )
    for item in items:
      parsed_routing_policy = ParseRoutingPolicy(
          args,
          item,
          rd_type is rdatatype.TXT or rd_type is rdatatype.SPF,
      )
      val = parsed_routing_policy.item_key
      rrdatas = parsed_routing_policy.routing_policy_data.rrdatas
      health_checked_ips = (
          parsed_routing_policy.routing_policy_data.health_checked_ips
      )
      internal_load_balancers = (
          parsed_routing_policy.routing_policy_data.internal_load_balancers
      )
      if internal_load_balancers:
        # At least one forwarding rule is specified
        includes_forwarding_rules = True
      if health_checked_ips:
        # At least one external endpoint is specified
        includes_external_endpoints = True
      targets = [
          GetLoadBalancerTarget(config, api_version, project)
          for config in internal_load_balancers
      ]
      health_checked_targets = messages.RRSetRoutingPolicyHealthCheckTargets()
      if targets:
        health_checked_targets.internalLoadBalancers = targets
      if health_checked_ips:
        health_checked_targets.externalEndpoints = health_checked_ips

      if args.routing_policy_type == 'WRR':
        record_set.routingPolicy.wrr.items.append(
            messages.RRSetRoutingPolicyWrrPolicyWrrPolicyItem(
                weight=float(val),
                rrdatas=rrdatas,
                healthCheckedTargets=health_checked_targets,
            )
        )
      else:
        record_set.routingPolicy.geo.items.append(
            messages.RRSetRoutingPolicyGeoPolicyGeoPolicyItem(
                location=val,
                rrdatas=rrdatas,
                healthCheckedTargets=health_checked_targets,
            )
        )

  elif args.routing_policy_type == 'FAILOVER':
    if not args.enable_health_checking and not args.health_check:
      raise ForwardingRuleWithoutHealthCheck(
          'Failover policy needs to have health checking enabled. '
          'Set --enable-health-checking or --health-check.'
      )
    record_set.routingPolicy = messages.RRSetRoutingPolicy(
        primaryBackup=messages.RRSetRoutingPolicyPrimaryBackupPolicy(
            primaryTargets=messages.RRSetRoutingPolicyHealthCheckTargets(),
            backupGeoTargets=messages.RRSetRoutingPolicyGeoPolicy(items=[]),
        )
    )
    if args.backup_data_trickle_ratio:
      record_set.routingPolicy.primaryBackup.trickleTraffic = (
          args.backup_data_trickle_ratio
      )
    if hasattr(args, 'health_check') and args.health_check:
      if args.IsSpecified('routing_policy_backup_data'):
        raise HealthCheckOnlyWithRoutingPolicyItem(
            '--health-check can only be set alongside'
            ' --routing-policy-backup-item.'
        )
      for ip_address in args.routing_policy_primary_data:
        if IsIpAddress(ip_address):
          record_set.routingPolicy.primaryBackup.primaryTargets.externalEndpoints.append(
              ip_address
          )
        else:
          raise arg_parsers.ArgumentTypeError(
              'The primary data should be a list of IP addresses.'
          )
        includes_external_endpoints = True
    elif args.enable_health_checking:
      for target in args.routing_policy_primary_data:
        if IsForwardingRule(target):
          record_set.routingPolicy.primaryBackup.primaryTargets.internalLoadBalancers.append(
              GetLoadBalancerTarget(target, api_version, project)
          )
        else:
          raise arg_parsers.ArgumentTypeError(
              'The primary data should be a list of forwarding rules.'
          )
        includes_forwarding_rules = True
    if args.routing_policy_backup_data_type == 'GEO':
      if args.enable_geo_fencing:
        record_set.routingPolicy.primaryBackup.backupGeoTargets.enableFencing = (
            args.enable_geo_fencing
        )
      items = (
          args.routing_policy_backup_item
          if args.IsSpecified('routing_policy_backup_item')
          else args.routing_policy_backup_data
      )
      for item in items:
        parsed_routing_policy = ParseRoutingPolicy(
            args,
            item,
            False,
        )
        val = parsed_routing_policy.item_key
        rrdatas = parsed_routing_policy.routing_policy_data.rrdatas
        health_checked_ips = (
            parsed_routing_policy.routing_policy_data.health_checked_ips
        )
        internal_load_balancers = (
            parsed_routing_policy.routing_policy_data.internal_load_balancers
        )
        targets = [
            GetLoadBalancerTarget(config, api_version, project)
            for config in internal_load_balancers
        ]
        health_checked_targets = messages.RRSetRoutingPolicyHealthCheckTargets()
        if targets:
          health_checked_targets.internalLoadBalancers = targets
        if health_checked_ips:
          health_checked_targets.externalEndpoints = health_checked_ips
        record_set.routingPolicy.primaryBackup.backupGeoTargets.items.append(
            messages.RRSetRoutingPolicyGeoPolicyGeoPolicyItem(
                location=val,
                rrdatas=rrdatas,
                healthCheckedTargets=health_checked_targets,
            )
        )
  if hasattr(args, 'health_check') and args.health_check:
    record_set.routingPolicy.healthCheck = GetHealthCheckSelfLink(
        args.health_check, project
    )
  if (
      not includes_forwarding_rules
      and hasattr(args, 'enable_health_checking')
      and args.enable_health_checking
  ):
    raise HealthCheckWithoutForwardingRule(
        '--enable-health-check is set, but no forwarding rules are provided. '
        'Either remove the --enable-health-check flag, or provide the '
        'forwarding rule names instead of IP addresses for the rules to be '
        'health checked.'
    )
  if (
      not includes_external_endpoints
      and hasattr(args, 'health_check')
      and args.health_check
  ):
    raise HealthCheckWithoutExternalEndpoints(
        '--health-check is set, but no external endpoints are provided. '
        'Either remove the --health-check flag, or provide the '
        'external endpoints to be health checked.'
    )
  return record_set
