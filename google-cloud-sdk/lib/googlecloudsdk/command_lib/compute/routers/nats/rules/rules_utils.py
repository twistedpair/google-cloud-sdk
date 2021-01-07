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
"""Util functions for NAT commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.compute.routers.nats.rules import flags
from googlecloudsdk.core import exceptions as core_exceptions
import six


def CreateRuleMessage(args, compute_holder):
  """Creates a Rule message from the specified arguments."""
  active_ips = [
      six.text_type(ip) for ip in flags.ACTIVE_IPS_ARG_CREATE.ResolveAsResource(
          args, compute_holder.resources)
  ]
  return compute_holder.client.messages.RouterNatRule(
      ruleNumber=args.rule_number,
      match=args.match,
      action=compute_holder.client.messages.RouterNatRuleAction(
          sourceNatActiveIps=active_ips))


class RuleNotFoundError(core_exceptions.Error):
  """Raised when a Rule is not found."""

  def __init__(self, rule_number):
    msg = 'Rule `{0}` not found'.format(rule_number)
    super(RuleNotFoundError, self).__init__(msg)


def FindRuleOrRaise(nat, rule_number):
  """Returns the Rule with the given rule_number in the given NAT."""
  for rule in nat.rules:
    if rule.ruleNumber == rule_number:
      return rule
  raise RuleNotFoundError(rule_number)


def UpdateRuleMessage(rule, args, compute_holder):
  """Updates a Rule message from the specified arguments."""
  if args.match:
    rule.match = args.match
  if args.source_nat_active_ips:
    rule.action.sourceNatActiveIps = [
        six.text_type(ip)
        for ip in flags.ACTIVE_IPS_ARG_UPDATE.ResolveAsResource(
            args, compute_holder.resources)
    ]
  if args.source_nat_drain_ips:
    rule.action.sourceNatDrainIps = [
        six.text_type(ip) for ip in flags.DRAIN_IPS_ARG.ResolveAsResource(
            args, compute_holder.resources)
    ]
  elif args.clear_source_nat_drain_ips:
    rule.action.sourceNatDrainIps = []
