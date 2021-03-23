# -*- coding: utf-8 -*- #
# Copyright 2017 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the compute security policies rules commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import completers as compute_completers


class SecurityPolicyRulesCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(SecurityPolicyRulesCompleter, self).__init__(
        collection='compute.securityPolicyRules', **kwargs)


def AddPriority(parser, operation, is_plural=False):
  """Adds the priority argument to the argparse."""
  parser.add_argument(
      'name' + ('s' if is_plural else ''),
      metavar='PRIORITY',
      nargs='*' if is_plural else None,
      completer=SecurityPolicyRulesCompleter,
      help=('The priority of the rule{0} to {1}. Rules are evaluated in order '
            'from highest priority to lowest priority where 0 is the highest '
            'priority and 2147483647 is the lowest priority.'.format(
                's' if is_plural else '', operation)))


def AddMatcher(parser, required=True):
  """Adds the matcher arguments to the argparse."""
  matcher = parser.add_group(
      mutex=True, required=required, help='Security policy rule matcher.')
  matcher.add_argument(
      '--src-ip-ranges',
      type=arg_parsers.ArgList(),
      metavar='SRC_IP_RANGE',
      help=('The source IPs/IP ranges to match for this rule. '
            'To match all IPs specify *.'))
  matcher.add_argument(
      '--expression',
      help='The Cloud Armor rules language expression to match for this rule.')


def AddAction(parser,
              required=True,
              support_redirect=False,
              support_rate_limit=False):
  """Adds the action argument to the argparse."""
  actions = [
      'allow', 'deny-403', 'deny-404', 'deny-502', 'redirect-to-recaptcha'
  ]
  if support_redirect:
    actions.append('redirect')
  if support_rate_limit:
    actions.extend(['rate-based-ban', 'throttle'])
  parser.add_argument(
      '--action',
      choices=actions,
      type=lambda x: x.lower(),
      required=required,
      help='The action to take if the request matches the match condition.')


def AddDescription(parser):
  """Adds the preview argument to the argparse."""
  parser.add_argument(
      '--description', help='An optional, textual description for the rule.')


def AddPreview(parser, default):
  """Adds the preview argument to the argparse."""
  parser.add_argument(
      '--preview',
      action='store_true',
      default=default,
      help='If specified, the action will not be enforced.')


def AddRedirectTarget(parser):
  """Adds redirect-target argument to the argparse."""
  parser.add_argument(
      '--redirect-target',
      help=('The URL to which traffic is routed when the rule action is set to'
            ' "redirect".'))


def AddRateLimitOptions(parser):
  """Adds rate limiting related arguments to the argparse."""
  parser.add_argument(
      '--rate-limit-threshold-count',
      type=int,
      help=('Number of HTTP(S) requests for calculating the threshold for rate '
            'limiting requests.'))

  parser.add_argument(
      '--rate-limit-threshold-interval-sec',
      type=int,
      help=('Interval over which the threshold for rate limiting requests is '
            'computed.'))

  conform_actions = ['allow']
  parser.add_argument(
      '--conform-action',
      choices=conform_actions,
      type=lambda x: x.lower(),
      help=('Action to take when requests are under the given threshold. When '
            'requests are throttled, this is also the action for all requests '
            'which are not dropped.'))

  exceed_actions = ['deny-403', 'deny-404', 'deny-429', 'deny-502']
  parser.add_argument(
      '--exceed-action',
      choices=exceed_actions,
      type=lambda x: x.lower(),
      help=('When a request is denied, returns the HTTP response code '
            'specified.'))

  enforce_on_key = ['ip', 'all-ips']
  parser.add_argument(
      '--enforce-on-key',
      choices=enforce_on_key,
      type=lambda x: x.lower(),
      help=('Determines the key to enforce the threshold_rps limit on. If key '
            'is ``ip", each IP has this limit enforced separately, whereas '
            '``all-ips" means a single limit is applied to all requests '
            'matching this rule.'))

  parser.add_argument(
      '--ban-threshold-count',
      type=int,
      help=('Number of HTTP(S) requests for calculating the threshold for '
            'banning requests. Can only be specified if the action for the '
            'rule is ``rate_based_ban". If specified, the key will be banned '
            'for the configured ``banDurationSec" when the number of requests '
            'that exceed the ``rateLimitThreshold" also exceed this '
            '``banThreshold".'))

  parser.add_argument(
      '--ban-threshold-interval-sec',
      type=int,
      help=('Interval over which the threshold for banning requests is '
            'computed. Can only be specified if the action for the rule is '
            '``rate_based_ban". If specified, the key will be banned for the '
            'configured ``banDurationSec" when the number of requests that '
            'exceed the ``rateLimitThreshold" also exceed this '
            '``banThreshold".'))

  parser.add_argument(
      '--ban-duration-sec',
      type=int,
      help=('Can only be specified if the action for the rule is '
            '``rate_based_ban". If specified, determines the time (in seconds) '
            'the traffic will continue to be banned by the rate limit after '
            'the rate falls below the threshold.'))


def AddRequestHeadersToAdd(parser):
  """Adds request-headers-to-add argument to the argparse."""
  parser.add_argument(
      '--request-headers-to-add',
      metavar='REQUEST_HEADERS_TO_ADD',
      type=arg_parsers.ArgDict(),
      help=('A dict of headers names and values to add to requests that match '
            'this rule.'))
