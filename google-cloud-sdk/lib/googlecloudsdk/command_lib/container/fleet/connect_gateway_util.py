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
"""Utilities for interacting with Connect Gateway API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.services import enable_api
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.container.fleet.memberships import errors as memberships_errors


def CheckGatewayApiEnablement(project_id, service_name):
  """Checks if the Connect Gateway API is enabled for a given project.

  Prompts the user to enable the API if the API is not enabled. Defaults to
  "No". Throws an error if the user declines to enable the API.

  Args:
    project_id: The ID of the project on which to check/enable the API.
    service_name: The name of the service to check/enable the API.

  Raises:
    memberships_errors.ServiceNotEnabledError: if the user declines to attempt
      to enable the API.
    exceptions.GetServicesPermissionDeniedException: if a 403 or 404 error is
      returned by the Get request.
    apitools_exceptions.HttpError: Another miscellaneous error with the
      listing service.
    api_exceptions.HttpException: API not enabled error if the user chooses to
      not enable the API.
  """
  if not enable_api.IsServiceEnabled(project_id, service_name):
    try:
      apis.PromptToEnableApi(
          project_id, service_name,
          memberships_errors.ServiceNotEnabledError('Connect Gateway API',
                                                    service_name, project_id))
    except apis.apitools_exceptions.RequestError:
      # Since we are not actually calling the API, there is nothing to retry,
      # so this signal to retry can be ignored
      pass
