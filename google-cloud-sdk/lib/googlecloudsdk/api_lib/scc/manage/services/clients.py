# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Useful commands for interacting with the Cloud SCC API."""

from typing import Generator

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.scc import util as scc_util
from googlecloudsdk.core import log
from googlecloudsdk.generated_clients.apis.securitycentermanagement.v1 import securitycentermanagement_v1_messages as messages


class SecurityCenterServicesClient(object):
  """Client for Security Center Services interaction with the Security Center Management API."""

  def __init__(self):
    # Although this client looks specific to projects, this is a codegen
    # artifact. It can be used for any parent types.
    self._client = apis.GetClientInstance(
        'securitycentermanagement', 'v1'
    ).projects_locations_securityCenterServices

  def Get(self, name: str) -> messages.SecurityCenterService:
    """Get a Security Center Service."""

    req = messages.SecuritycentermanagementProjectsLocationsSecurityCenterServicesGetRequest(
        name=name
    )
    return self._client.Get(req)

  def List(self, page_size: int, parent: str, limit: int) -> Generator[
      messages.SecurityCenterService,
      None,
      messages.ListSecurityCenterServicesResponse,
  ]:
    """List the details of a Security Center Services."""

    req = messages.SecuritycentermanagementProjectsLocationsSecurityCenterServicesListRequest(
        pageSize=page_size, parent=parent
    )
    return list_pager.YieldFromList(
        self._client,
        request=req,
        limit=limit,
        field='securityCenterServices',
        batch_size=page_size,
        batch_size_attribute='pageSize',
    )

  def Update(
      self,
      name: str,
      validate_only: bool,
      module_config: messages.SecurityCenterService.ModulesValue,
      enablement_state: messages.SecurityCenterService.IntendedEnablementStateValueValuesEnum,
      update_mask: str,
  ) -> messages.SecurityCenterService:
    """Update a Security Center Service."""

    security_center_service = messages.SecurityCenterService(
        modules=module_config,
        intendedEnablementState=enablement_state,
        name=name,
    )

    req = messages.SecuritycentermanagementProjectsLocationsSecurityCenterServicesPatchRequest(
        securityCenterService=security_center_service,
        name=name,
        updateMask=scc_util.CleanUpUserMaskInput(update_mask),
        validateOnly=validate_only,
    )
    response = self._client.Patch(req)
    if validate_only:
      log.status.Print('Request is valid.')
      return response
    log.UpdatedResource(name)
    return response
