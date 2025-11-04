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


def AddIntegratedServices(parser):
  """Add flags for specifying integrated services."""
  group = parser.add_group(
      mutex=True,
      help=(
          'Manage integrated services to apply Model Armor floor settings.'
          ' Integrated services will have Model Armor sanitization enabled'
          ' project-wide.'
      ),
  )
  group.add_argument(
      _ArgOrFlag('add-integrated-services', False),
      metavar='INTEGRATED_SERVICE',
      type=arg_parsers.ArgList(),
      help=(
          'Set the list of integrated services for the floor setting. This can'
          ' be used to enable project-wide Model Armor sanitization for the'
          ' respective services.'
      ),
  )
  group.add_argument(
      _ArgOrFlag('remove-integrated-services', False),
      metavar='INTEGRATED_SERVICE',
      type=arg_parsers.ArgList(),
      help='Remove specified service(s) from the list of integrated services.',
  )
  group.add_argument(
      _ArgOrFlag('clear-integrated-services', False),
      action='store_true',
      help='Clear all integrated services from the floor setting.',
  )


def AddVertexAiFloorSetting(parser):
  """Add flags for specifying vertex ai floor setting."""
  group = parser.add_group(
      mutex=False, help='Options for Vertex AI sanitization.'
  )
  group.add_argument(
      _ArgOrFlag('enable-vertex-ai-cloud-logging', False),
      help=(
          'Enable Cloud Logging for Vertex AI sanitization to log Model'
          ' Armor sanitization results.'
      ),
      action='store_true',
      default=False,
  )
  group.add_argument(
      _ArgOrFlag('vertex-ai-enforcement-type', False),
      dest='vertex_ai_enforcement_type',
      help=(
          'Specifies the enforcement mode for Vertex AI sanitization, such as'
          ' "INSPECT_ONLY" or "INSPECT_AND_BLOCK".'
          ' Default is "INSPECT_ONLY".'
      ),
  )


def AddMultiLanguageDetection(parser):
  """Add flags for specifying multi language detection."""
  group = parser.add_group(
      mutex=False, help='Multi language detection enablement.'
  )
  group.add_argument(
      _ArgOrFlag('enable-multi-language-detection', False),
      help=(
          'Enable multi-language detection for floor setting, allowing Model'
          ' Armor to process content in multiple languages.'
      ),
      action='store_true',
      default=False,
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
