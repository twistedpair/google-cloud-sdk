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


def EnableServiceApiCall(client, messages, project_id, service_name):
  """Make API call to enable a specific API."""

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
