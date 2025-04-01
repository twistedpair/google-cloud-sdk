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
"""Module containing the extended wrappers for Remediation Intents service."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Any

from googlecloudsdk.api_lib.scc.remediation_intents import sps_api
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.scc.remediation_intents import errors


class ExtendedSPSClient():
  """Extended client for the SPS Service (wrappers for specific API calls).

  Attributes:
    release_track: The Gcloud release track to use, like ALPHA, GA.
    org_id: The organization ID for which the API methods are called.
    api_version: The API version to use like v1alpha, main etc.
    client: The client for the SPS Service.
    messages: The messages module for the SPS Service.
  """

  def __init__(self, org_id: str, release_track=base.ReleaseTrack.ALPHA):
    """Initializes the ExtendedSPSClient.

    Args:
      org_id: The organization ID for which the API methods are called.
      release_track: The release track to use for the API version.
    """
    self.release_track = release_track
    self.org_id = org_id
    self.api_version = sps_api.VERSION_MAP.get(release_track)
    self.client = sps_api.GetClientInstance(release_track)
    self.messages = sps_api.GetMessagesModule(release_track)

  def fetch_enqueued_remediation_intent(self) -> Any:
    """Fetches a Remediation Intent resource in ENQUEUED state in given org.

    Returns:
      A Remediation Intent resource in ENQUEUED state for the given org. If no
      such resource is found, returns None.
      Return format is of class (securityposture.messages.RemediationIntent).

    Raises:
      APICallError: An error while calling the SPS Service.
    """
    request = self.messages.SecuritypostureOrganizationsLocationsRemediationIntentsListRequest(
        parent=f'organizations/{self.org_id}/locations/global',
        filter='state : REMEDIATION_INTENT_ENQUEUED',
    )
    try:
      response = (  # List API call.
          self.client.organizations_locations_remediationIntents.List(request)
      )
    except Exception as e:  # Any error like network or system failure.
      raise errors.APICallError('List', str(e))

    remediation_intents = response.remediationIntents
    if remediation_intents is None or len(remediation_intents) < 1:
      return None
    return remediation_intents[0]

  def create_semi_autonomous_remediation_intent(self) -> None:
    """Creates a Semi Autonomous type Remediation Intent resource.

    Raises:
      APICallError: An error while calling the SPS Service.
    """
    request = self.messages.SecuritypostureOrganizationsLocationsRemediationIntentsCreateRequest(
        parent=f'organizations/{self.org_id}/locations/global',
        createRemediationIntentRequest=self.messages.CreateRemediationIntentRequest(
            workflowType=self.messages.CreateRemediationIntentRequest.WorkflowTypeValueValuesEnum.WORKFLOW_TYPE_SEMI_AUTONOMOUS,
        ),
    )
    try:  # Create API call.
      operation = self.client.organizations_locations_remediationIntents.Create(
          request=request
      )
      _ = sps_api.WaitForOperation(   # Polling the LRO.
          operation_ref=sps_api.GetOperationsRef(operation.name),
          message='Waiting for remediation intent to be created',
          has_result=True,
      )
    except Exception as e:
      raise errors.APICallError('Create', str(e))

  def update_remediation_intent(
      self,
      ri_name: str, update_mask: str,
      remediation_intent: Any,
  ) -> Any:
    """Updates a Remediation Intent resource.

    Args:
      ri_name: The name of the Remediation Intent resource to be updated.
      update_mask: The update mask for the update operation.
      remediation_intent: The updated Remediation Intent resource.

    Returns:
      The updated Remediation Intent resource.
      Return format is of class (securityposture.messages.RemediationIntent).

    Raises:
      APICallError: An error while calling the SPS Service.
    """
    request = self.messages.SecuritypostureOrganizationsLocationsRemediationIntentsPatchRequest(
        name=ri_name,
        updateMask=update_mask,
        remediationIntent=remediation_intent
    )
    try:
      operation = self.client.organizations_locations_remediationIntents.Patch(
          request=request
      )
      return sps_api.WaitForOperation(   # Polling the LRO.
          operation_ref=sps_api.GetOperationsRef(operation.name),
          message='Waiting for remediation intent to be updated',
          has_result=True,
      )
    except Exception as e:
      raise errors.APICallError('Update', str(e))
