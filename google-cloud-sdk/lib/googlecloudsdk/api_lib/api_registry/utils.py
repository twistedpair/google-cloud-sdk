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

"""Utilities for MCP Servers and Tools API."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import properties

_CLOUD_API_REGISTRY_API = 'cloudapiregistry'
_CLOUD_API_REGISTRY_API_VERSION = 'v1alpha'


def GetClientInstance(no_http=False):
  return apis.GetClientInstance(
      _CLOUD_API_REGISTRY_API, _CLOUD_API_REGISTRY_API_VERSION, no_http=no_http)


def GetMessagesModule(client=None):
  client = client or GetClientInstance()
  return client.MESSAGES_MODULE


def GetProject():
  return properties.VALUES.core.project.GetOrFail()


def GetLocation():
  # Since API Registry is a global service right now.
  return 'global'
