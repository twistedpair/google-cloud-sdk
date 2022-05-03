# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Flags and helpers for Immersive Stream for XR commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.immersive_stream.xr import api_util
from googlecloudsdk.calliope import arg_parsers

_REALM_CONFIG_ARG_HELP_TEXT = """\
  Flag used to specify realm and capacity required for the service instance's availability.

  'realm' is the realm in which the instance is deployed, and must be one of the following:
      REALM_UNSPECIFIED
      REALM_NA_CENTRAL
      REALM_NA_EAST
      REALM_NA_WEST
      REALM_ASIA_NORTHEAST
      REALM_ASIA_SOUTHEAST
      REALM_EU_WEST

  'capacity' is the maxium number of concurrent streaming sessions that the instance can support in the given realm.
"""


def GetFormattedSupportedEnums():
  messages = api_util.GetMessages()
  supported_enums = ''.join(
      '\n\t - {}'.format(enum.name)
      for enum in messages.RealmConfig.RealmValueValuesEnum)
  return supported_enums


def RealmValidator(realm):
  """Validates that the realm argument is a supported RealmValueValuesEnum."""
  messages = api_util.GetMessages()
  try:
    realm = realm.upper()
    messages.RealmConfig.RealmValueValuesEnum(realm)
  except TypeError:
    raise arg_parsers.ArgumentTypeError(
        'invalid realm {}, must be one of:{}'.format(
            realm, GetFormattedSupportedEnums()))
  return realm


def AddRealmConfigArg(name, parser, repeatable=True, required=True):
  capacity_validator = arg_parsers.RegexpValidator(r'[0-9]+',
                                                   'capacity must be a number')
  repeatable_help = '\nThis is a repeatable flag.' if repeatable else ''
  parser.add_argument(
      name,
      help=_REALM_CONFIG_ARG_HELP_TEXT + repeatable_help,
      type=arg_parsers.ArgDict(
          spec={
              'realm': RealmValidator,
              'capacity': capacity_validator
          },
          required_keys=['realm', 'capacity']),
      required=required,
      action='append')
