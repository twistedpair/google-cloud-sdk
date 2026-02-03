# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""A library for Security Command Center(SCC) external exposure commands utils."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis

API_NAME = 'externalexposure'
DEFAULT_API_VERSION = 'v1alpha'
DEFAULT_LOCATION = 'global'


def GetClient(version=DEFAULT_API_VERSION):
  """Import and return the externalexposure client module.

  Args:
    version: the API version

  Returns:
    externalexposure client module.
  """
  return apis.GetClientInstance(API_NAME, version)


def GetMessagesModule(version=DEFAULT_API_VERSION):
  """Import and return the externalexposure message module.

  Args:
    version: the API version

  Returns:
    externalexposure message module.
  """

  return apis.GetMessagesModule(API_NAME, version)


def GenerateParent(args):
  if args.organization:
    return 'organizations/{}/locations/{}'.format(
        args.organization, DEFAULT_LOCATION
    )
  elif args.project:
    return 'projects/{}/locations/{}'.format(args.project, DEFAULT_LOCATION)
  elif args.folder:
    return 'folders/{}/locations/{}'.format(args.folder, DEFAULT_LOCATION)
