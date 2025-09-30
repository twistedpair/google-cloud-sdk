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
"""API Library for gcloud scheduler CMEK config."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions


class RequiredFieldsMissingError(exceptions.Error):
  """Error for when calling a method when a required field is unspecified."""


class CmekConfig(object):
  """API client for Cloud Scheduler CMEK Config."""

  def __init__(self, messages, cmek_config_service):
    self.messages = messages
    self.cmek_config_service = cmek_config_service

  def GetCmekConfig(self, project_id, location_id):
    """Prepares and sends a GetCmekConfig request for the given CmekConfig."""
    cmek_config_name = (
        'projects/{project_id}/locations/{location_id}/cmekConfig'.format(
            project_id=project_id, location_id=location_id
        )
    )
    request = self.messages.CloudschedulerProjectsLocationsGetCmekConfigRequest(
        name=cmek_config_name,
    )

    return self.cmek_config_service.GetCmekConfig(request)

  def UpdateCmekConfig(self, project_id, location_id, cmek_config):
    """Prepares and sends an UpdateCmekConfig request for the given CmekConfig."""
    cmek_config_name = (
        'projects/{project_id}/locations/{location_id}/cmekConfig'.format(
            project_id=project_id, location_id=location_id
        )
    )
    request = (
        self.messages.CloudschedulerProjectsLocationsUpdateCmekConfigRequest(
            name=cmek_config_name, cmekConfig=cmek_config
        )
    )
    return self.cmek_config_service.UpdateCmekConfig(request)
