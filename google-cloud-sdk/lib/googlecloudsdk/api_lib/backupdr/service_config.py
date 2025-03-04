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
"""Cloud Backup and DR Service Config client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.backupdr import util


class ServiceConfigClient(util.BackupDrClientBase):
  """Cloud Backup and DR Service Config client."""

  def __init__(self):
    super(ServiceConfigClient, self).__init__()
    self.service = self.client.projects_locations_serviceConfig

  def Init(self, location, resource_type):
    """Calls the Backup and DR Initialize service.

    Args:
      location: location of the service config.
      resource_type: resource type for which the service config is being
        initialized.

    Returns:
      A long running operation
    """
    name = f'{location}/serviceConfig'
    request = (
        self.messages.BackupdrProjectsLocationsServiceConfigInitializeRequest(
            name=name,
            initializeServiceRequest=self.messages.InitializeServiceRequest(
                resourceType=resource_type,
            ),
        )
    )
    return self.service.Initialize(request)
