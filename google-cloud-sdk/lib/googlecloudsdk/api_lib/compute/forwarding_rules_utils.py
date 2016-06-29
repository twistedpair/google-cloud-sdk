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
"""Common classes and functions for forwarding rules."""
import abc
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import exceptions


class ForwardingRulesMutator(base_classes.BaseAsyncMutator):
  """Base class for modifying forwarding rules."""

  @property
  def service(self):
    if self.global_request:
      return self.compute.globalForwardingRules
    else:
      return self.compute.forwardingRules

  @property
  def resource_type(self):
    return 'forwardingRules'

  @abc.abstractmethod
  def CreateGlobalRequests(self, args):
    """Return a list of one of more globally-scoped request."""

  @abc.abstractmethod
  def CreateRegionalRequests(self, args):
    """Return a list of one of more regionally-scoped request."""

  def CreateRequests(self, args):
    self.global_request = getattr(args, 'global')

    if self.global_request:
      return self.CreateGlobalRequests(args)
    else:
      return self.CreateRegionalRequests(args)


class ForwardingRulesTargetMutator(ForwardingRulesMutator):
  """Base class for modifying forwarding rule targets."""

  def GetGlobalTarget(self, args):
    """Return the forwarding target for a globally scoped request."""

    if args.target_instance:
      raise exceptions.ToolException(
          'You cannot specify [--target-instance] for a global '
          'forwarding rule.')
    if args.target_pool:
      raise exceptions.ToolException(
          'You cannot specify [--target-pool] for a global '
          'forwarding rule.')

    if getattr(args, 'backend_service', None):
      raise exceptions.ToolException(
          'You cannot specify [--backend-service] for a global '
          'forwarding rule.')

    if getattr(args, 'load_balancing_scheme', None) == 'INTERNAL':
      raise exceptions.ToolException(
          'You cannot specify internal [--load-balancing-scheme] for a global '
          'forwarding rule.')

    if args.target_http_proxy:
      return self.CreateGlobalReference(
          args.target_http_proxy, resource_type='targetHttpProxies')

    if args.target_https_proxy:
      return self.CreateGlobalReference(
          args.target_https_proxy, resource_type='targetHttpsProxies')

    if getattr(args, 'target_vpn_gateway', None):
      raise exceptions.ToolException(
          'You cannot specify [--target-vpn-gateway] for a global '
          'forwarding rule.')

  def GetRegionalTarget(self, args, forwarding_rule_ref=None):
    """Return the forwarding target for a regionally scoped request."""
    if args.target_http_proxy:
      raise exceptions.ToolException(
          'You cannot specify [--target-http-proxy] for a regional '
          'forwarding rule.')
    if getattr(args, 'target_https_proxy', None):
      raise exceptions.ToolException(
          'You cannot specify [--target-https-proxy] for a regional '
          'forwarding rule.')
    if getattr(args, 'target_ssl_proxy', None):
      raise exceptions.ToolException(
          'You cannot specify [--target-ssl-proxy] for a regional '
          'forwarding rule.')
    if args.target_instance_zone and not args.target_instance:
      raise exceptions.ToolException(
          'You cannot specify [--target-instance-zone] unless you are '
          'specifying [--target-instance].')

    if getattr(args, 'load_balancing_scheme', None) == 'INTERNAL':
      if getattr(args, 'port_range', None):
        raise exceptions.ToolException(
            'You cannot specify [--port-range] for a forwarding rule '
            'whose [--load-balancing-scheme] is internal, '
            'please use [--ports] flag instead.')
    elif getattr(args, 'subnet', None) or getattr(args, 'network', None):
      raise exceptions.ToolException(
          'You cannot specify [--subnet] or [--network] for non-internal '
          '[--load-balancing-scheme] forwarding rule.')

    if forwarding_rule_ref:
      region_arg = forwarding_rule_ref.region
    else:
      region_arg = args.region

    if args.target_pool:
      target_ref = self.CreateRegionalReference(
          args.target_pool, region_arg, resource_type='targetPools')
      target_region = target_ref.region
    elif args.target_instance:
      target_ref = self.CreateZonalReference(
          args.target_instance, args.target_instance_zone,
          resource_type='targetInstances',
          flag_names=['--target-instance-zone'],
          region_filter=region_arg)
      target_region = utils.ZoneNameToRegionName(target_ref.zone)
    elif getattr(args, 'target_vpn_gateway', None):
      target_ref = self.CreateRegionalReference(
          args.target_vpn_gateway, region_arg,
          resource_type='targetVpnGateways')
      target_region = target_ref.region
    elif getattr(args, 'backend_service', None):
      target_ref = self.CreateRegionalReference(
          args.backend_service, region_arg,
          resource_type='regionBackendServices')
      target_region = target_ref.region

    return target_ref, target_region
