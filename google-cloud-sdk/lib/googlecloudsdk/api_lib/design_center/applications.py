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
"""API client library for Applications."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.design_center import utils
from googlecloudsdk.calliope import base


class ApplicationsClient(object):
  """Client for Applications in the Design Center API."""

  def __init__(self, release_track=base.ReleaseTrack.ALPHA):
    self.client = utils.GetClientInstance(release_track)
    self.messages = utils.GetMessagesModule(release_track)
    self._service = self.client.projects_locations_spaces_applications

  def ImportIac(self, name, gcs_uri=None, iac_module=None,
                allow_partial_import=False, validate_iac=False):
    """Calls the ImportApplicationIaC RPC.

    Args:
      name: str, The full resource name of the Application.
      gcs_uri: str, The GCS URI of the IaC source.
      iac_module: messages.IaCModule, The IaCModule object.
      allow_partial_import: bool, Whether to allow partial imports.
      validate_iac: bool, Whether to only validate the IaC.

    Returns:
      The response from the API call.
    """
    if not name:
      raise ValueError('Application name cannot be empty or None.')

    import_iac_request = self.messages.ImportApplicationIaCRequest(
        allowPartialImport=allow_partial_import,
        validateIac=validate_iac)

    if gcs_uri:
      import_iac_request.gcsUri = gcs_uri
    elif iac_module:
      import_iac_request.iacModule = iac_module

    request = (
        self.messages.DesigncenterProjectsLocationsSpacesApplicationsImportIaCRequest(
            name=name,
            importApplicationIaCRequest=import_iac_request))

    return self._service.ImportIaC(request)
