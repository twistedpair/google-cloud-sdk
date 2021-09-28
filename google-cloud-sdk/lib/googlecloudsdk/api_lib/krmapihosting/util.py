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
"""KRM API Hosting API utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis

_DEFAULT_API_VERSION = 'v1alpha1'


def GetMessagesModule(api_version=_DEFAULT_API_VERSION):
  return apis.GetMessagesModule('krmapihosting', api_version)


def GetClientInstance(api_version=_DEFAULT_API_VERSION, use_http=True):
  """Returns an instance of the KRM API Hosting client.

  Args:
    api_version: The desired api version.
    use_http: bool, True to create an http object for this client.

  Returns:
    base_api.BaseApiClient, An instance of the Cloud Build client.
  """
  return apis.GetClientInstance(
      'krmapihosting', api_version, no_http=(not use_http))
