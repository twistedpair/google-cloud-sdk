# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Common flags for workforce pools commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


def AddParentFlags(parser, verb):
  parser.add_argument(
      '--organization',
      help='The parent organization of the workforce pool{0} to {1}.'.format(
          's' if verb == 'list' else '', verb),
      required=True)


def AddLocationFlag(parser, verb):
  parser.add_argument(
      '--location',
      help='The location of the workforce pool{0} to {1}.'.format(
          's' if verb == 'list' else '', verb),
      required=True)


def ParseLocation(args):
  if not args.IsSpecified('location'):
    return 'locations/global'
  return 'locations/{}'.format(args.location)


# Adding this flag as a ArgList to hide `code` and
# `merge-user-info-over-id-token-claims` choices from the end user. Currently
# there is no other way to hide new enum choices. These flags will move back
# to enum types once feature is ready for launch
def AddWebSsoFlag():
  return [
      base.Argument(
          '--web-sso-response-type',
          dest='web_sso_response_type',
          type=arg_parsers.ArgList(
              choices=[
                  'id-token',
                  'code',
              ],
              visible_choices=['id-token'],
              max_length=1,
              min_length=1
          ),
          metavar='WEB_SSO_RESPONSE_TYPE',
          help=(
              'Response Type to request for in the OIDC Authorization'
              ' Request for'
              ' web sign-in. Use `id-token` to select the [implicit'
              ' flow](https://openid.net/specs/openid-connect-core-1_0.html#ImplicitFlowAuth).'
          ),
      ),
      base.Argument(
          '--web-sso-assertion-claims-behavior',
          dest='web_sso_assertion_claims_behavior',
          type=arg_parsers.ArgList(
              choices=[
                  'only-id-token-claims',
                  'merge-user-info-over-id-token-claims',
              ],
              visible_choices=['only-id-token-claims'],
              max_length=1,
              min_length=1
          ),
          metavar='WEB_SSO_ASSERTION_CLAIMS_BEHAVIOR',
          help=(
              'The behavior for how OIDC Claims are included in the `assertion`'
              ' object used for attribute mapping and attribute condition. Use'
              ' `only-id-token-claims` to include only ID token claims.'
          ),
      )
  ]
