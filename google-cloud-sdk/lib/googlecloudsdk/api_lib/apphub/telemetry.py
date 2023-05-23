# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Apphub Telemetry API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.apphub import utils as api_lib_utils
from googlecloudsdk.command_lib.apphub import utils as command_lib_utils


class TelemetryClient(object):
  """Client for telemetry in Apphub API."""

  def __init__(self, client=None, messages=None):
    self._generated_client = client or api_lib_utils.GetClientInstance()
    self.messages = messages or api_lib_utils.GetMessagesModule()
    self._telemetry_client = self._generated_client.projects_locations

  def Describe(self):
    get_request = (
        self.messages.ApphubProjectsLocationsGetTelemetryRequest(
            name=command_lib_utils.GetGlobalTelemetryResourceRelativeName()
        )
    )
    return self._telemetry_client.GetTelemetry(get_request)
