# -*- coding: utf-8 -*- #
# Copyright 2024 Google Inc. All Rights Reserved.
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
"""Cloud Backup and DR Backup Vaults client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.backupdr import util
from googlecloudsdk.command_lib.backupdr import util as command_util


class BackupVaultsClient(util.BackupDrClientBase):
  """Cloud Backup and DR Backup Vault client."""

  def __init__(self):
    super(BackupVaultsClient, self).__init__()
    self.service = self.client.projects_locations_backupVaults

  def Create(
      self,
      resource,
      enforced_retention,
      description,
      labels,
      effective_time,
      request_id,
  ):

    parent = resource.Parent().RelativeName()
    backup_vault_id = resource.Name()
    backup_vault = self.messages.BackupVault(
        enforcedRetentionDuration=enforced_retention,
        description=description,
        labels=labels,
        effectiveTime=effective_time,
    )

    if request_id:
      request = (
          self.messages.BackupdrProjectsLocationsBackupVaultsCreateRequest(
              backupVault=backup_vault,
              backupVaultId=backup_vault_id,
              parent=parent,
              requestId=command_util.GenerateRequestId(),
          )
      )
    else:
      request = (
          self.messages.BackupdrProjectsLocationsBackupVaultsCreateRequest(
              backupVault=backup_vault,
              backupVaultId=backup_vault_id,
              parent=parent,
          )
      )
    return self.service.Create(request)

  def Delete(self, resource, force_delete, request_id):
    if request_id:
      request = (
          self.messages.BackupdrProjectsLocationsBackupVaultsDeleteRequest(
              name=resource.RelativeName(),
              force=force_delete,
              requestId=command_util.GenerateRequestId(),
          )
      )
    else:
      request = (
          self.messages.BackupdrProjectsLocationsBackupVaultsDeleteRequest(
              name=resource.RelativeName(), force=force_delete
          )
      )
    return self.service.Delete(request)
