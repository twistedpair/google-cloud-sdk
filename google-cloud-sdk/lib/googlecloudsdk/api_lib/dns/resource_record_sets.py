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

from dns import rdatatype
from googlecloudsdk.api_lib.dns import import_util
from googlecloudsdk.api_lib.dns import record_types
from googlecloudsdk.api_lib.dns import util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources


class UnsupportedRecordType(exceptions.Error):
  """Unsupported record-set type."""


class ForwardingRuleWithoutHealthCheck(exceptions.Error):
  """Forwarding rules specified without enabling health check."""


class HealthCheckWithoutForwardingRule(exceptions.Error):
  """Health check enabled but no forwarding rules present."""


class ForwardingRuleNotFound(exceptions.Error):
  """Either the forwarding rule doesn't exist, or multiple forwarding rules present with the same name - across different regions."""


class UnsupportedLoadBalancingScheme(exceptions.Error):
  """Unsupported load balancing scheme."""


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
  load_balancer_target.loadBalancerType = dns_messages.RRSetRoutingPolicyLoadBalancerTarget.LoadBalancerTypeValueValuesEnum(
      'regionalL4ilb')
  config = None
  if len(forwarding_rule.split('@')) == 2:
    name, scope = forwarding_rule.split('@')
    load_balancer_target.region = scope
    config = compute_client.forwardingRules.Get(
        compute_messages.ComputeForwardingRulesGetRequest(
            project=project, forwardingRule=name, region=scope))
    if config is None:
      raise ForwardingRuleNotFound(
          "Either the forwarding rule doesn't exist, or multiple forwarding rules present with the same name - across different regions."
      )
  else:
    try:
      resource = resources.REGISTRY.Parse(
          forwarding_rule, collection='compute.forwardingRules'
      ).AsDict()
      load_balancer_target.region = resource['region']
      config = compute_client.forwardingRules.Get(
          compute_messages.ComputeForwardingRulesGetRequest(
              project=resource['project'],
              region=resource['region'],
              forwardingRule=resource['forwardingRule'],
          )
      )
    except resources.RequiredFieldOmittedException:
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
      region_url_split = config.region.split('/')
      # region returned in the response is the url of the form:
      # https://www.googleapis.com/compute/v1/projects/project/regions/region
      load_balancer_target.region = region_url_split[
          region_url_split.index('regions') + 1]
  # L4 ILB forwarding rules will specify loadBalancingScheme=INTERNAL and a
  # backend service. We check for backendService to filter out L7ILBs that
  # specify loadBalancingScheme=INTERNAL and a target.
  if config.loadBalancingScheme != compute_messages.ForwardingRule.LoadBalancingSchemeValueValuesEnum(
      'INTERNAL') or not config.backendService:
    raise UnsupportedLoadBalancingScheme(
        'Only Regional L4 forwarding rules are supported at this time.')
  load_balancer_target.ipAddress = config.IPAddress
  if config.IPProtocol == compute_messages.ForwardingRule.IPProtocolValueValuesEnum(
      'TCP'):
    load_balancer_target.ipProtocol = dns_messages.RRSetRoutingPolicyLoadBalancerTarget.IpProtocolValueValuesEnum(
        'tcp')
  else:
    load_balancer_target.ipProtocol = dns_messages.RRSetRoutingPolicyLoadBalancerTarget.IpProtocolValueValuesEnum(
        'udp')
  load_balancer_target.project = project
  load_balancer_target.networkUrl = config.network
  if config.allPorts:
    load_balancer_target.port = '80'  # Any random port
  elif not config.ports:
    load_balancer_target.port = config.portRange.split('-')[0]
  else:
    load_balancer_target.port = config.ports[0]
  return load_balancer_target


def CreateRecordSetFromArgs(args,
                            project,
                            api_version='v1',
                            allow_extended_records=False):
  """Creates and returns a record-set from the given args.

  Args:
    args: The arguments to use to create the record-set.
    project: The GCP project where these resources are to be created.
    api_version: [str], the api version to use for creating the RecordSet.
    allow_extended_records: [bool], enables extended records if true, otherwise
      throws an exception when given an extended record type.

  Raises:
    UnsupportedRecordType: If given record-set type is not supported
    ForwardingRuleWithoutHealthCheck: If forwarding rules are specified without
      enabling health check.
    ForwardingRuleNotFound: Either the forwarding rule doesn't exist, or
      multiple forwarding rules present with the same name - across different
      regions.
    HealthCheckWithoutForwardingRule: Health check enabled but no forwarding
      rules present.

  Returns:
    ResourceRecordSet, the record-set created from the given args.
  """
  messages = apis.GetMessagesModule('dns', api_version)
  if allow_extended_records:
    if args.type in record_types.CLOUD_DNS_EXTENDED_TYPES:
      # Extended records are internal to Cloud DNS, so don't have wire values.
      rd_type = rdatatype.NONE
    else:
      rd_type = _TryParseRRTypeFromString(args.type)
  else:
    rd_type = _TryParseRRTypeFromString(args.type)

  record_set = messages.ResourceRecordSet()
  # Need to assign kind to default value for useful equals comparisons.
  record_set.kind = record_set.kind
  record_set.name = util.AppendTrailingDot(args.name)
  record_set.ttl = args.ttl
  record_set.type = args.type
  includes_forwarding_rules = False

  if args.rrdatas:
    record_set.rrdatas = args.rrdatas
    if rd_type is rdatatype.TXT or rd_type is rdatatype.SPF:
      record_set.rrdatas = [
          import_util.QuotedText(datum) for datum in args.rrdatas
      ]

  elif args.routing_policy_type == 'WRR':
    record_set.routingPolicy = messages.RRSetRoutingPolicy(
        wrr=messages.RRSetRoutingPolicyWrrPolicy(items=[]))
    for policy_item in args.routing_policy_data:
      if args.type != 'A':
        # Forwarding configs only make sense for A record types. For other
        # types, there's only one type of records, so merge the two.
        policy_item['rrdatas'] += policy_item['forwarding_configs']
        policy_item['forwarding_configs'] = []
      if rd_type is rdatatype.TXT or rd_type is rdatatype.SPF:
        policy_item['rrdatas'] = [
            import_util.QuotedText(datum) for datum in policy_item['rrdatas']
        ]
      if len(policy_item['forwarding_configs']
            ) and not args.enable_health_checking:
        raise ForwardingRuleWithoutHealthCheck(
            'Specifying a forwarding rule enables health checking. If this is intended, set --enable-health-checking.'
        )
      if policy_item['forwarding_configs']:
        includes_forwarding_rules = True
      targets = [
          GetLoadBalancerTarget(config, api_version, project)
          for config in policy_item['forwarding_configs']
      ]
      if targets:
        record_set.routingPolicy.wrr.items.append(
            messages.RRSetRoutingPolicyWrrPolicyWrrPolicyItem(
                weight=float(policy_item['key']),
                rrdatas=policy_item['rrdatas'],
                healthCheckedTargets=messages
                .RRSetRoutingPolicyHealthCheckTargets(
                    internalLoadBalancers=targets)))
      else:
        record_set.routingPolicy.wrr.items.append(
            messages.RRSetRoutingPolicyWrrPolicyWrrPolicyItem(
                weight=float(policy_item['key']),
                rrdatas=policy_item['rrdatas']))

  elif args.routing_policy_type == 'GEO':
    record_set.routingPolicy = messages.RRSetRoutingPolicy(
        geo=messages.RRSetRoutingPolicyGeoPolicy(items=[]))
    if args.enable_geo_fencing:
      record_set.routingPolicy.geo.enableFencing = args.enable_geo_fencing
    for policy_item in args.routing_policy_data:
      if args.type != 'A':
        # Forwarding configs only make sense for A record types. For other
        # types, there's only one type of records, so merge the two.
        policy_item['rrdatas'] += policy_item['forwarding_configs']
        policy_item['forwarding_configs'] = []
      if rd_type is rdatatype.TXT or rd_type is rdatatype.SPF:
        policy_item['rrdatas'] = [
            import_util.QuotedText(datum) for datum in policy_item['rrdatas']
        ]
      if len(policy_item['forwarding_configs']
            ) and not args.enable_health_checking:
        raise ForwardingRuleWithoutHealthCheck(
            'Specifying a forwarding rule enables health checking. If this is intended, set --enable-health-checking.'
        )
      if policy_item['forwarding_configs']:
        includes_forwarding_rules = True
      targets = [
          GetLoadBalancerTarget(config, api_version, project)
          for config in policy_item['forwarding_configs']
      ]
      if targets:
        record_set.routingPolicy.geo.items.append(
            messages.RRSetRoutingPolicyGeoPolicyGeoPolicyItem(
                location=policy_item['key'],
                rrdatas=policy_item['rrdatas'],
                healthCheckedTargets=messages
                .RRSetRoutingPolicyHealthCheckTargets(
                    internalLoadBalancers=targets)))
      else:
        record_set.routingPolicy.geo.items.append(
            messages.RRSetRoutingPolicyGeoPolicyGeoPolicyItem(
                location=policy_item['key'], rrdatas=policy_item['rrdatas']))
  elif args.routing_policy_type == 'FAILOVER':
    if not args.enable_health_checking:
      raise ForwardingRuleWithoutHealthCheck(
          'Failover policy needs to have health checking enabled. Set --enable-health-checking.'
      )
    includes_forwarding_rules = True
    record_set.routingPolicy = messages.RRSetRoutingPolicy(
        primaryBackup=messages.RRSetRoutingPolicyPrimaryBackupPolicy(
            primaryTargets=messages.RRSetRoutingPolicyHealthCheckTargets(
                internalLoadBalancers=[]),
            backupGeoTargets=messages.RRSetRoutingPolicyGeoPolicy(items=[])))
    if args.backup_data_trickle_ratio:
      record_set.routingPolicy.primaryBackup.trickleTraffic = args.backup_data_trickle_ratio
    for target in args.routing_policy_primary_data:
      record_set.routingPolicy.primaryBackup.primaryTargets.internalLoadBalancers.append(
          GetLoadBalancerTarget(target, api_version, project))
    if args.routing_policy_backup_data_type == 'GEO':
      if args.enable_geo_fencing:
        record_set.routingPolicy.primaryBackup.backupGeoTargets.enableFencing = args.enable_geo_fencing
      for policy_item in args.routing_policy_backup_data:
        targets = [
            GetLoadBalancerTarget(config, api_version, project)
            for config in policy_item['forwarding_configs']
        ]
        if targets:
          record_set.routingPolicy.primaryBackup.backupGeoTargets.items.append(
              messages.RRSetRoutingPolicyGeoPolicyGeoPolicyItem(
                  location=policy_item['key'],
                  rrdatas=policy_item['rrdatas'],
                  healthCheckedTargets=messages
                  .RRSetRoutingPolicyHealthCheckTargets(
                      internalLoadBalancers=targets)))
        else:
          record_set.routingPolicy.primaryBackup.backupGeoTargets.items.append(
              messages.RRSetRoutingPolicyGeoPolicyGeoPolicyItem(
                  location=policy_item['key'], rrdatas=policy_item['rrdatas']))
  if not includes_forwarding_rules and hasattr(
      args, 'enable_health_checking') and args.enable_health_checking:
    raise HealthCheckWithoutForwardingRule(
        '--enable-health-check is set, but no forwarding rules are provided. '
        'Either remove the --enable-health-check flag, or provide the forwarding '
        'rule names instead of ip addresses for the rules to be health checked.'
    )
  return record_set
