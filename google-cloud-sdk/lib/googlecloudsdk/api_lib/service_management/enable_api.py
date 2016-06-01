# Copyright 2016 Google Inc. All Rights Reserved.
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

"""service-management enable helper functions."""

from googlecloudsdk.api_lib.service_management import services_util
from googlecloudsdk.api_lib.util import http_error_handler
from googlecloudsdk.core import log


@http_error_handler.HandleHttpErrors
def EnableServiceApiCall(project_id, service_name):
  """Make API call to enable a specific API."""

  client = services_util.GetClientInstance()
  messages = services_util.GetMessagesModule()

  # Shorten the patch request name for better readability
  patch_request = messages.ServicemanagementServicesProjectSettingsPatchRequest

  usage_settings = messages.UsageSettings(
      consumerEnableStatus=(messages.UsageSettings
                            .ConsumerEnableStatusValueValuesEnum.ENABLED))

  project_settings = messages.ProjectSettings(usageSettings=usage_settings)

  request = patch_request(
      serviceName=service_name,
      consumerProjectId=project_id,
      projectSettings=project_settings,
      updateMask='usage_settings.consumer_enable_status')

  return client.services_projectSettings.Patch(request)


@http_error_handler.HandleHttpErrors
def EnableServiceIfDisabled(project_id, service_name, async=False):
  """Check to see if the service is enabled, and if it is not, do so."""

  client = services_util.GetClientInstance()
  messages = services_util.GetMessagesModule()

  # Check to see if the service is already enabled
  request = messages.ServicemanagementServicesProjectSettingsGetRequest(
      serviceName=service_name,
      consumerProjectId=project_id,
      view=services_util.GetCallerViews().get('CONSUMER'))

  project_settings_result = client.services_projectSettings.Get(request)
  enabled = messages.UsageSettings.ConsumerEnableStatusValueValuesEnum.ENABLED

  # If the service is not yet enabled, enable it
  if (not project_settings_result.usageSettings or
      project_settings_result.usageSettings.consumerEnableStatus != enabled):
    log.status.Print('Enabling service {0} on project {1}...'.format(
        service_name, project_id))

    # Enable the service
    operation = EnableServiceApiCall(project_id, service_name)

    # Process the enable operation
    services_util.ProcessOperationResult(operation, async)
