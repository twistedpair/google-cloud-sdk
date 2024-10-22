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
"""Utilities for Audit Manager API, Operations Endpoints."""

from googlecloudsdk.api_lib.audit_manager import constants
from googlecloudsdk.api_lib.audit_manager import util


class OperationsClient(object):
  """Client for operations in Audit Manager API."""

  def __init__(
      self, api_version: constants.ApiVersion, client=None, messages=None
  ) -> None:
    self.client = client or util.GetClientInstance(api_version=api_version)
    self.messages = messages or util.GetMessagesModule(
        api_version=api_version, client=client
    )

  def Get(self, name: str, is_parent_folder: bool):
    """Describe an Audit Manager operation.

    Args:
      name: The name of the Audit Operation being described.
      is_parent_folder: Whether the parent is folder and not project.

    Returns:
      Described audit operation resource.
    """
    service = (
        self.client.folders_locations_operationDetails
        if is_parent_folder
        else self.client.projects_locations_operationDetails
    )

    req = (
        self.messages.AuditmanagerFoldersLocationsOperationDetailsGetRequest()
        if is_parent_folder
        else self.messages.AuditmanagerProjectsLocationsOperationDetailsGetRequest()
    )

    req.name = name
    return service.Get(req)
