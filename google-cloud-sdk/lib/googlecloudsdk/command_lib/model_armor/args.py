# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Shared resource arguments and flags."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


def AddFullUri(parser, positional=False, help_text=None, **kwargs):
  """Add full uri argument to the parser."""

  parser.add_argument(
      _ArgOrFlag('full-uri', positional), help=(help_text), **kwargs
  )


def AddFloorSettingEnforcement(
    parser, positional=False, help_text=None, **kwargs
):
  """Enable or disable the floor setting enforcement."""

  parser.add_argument(
      _ArgOrFlag('enable-floor-setting-enforcement', positional),
      help=(help_text),
      **kwargs
  )


def AddMaliciousUriFilterSettingsEnforcement(parser):
  """Add malicious uri filter settings enforcement argument to the parser."""
  group = parser.add_group(mutex=True, help='Malicious uri filter settings.')
  group.add_argument(
      _ArgOrFlag('malicious-uri-filter-settings-enforcement', False),
      metavar='MALICIOUS_URI_FILTER_SETTINGS_ENFORCEMENT',
      help='Malicious URI filter settings.',
  )


def AddPIJBFilterSettingsGroup(parser):
  """Add flags for specifying pi and jailbreak filter settings."""
  group = parser.add_group(
      mutex=False, help='PI and jailbreak filter settings.'
  )
  group.add_argument(
      _ArgOrFlag('pi-and-jailbreak-filter-settings-enforcement', False),
      metavar='PI_AND_JAILBREAK_FILTER_SETTINGS_ENFORCEMENT',
      help=(
          'The pi and jailbreak filter settings enforcement. The value can be'
          ' either "enable" or "disable".'
      ),
  )
  group.add_argument(
      _ArgOrFlag('pi-and-jailbreak-filter-settings-confidence-level', False),
      metavar='PI_AND_JAILBREAK_FILTER_SETTINGS_CONFIDENCE_LEVEL',
      help=(
          'The pi and jailbreak filter settings confidence level. The value can'
          ' be either "high", "medium-and-above" or "low-and-above"'
      ),
  )


def AddSDPFilterBasicConfigGroup(parser):
  """Add flags for specifying sdp filter settings."""
  group = parser.add_group(mutex=False, help='SDP filter settings.')
  group.add_argument(
      _ArgOrFlag('basic-config-filter-enforcement', False),
      metavar='BASIC_CONFIG_FILTER_ENFORCEMENT',
      help=(
          'The sdp filter settings enforcement. The value can be either'
          ' "ENABLED" or "DISABLED"'
      ),
  )
  group.add_argument(
      _ArgOrFlag('advanced-config-inspect-template', False),
      metavar='ADVANCED_CONFIG_INSPECT_TEMPLATE',
      help=(
          'The sdp filter settings enforcement. The value can be either'
          ' "enable" or "disable".'
      ),
  )
  group.add_argument(
      _ArgOrFlag('advanced-config-deidentify-template', False),
      metavar='ADVANCED_CONFIG_DEIDENTIFY_TEMPLATE',
      help=(
          'The sdp filter settings enforcement. The value can be either'
          ' "enable" or "disable".'
      ),
  )


def AddRaiFilterSettingsGroup(parser):
  """Add flags for specifying rai filter settings."""
  group = parser.add_group(mutex=True, help='RAI filter settings.')
  group.add_argument(
      _ArgOrFlag('rai-settings-filters', False),
      metavar='confidenceLevel=CONFIDENCELEVEL],[filterType=FILTERTYPE]',
      type=arg_parsers.ArgObject(repeated=True),
      action=arg_parsers.FlattenAction(),
      help=(
          'Set rai_settings_filters to new value. List of Responsible AI'
          ' filters enabled for floor setting'
      ),
  )
  group.add_argument(
      _ArgOrFlag('add-rai-settings-filters', False),
      metavar='confidenceLevel=CONFIDENCELEVEL],[filterType=FILTERTYPE]',
      type=arg_parsers.ArgObject(repeated=True),
      action=arg_parsers.FlattenAction(),
      help='Add rai filter settings.',
  )
  group.add_argument(
      _ArgOrFlag('remove-rai-settings-filters', False),
      metavar='confidenceLevel=CONFIDENCELEVEL],[filterType=FILTERTYPE]',
      type=arg_parsers.ArgObject(repeated=True),
      action=arg_parsers.FlattenAction(),
      help='Remove rai filter settings.',
  )
  group.add_argument(
      _ArgOrFlag('clear-rai-settings-filters', False),
      action='store_true',
      help='Clear all rai filter settings.',
  )


def _ArgOrFlag(name, positional):
  """Returns the argument name in resource argument format or flag format.

  Args:
      name (str): name of the argument
      positional (bool): whether the argument is positional

  Returns:
      arg (str): the argument or flag
  """
  if positional:
    return name.upper().replace('-', '_')
  return '--{}'.format(name)
