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
"""CRM API Capability utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from googlecloudsdk.api_lib.util import apis

API_VERSION = 'v3'


def CapabilitiesClient(api_version: str = API_VERSION):
  return apis.GetClientInstance('cloudresourcemanager', api_version)


def CapabilitiesService(api_version: str = API_VERSION):
  return CapabilitiesClient(api_version).folders_capabilities


def CapabilitiesMessages(api_version: str = API_VERSION):
  return apis.GetMessagesModule('cloudresourcemanager', api_version)


def GetCapability(capability_id: str) -> CapabilitiesMessages().Capability:
  """Get a particular Capability using capability_id.

  The method explicitly sets Capability.value to False in case Capability is not
  enabled, because the default response does not populate the value field if the
  capability is disabled.

  Args:
    capability_id: The capability_id to get.

  Returns:
    The response from the Get Request. In case the value is False, it is
    explicitly populated with the proper value for clarity.
  """
  get_capability_response = CapabilitiesService().Get(
      CapabilitiesMessages().CloudresourcemanagerFoldersCapabilitiesGetRequest(
          name=capability_id
      )
  )
  if not get_capability_response.value:
    get_capability_response.value = False
  return get_capability_response


def UpdateCapability(
    capability_id: str, value: bool, update_mask: str = ''
) -> CapabilitiesMessages().Operation:
  """Send an Update Request for the capability.

  Capability is a singleton resource, and only certain capability_types are
  allowed. Currently, "app-management" is the only possible capability_type.

  Args:
    capability_id: The capability_id to update. Should be in the format:
        folders/{folder_id}/capabilities/{capability_type}.
    value: The value to set for the capability.
    update_mask: The update mask to use for the request.

  Returns:
    The response from the Update Request.
  """
  return CapabilitiesService().Patch(
      CapabilitiesMessages().CloudresourcemanagerFoldersCapabilitiesPatchRequest(
          name=capability_id,
          updateMask=update_mask,
          capability=CapabilitiesMessages().Capability(
              name=capability_id, value=value
          ),
      )
  )
