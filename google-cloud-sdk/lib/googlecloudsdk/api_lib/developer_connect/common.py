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
"""Common utilities for the Developer Connect API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base

import six.moves.urllib.parse

API_NAME = 'developerconnect'
API_VERSION_1 = 'v1'


def GetApiVersion(release_track):
  if release_track == base.ReleaseTrack.GA:
    return API_VERSION_1
  else:
    return None


def GetApiServiceName(api_version):
  """Gets the service name based on the configured API endpoint."""
  endpoint = apis.GetEffectiveApiEndpoint(API_NAME, api_version)
  return six.moves.urllib.parse.urlparse(endpoint).hostname
