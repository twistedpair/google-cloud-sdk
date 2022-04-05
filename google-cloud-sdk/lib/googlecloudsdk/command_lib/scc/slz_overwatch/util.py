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
"""Contains Helper Functions for overwatch."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64
import contextlib
import json
import re

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files
from six import text_type
from six.moves.urllib import parse

INVALID_OVERWATCH_PATH_MSG = ('The Overwatch Path should be of the form '
                              'organizations/<org_id>/locations/<location_id>'
                              '/overwatches/<overwatch_id> found {}.')
INVALID_JSON_MESSAGE = 'Invalid JSON at {}.'
INVALID_LOCATION_MESSAGE = ('The location in overwatch path "{}" does not '
                            'match the default location parameter "{}" '
                            'specified at scc/slz-overwatch-location.')


def base_64_encoding(file_path=None, open_=None):
  """Encodes content of a blueprint plan JSON to Base64.

  Args:
    file_path: The path of the blueprint plan file to be encoded.
    open_: The filestream of the blueprint json file.

  Returns:
    Base64 encoded message.
  """
  if not open_:
    open_ = files.ReadFileContents(file_path)
  try:
    blueprint_plan = json.load(open_)
  except ValueError:
    raise exceptions.BadFileException(INVALID_JSON_MESSAGE.format(file_path))
  encoded_string = base64.standard_b64encode(
      json.dumps(blueprint_plan).encode('utf-8'))
  return encoded_string.decode('utf-8')


def parse_overwatch_path(path):
  """Verifies and Parses overwatch path.

  Args:
    path: The overwatch path.

  Returns:
    org_id: The organization ID.
    region: The location ID.
    overwatch_id: The overwatch ID.

  Raises:
    InvalidArgumentException if overwatch path is not correct.
  """
  overwatch_pattern = ('^organizations/[0-9]+/locations/[-_a-zA-Z0-9]+'
                       '/overwatches/[-_a-zA-Z0-9]+$')
  if path and re.match(overwatch_pattern, path):
    _, org_id, _, region, _, overwatch_id = path.strip().split('/')
    return org_id, region, overwatch_id
  else:
    raise exceptions.InvalidArgumentException(
        'OVERWATCH', INVALID_OVERWATCH_PATH_MSG.format(path))


def derive_regional_endpoint(endpoint, region):
  scheme, netloc, path, params, query, fragment = [
      text_type(el) for el in parse.urlparse(endpoint)
  ]
  netloc = '{}-{}'.format(region, netloc)
  return parse.urlunparse((scheme, netloc, path, params, query, fragment))


@contextlib.contextmanager
def override_endpoint(path=None):
  """Check for region and set api_endpoint_overrides property.

  Args:
    path: The overwatch path. (optional)

  Yields:
    None

  Raises:
    InvalidArgumentException: Location in overwatch path does not match the
    default location.
  """
  # Check default value of location from scc/slz-overwatch-location
  default_location = properties.VALUES.scc.slz_overwatch_location.Get()
  if path and default_location != 'global':
    _, overwatch_location, _ = parse_overwatch_path(path)
    if overwatch_location != default_location:
      raise exceptions.InvalidArgumentException(
          'OVERWATCH',
          INVALID_LOCATION_MESSAGE.format(overwatch_location, default_location))

  old_endpoint = apis.GetEffectiveApiEndpoint('securedlandingzone', 'v1beta')
  try:
    if default_location != 'global':
      # Use regional Endpoint
      regional_endpoint = derive_regional_endpoint(old_endpoint,
                                                   default_location)
      properties.VALUES.api_endpoint_overrides.securedlandingzone.Set(
          regional_endpoint)
    yield
  finally:
    properties.VALUES.api_endpoint_overrides.securedlandingzone.Set(
        old_endpoint)
