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
              support_rate_limit=False,
              support_tcp_ssl=False):
  """Adds the action argument to the argparse."""
  actions = {
      'allow': 'Allows the request from HTTP(S) Load Balancing.',
      'deny-403':
          'Denies the request from HTTP(S) Load Balancing, with an HTTP '
          'response status code of 403.',
      'deny-404':
          'Denies the request from HTTP(S) Load Balancing, with an HTTP '
          'response status code of 404.',
      'deny-502':
          'Denies the request from HTTP(S) Load Balancing, with an HTTP '
          'response status code of 503.',
      'redirect-to-recaptcha':
          '(DEPRECATED) Redirects the request from HTTP(S) Load Balancing, for'
          ' reCAPTCHA Enterprise assessment. This flag choice is deprecated. '
          'Use --action=redirect and --redirect-type=google-recaptcha instead.'
  }
  if support_redirect:
    actions.update({
        'redirect':
            'Redirects the request from HTTP(S) Load Balancing, based on redirect options.'
    })
  if support_rate_limit:
    actions.update({
        'rate-based-ban':
            'Enforces rate-based ban action from HTTP(S) Load Balancing, based on rate limit options.',
        'throttle':
            'Enforces throttle action from HTTP(S) Load Balancing, based on rate limit options.'
    })
  if support_tcp_ssl:
    actions.update(
        {'deny': 'Denies the request from TCP/SSL Proxy Load Balancing.'})
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


def AddRedirectOptions(parser):
  """Adds redirect action related argument to the argparse."""
  redirect_type = ['google-recaptcha', 'external-302']
  parser.add_argument(
      '--redirect-type',
      choices=redirect_type,
      type=lambda x: x.lower(),
      help="""\
      Type for the redirect action. Default to ``external-302'' if unspecified
      while --redirect-target is given.
      """)

  parser.add_argument(
      '--redirect-target',
      help="""\
      URL target for the redirect action. Must be specified if the redirect
      type is ``external-302''. Cannot be specified if the redirect type is
      ``google-recaptcha''.
      """)


def AddRateLimitOptions(parser,
                        support_tcp_ssl=False,
                        support_exceed_redirect=True):
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
  if support_tcp_ssl:
    exceed_actions.append('deny')
  if support_exceed_redirect:
    exceed_actions.append('redirect')
  parser.add_argument(
      '--exceed-action',
      choices=exceed_actions,
      type=lambda x: x.lower(),
      help="""\
      Action to take when requests are above the given threshold. When a request
      is denied, return the specified HTTP response code. When a request is
      redirected, use the redirect options based on --exceed-redirect-type and
      --exceed-redirect-target below.
      """)

  if support_exceed_redirect:
    exceed_redirect_types = ['google-recaptcha', 'external-302']
    parser.add_argument(
        '--exceed-redirect-type',
        choices=exceed_redirect_types,
        type=lambda x: x.lower(),
        help="""\
        Type for the redirect action that is configured as the exceed action.
        """)
    parser.add_argument(
        '--exceed-redirect-target',
        help="""\
        URL target for the redirect action that is configured as the exceed
        action when the redirect type is ``external-302''.
        """)

  enforce_on_key = ['ip', 'all', 'http-header', 'xff-ip', 'http-cookie']
  parser.add_argument(
      '--enforce-on-key',
      choices=enforce_on_key,
      type=lambda x: x.lower(),
      help="""\
      Different key types available to enforce the rate limit threshold limit on:
      - ``ip'': each client IP address has this limit enforced separately
      - ``all'': a single limit is applied to all requests matching this rule
      - ``http-header'': key type takes the value of the HTTP header configured
                         in enforce-on-key-name as the key value
      - ``xff-ip'': takes the original IP address specified in the X-Forwarded-For
                    header as the key
      - ``http-cookie'': key type takes the value of the HTTP cookie configured
                         in enforce-on-key-name as the key value
      """)

  parser.add_argument(
      '--enforce-on-key-name',
      help="""\
      Determines the key name for the rate limit key. Applicable only for the
      following rate limit key types:
      - http-header: The name of the HTTP header whose value is taken as the key
      value.
      - http-cookie: The name of the HTTP cookie whose value is taken as the key
      value.
      """)

  parser.add_argument(
      '--ban-threshold-count',
      type=int,
      help="""\
      Number of HTTP(S) requests for calculating the threshold for
      banning requests. Can only be specified if the action for the
      rule is ``rate-based-ban''. If specified, the key will be banned
      for the configured ``BAN_DURATION_SEC'' when the number of requests
      that exceed the ``RATE_LIMIT_THRESHOLD_COUNT'' also exceed this
      ``BAN_THRESHOLD_COUNT''.
      """)

  parser.add_argument(
      '--ban-threshold-interval-sec',
      type=int,
      help="""\
      Interval over which the threshold for banning requests is
      computed. Can only be specified if the action for the rule is
      ``rate-based-ban''. If specified, the key will be banned for the
      configured ``BAN_DURATION_SEC'' when the number of requests that
      exceed the ``RATE_LIMIT_THRESHOLD_COUNT'' also exceed this
      ``BAN_THRESHOLD_COUNT''.
      """)

  parser.add_argument(
      '--ban-duration-sec',
      type=int,
      help="""\
      Can only be specified if the action for the rule is
      ``rate-based-ban''. If specified, determines the time (in seconds)
      the traffic will continue to be banned by the rate limit after
      the rate falls below the threshold.
      """)


def AddRequestHeadersToAdd(parser):
  """Adds request-headers-to-add argument to the argparse."""
  parser.add_argument(
      '--request-headers-to-add',
      metavar='REQUEST_HEADERS_TO_ADD',
      type=arg_parsers.ArgDict(),
      help="""\
      A comma-separated list of header names and header values to add to
      requests that match this rule.
      """)
