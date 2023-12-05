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
"""Useful commands for interacting with the Cloud SCC API."""

from typing import Generator
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.generated_clients.apis.securitycentermanagement.v1 import securitycentermanagement_v1_messages as messages


class SHACustomModuleClient(object):
  """Client for SHA custom module interaction with the Security Center Management API."""

  def __init__(self):
    # Although this client looks specific to projects, this is a codegen
    # artifact. It can be used for any parent types.
    self._client = apis.GetClientInstance(
        'securitycentermanagement', 'v1'
    ).projects_locations_securityHealthAnalyticsCustomModules

  def Get(self, name: str) -> messages.SecurityHealthAnalyticsCustomModule:
    """Get a SHA custom module."""

    req = messages.SecuritycentermanagementProjectsLocationsSecurityHealthAnalyticsCustomModulesGetRequest(
        name=name
    )
    return self._client.Get(req)

  def Simulate(
      self, parent, custom_config, resource
  ) -> messages.SimulateSecurityHealthAnalyticsCustomModuleResponse:
    """Simulate a SHA custom module."""

    sim_req = messages.SimulateSecurityHealthAnalyticsCustomModuleRequest(
        customConfig=custom_config, resource=resource
    )
    req = messages.SecuritycentermanagementProjectsLocationsSecurityHealthAnalyticsCustomModulesSimulateRequest(
        parent=parent,
        simulateSecurityHealthAnalyticsCustomModuleRequest=sim_req,
    )
    return self._client.Simulate(req)

  def Delete(self, name: str, validate_only: bool):
    """Delete a SHA custom module."""

    req = messages.SecuritycentermanagementProjectsLocationsSecurityHealthAnalyticsCustomModulesDeleteRequest(
        name=name, validateOnly=validate_only
    )
    if validate_only:
      log.status.Print('Request is valid.')
      return
    console_io.PromptContinue(
        message=(
            'Are you sure you want to delete the Security Health Analytics'
            ' custom module {}?\n'.format(name)
        ),
        cancel_on_no=True,
    )
    response = self._client.Delete(req)
    log.DeletedResource(name)
    return response

  def List(
      self, page_size: int, page_token: str, parent: str, limit: int
  ) -> Generator[
      messages.SecurityHealthAnalyticsCustomModule,
      None,
      messages.ListSecurityHealthAnalyticsCustomModulesResponse,
  ]:
    """List the details of an SHA custom module."""

    req = messages.SecuritycentermanagementProjectsLocationsSecurityHealthAnalyticsCustomModulesListRequest(
        pageSize=page_size, pageToken=page_token, parent=parent
    )
    return list_pager.YieldFromList(
        self._client,
        request=req,
        limit=limit,
        field='securityHealthAnalyticsCustomModules',
        batch_size=page_size,
        batch_size_attribute='pageSize',
        current_token_attribute='pageToken',
    )


class EffectiveSHACustomModuleClient(object):
  """Client for SHA effective custom module interaction with the Security Center Management API."""

  def __init__(self):
    self._client = apis.GetClientInstance(
        'securitycentermanagement', 'v1'
    ).projects_locations_effectiveSecurityHealthAnalyticsCustomModules

  def Get(self,
          name: str) -> messages.EffectiveSecurityHealthAnalyticsCustomModule:
    """Get a SHA effective custom module."""

    req = messages.SecuritycentermanagementProjectsLocationsEffectiveSecurityHealthAnalyticsCustomModulesGetRequest(
        name=name
    )
    return self._client.Get(req)
