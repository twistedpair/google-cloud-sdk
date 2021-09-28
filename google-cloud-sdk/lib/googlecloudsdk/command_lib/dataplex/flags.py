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
"""Shared resource args for Cloud Dataplex surface."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


def AddDiscoveryArgs(parser):
  """Adds Discovery Args to parser."""
  discovery_spec = parser.add_group(
      help='Settings to manage the metadata discovery and publishing.')
  discovery_spec.add_argument(
      '--discovery-enabled',
      action=arg_parsers.StoreTrueFalseAction,
      help='Whether discovery is enabled.')
  discovery_spec.add_argument(
      '--discovery-include-patterns',
      default=[],
      type=arg_parsers.ArgList(),
      metavar='INCLUDE_PATTERNS',
      help="""The list of patterns to apply for selecting data to include
        during discovery if only a subset of the data should considered. For
        Cloud Storage bucket assets, these are interpreted as glob patterns
        used to match object names. For BigQuery dataset assets, these are
        interpreted as patterns to match table names.""")
  discovery_spec.add_argument(
      '--discovery-exclude-patterns',
      default=[],
      type=arg_parsers.ArgList(),
      metavar='EXCLUDE_PATTERNS',
      help="""The list of patterns to apply for selecting data to exclude
        during discovery. For Cloud Storage bucket assets, these are interpreted
        as glob patterns used to match object names. For BigQuery dataset
        assets, these are interpreted as patterns to match table names.""")
  trigger = discovery_spec.add_group(
      help='Determines when discovery jobs are triggered.')
  trigger.add_argument(
      '--discovery-schedule',
      help="""[Cron schedule](https://en.wikipedia.org/wiki/Cron) for running
                discovery jobs periodically. Discovery jobs must be scheduled at
                least 30 minutes apart.""")
  return discovery_spec
