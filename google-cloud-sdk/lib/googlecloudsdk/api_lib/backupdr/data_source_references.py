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
"""Cloud Backup and DR Backup plan associations client."""

from googlecloudsdk.api_lib.backupdr import util
from googlecloudsdk.core import properties


class DataSourceReferencesClient(util.BackupDrClientBase):
  """Cloud Backup and DR Data Source References client."""

  def __init__(self):
    super(DataSourceReferencesClient, self).__init__()
    self.service = self.client.projects_locations_dataSourceReferences

  def FetchForResourceType(
      self,
      location,
      resource_type,
      filter_expression=None,
      page_size=None,
      order_by=None,
  ):
    project = properties.VALUES.core.project.GetOrFail()
    parent = 'projects/{}/locations/{}'.format(project, location)
    request = self.messages.BackupdrProjectsLocationsDataSourceReferencesFetchForResourceTypeRequest(
        parent=parent,
        resourceType=resource_type,
        pageSize=page_size,
        filter=filter_expression,
        orderBy=order_by,
    )
    return self.service.FetchForResourceType(request)
