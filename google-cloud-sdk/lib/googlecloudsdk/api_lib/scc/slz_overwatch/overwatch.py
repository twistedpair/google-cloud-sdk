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
"""Overwatch Object to run all commands under overwatch."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.scc.slz_overwatch import instances
from googlecloudsdk.command_lib.scc.slz_overwatch import util


class SLZOverwatchClient(object):
  """Implements overwatch commands using API Client."""

  def __init__(self):
    self._messages = instances.get_overwatch_message()
    self._overwatch_service = instances.get_overwatch_service()
    self._organization_service = instances.get_organization_service()
    self._operation_service = instances.get_operations_service()

  def List(self, parent, page_size=None, page_token=None):
    """Implements method for the overwatch command `list`.

    Args:
      parent: The organization ID and location in the format
        organizations/<ORG_ID>/locations/<LOCATION-ID>.
      page_size: The entries required at a time.
      page_token: The page token for the specific page. If the page_token is
        empty, then it indicates to return results from the start.

    Returns:
      response: The response from the List method of API client.
    """
    request = self._messages.SecuredlandingzoneOrganizationsLocationsOverwatchesListRequest(
        parent=parent, pageSize=page_size, pageToken=page_token)
    response = self._overwatch_service.List(request)
    return response

  def Get(self, overwatch_path):
    """Implements method for the overwatch command `get`.

    Args:
      overwatch_path: The complete overwatch path. Format:
        organizations/<ORG_ID>/locations/<LOCATION_ID>/overwatches/<OVERWATCH_ID>.

    Returns:
      response: The json response from the Get method of API client.
    """
    # Using ParseOverwatchPath to validate the overwatch path.
    _ = util.parse_overwatch_path(overwatch_path)
    request = self._messages.SecuredlandingzoneOrganizationsLocationsOverwatchesGetRequest(
        name=overwatch_path)
    response = self._overwatch_service.Get(request)
    return response

  def Delete(self, overwatch_path):
    """Implements method for the overwatch command `delete`.

    Args:
      overwatch_path: The complete overwatch path. Format:
        organizations/<ORG_ID>/locations/<LOCATION_ID>/overwatches/<OVERWATCH_ID>.

    Returns:
      response: The json response from the Delete method of API client.
    """
    # Using ParseOverwatchPath to validate the overwatch path.
    _ = util.parse_overwatch_path(overwatch_path)
    request = self._messages.SecuredlandingzoneOrganizationsLocationsOverwatchesDeleteRequest(
        name=overwatch_path)
    response = self._overwatch_service.Delete(request)
    return response

  def Create(self, overwatch_path, blueprint_plan):
    """Implements method for the overwatch command `create`.

    Args:
      overwatch_path: The complete overwatch path. Format:
        organizations/<ORG_ID>/locations/<LOCATION_ID>/overwatches/<OVERWATCH_ID>.
      blueprint_plan: Base64 encoded blueprint plan message.

    Returns:
      response: The json response from the Create method of API client.
    """
    overwatch = self._messages.GoogleCloudSecuredlandingzoneV1betaOverwatch(
        name=overwatch_path,
        # Any overwatch created by default is set to ACTIVE
        state=self._messages.GoogleCloudSecuredlandingzoneV1betaOverwatch
        .StateValuesEnum.ACTIVE,
        blueprint_plan=blueprint_plan)
    # ParseOverwatchPath also checks if the overwatch path is valid.
    org_id, loc_id, overwatch_id = util.parse_overwatch_path(overwatch_path)
    parent = 'organizations/{}/locations/{}'.format(org_id, loc_id)
    request = self._messages.SecuredlandingzoneOrganizationsLocationsOverwatchesCreateRequest(
        parent=parent,
        googleCloudSecuredlandingzoneV1betaOverwatch=overwatch,
        overwatchId=overwatch_id)
    response = self._overwatch_service.Create(request)
    return response

  def Suspend(self, overwatch_path):
    """Implements method for the overwatch command `suspend`.

    Args:
      overwatch_path: The complete overwatch path. Format:
        organizations/<ORG_ID>/locations/<LOCATION_ID>/overwatches/<OVERWATCH_ID>.

    Returns:
      response: The json response from the Suspend method of API client.
    """
    # Using ParseOverwatchPath to validate the overwatch path.
    _ = util.parse_overwatch_path(overwatch_path)
    request = self._messages.SecuredlandingzoneOrganizationsLocationsOverwatchesSuspendRequest(
        name=overwatch_path)
    response = self._overwatch_service.Suspend(request)
    return response

  def Activate(self, overwatch_path):
    """Implements method for the overwatch command `activate`.

    Args:
      overwatch_path: The complete overwatch path. Format:
        organizations/<ORG_ID>/locations/<LOCATION_ID>/overwatches/<OVERWATCH_ID>.

    Returns:
      response: The json response from the Activate method of API client.
    """
    # Using ParseOverwatchPath to validate the overwatch path.
    _ = util.parse_overwatch_path(overwatch_path)
    request = self._messages.SecuredlandingzoneOrganizationsLocationsOverwatchesActivateRequest(
        name=overwatch_path)
    response = self._overwatch_service.Activate(request)
    return response

  def Patch(self, overwatch_path, blueprint_plan, update_mask):
    """Implements method for the overwatch command `update`.

    Args:
      overwatch_path: The complete overwatch path. Format:
        organizations/<ORG_ID>/locations/<LOCATION_ID>/overwatches/<OVERWATCH_ID>.
      blueprint_plan: Base64 encoded blueprint plan message.
      update_mask: The name of the field that will be updated.

    Returns:
      response: The json response from the Update method of API client.
    """
    overwatch = self._messages.GoogleCloudSecuredlandingzoneV1betaOverwatch(
        name=overwatch_path, blueprint_plan=blueprint_plan)
    # ParseOverwatchPath also checks if the overwatch path is valid.
    _ = util.parse_overwatch_path(overwatch_path)
    request = self._messages.SecuredlandingzoneOrganizationsLocationsOverwatchesPatchRequest(
        name=overwatch_path,
        googleCloudSecuredlandingzoneV1betaOverwatch=overwatch,
        update_mask=update_mask)
    response = self._overwatch_service.Patch(request)
    return response

  def Enable(self, organization_id, location_id):
    """Implements method for the overwatch command `enable`.

    Args:
      organization_id: The organization ID. Format: organizations/<ORG_ID>.
      location_id: The location where overwatch needs to be enabled.

    Returns:
      response: The json response from the Enable method of API client.
    """
    request = self._messages.SecuredlandingzoneOrganizationsLocationsEnableOverwatchRequest(
        organization=organization_id, locationsId=location_id)
    response = self._organization_service.EnableOverwatch(request)
    return response

  def Operation(self, operation_id):
    """Implements method for the overwatch command  `operation`.

    Args:
      operation_id: The operation ID of google.lonrunning.operation. Format:
        operations/<OPERATION_ID>.

    Returns:
      response: The json response from the Operation method of API client.
    """
    request = self._messages.SecuredlandingzoneOrganizationsOperationsGetRequest(
        name=operation_id)
    response = self._operation_service.Get(request)
    return response
