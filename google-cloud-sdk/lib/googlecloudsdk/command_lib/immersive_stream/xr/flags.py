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

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core import log
import six.moves.urllib.parse

_REGION_CONFIG_ARG_HELP_TEXT = """\
  Flag used to specify region and capacity required for the service instance's availability.

  'region' is the region in which the instance is deployed.

  'capacity' is the maxium number of concurrent streaming sessions that the instance can support in the given region.
"""

_FALLBACK_URL_HELP_TEXT = """\
    Flag used to specify the fallback url to redirect users to when this service instance is unable to provide the streaming experience.
"""


def RegionValidator(region):
  """RegionValidator is a no-op. The validation is handled in CLH server."""
  return region


def AddRegionConfigArg(name, parser, repeatable=True, required=True):
  capacity_validator = arg_parsers.RegexpValidator(r'[0-9]+',
                                                   'capacity must be a number')
  repeatable_help = '\nThis is a repeatable flag.' if repeatable else ''
  parser.add_argument(
      name,
      help=_REGION_CONFIG_ARG_HELP_TEXT + repeatable_help,
      type=arg_parsers.ArgDict(
          spec={
              'region': RegionValidator,
              'capacity': capacity_validator
          },
          required_keys=['region', 'capacity']),
      required=required,
      action='append')


def ValidateUrl(url):
  """Rudimentary url validator.

  Args:
    url: String

  Returns:
    Whether the input string contains both a scheme and a network location. Note
    that this is a very rudimentary validator and does not work on all cases.
    Invalid urls may still pass this check.
  """
  parsed_url = six.moves.urllib.parse.urlsplit(url)
  if not parsed_url.scheme:
    log.error('Invalid URL - The URL must contain a scheme')
    return False
  if not parsed_url.netloc:
    log.error('Invalid URL - The URL must contain a network location')
    return False
  return True
