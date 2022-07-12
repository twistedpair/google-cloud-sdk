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
"""Utilities for enabling service APIs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.services import enable_api
from googlecloudsdk.api_lib.util import api_enablement
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io


def PromptToEnableApiIfDisabled(service_name):
  # type: (str) -> None
  """Prompts to enable the API if it's not enabled.

  Args:
    service_name: The name of the service to enable.
  """
  project_id = properties.VALUES.core.project.GetOrFail()
  if console_io.CanPrompt() and not enable_api.IsServiceEnabled(
      project_id, service_name):
    api_enablement.PromptToEnableApi(project_id, service_name)
