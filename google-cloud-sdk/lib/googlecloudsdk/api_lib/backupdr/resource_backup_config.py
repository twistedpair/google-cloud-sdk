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
"""Resource Backup Configs API Client for Protection Summary."""

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.backupdr import util
from googlecloudsdk.calliope import exceptions


class ResourceBackupConfigClient(util.BackupDrClientBase):
  """Resource Backup Configs API Client for Protection Summary."""

  def __init__(self):
    super(ResourceBackupConfigClient, self).__init__()
    self.service = self.client.projects_locations_resourceBackupConfigs

  def List(self, parent, filters, page_size=None, limit=None, order_by=None):
    request = (
        self.messages.BackupdrProjectsLocationsResourceBackupConfigsListRequest(
            parent=parent,
            filter=filters,
            pageSize=page_size,
            orderBy=order_by,
        )
    )
    try:
      for resource in list_pager.YieldFromList(
          self.service,
          request,
          batch_size_attribute='pageSize',
          batch_size=page_size,
          limit=limit,
          field='resourceBackupConfigs',
      ):
        yield resource
    except apitools_exceptions.HttpError as e:
      raise exceptions.HttpException(e, util.HTTP_ERROR_FORMAT)

  def Get(self, name):
    request = (
        self.messages.BackupdrProjectsLocationsResourceBackupConfigsGetRequest(
            name=name
        )
    )
    return self.service.Get(request)
