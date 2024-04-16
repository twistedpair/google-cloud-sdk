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
  ):

    parent = resource.Parent().RelativeName()
    backup_vault_id = resource.Name()
    backup_vault = self.messages.BackupVault(
        enforcedRetentionDuration=enforced_retention,
        description=description,
        labels=labels,
        effectiveTime=effective_time,
    )
    request_id = command_util.GenerateRequestId()

    request = self.messages.BackupdrProjectsLocationsBackupVaultsCreateRequest(
        backupVault=backup_vault,
        backupVaultId=backup_vault_id,
        parent=parent,
        requestId=request_id,
    )
    return self.service.Create(request)

  def Delete(self, resource, force_delete):
    request_id = command_util.GenerateRequestId()
    request = self.messages.BackupdrProjectsLocationsBackupVaultsDeleteRequest(
        name=resource.RelativeName(), force=force_delete, requestId=request_id
    )

    return self.service.Delete(request)

  def ParseUpdate(self, description, effective_time, enforced_retention):
    updated_bv = self.messages.BackupVault()
    if description is not None:
      updated_bv.description = description
    if effective_time is not None:
      updated_bv.effectiveTime = effective_time
    if enforced_retention != "Nones":
      updated_bv.enforcedRetentionDuration = enforced_retention
    return updated_bv

  def Update(self, resource, backup_vault, update_mask):
    request_id = command_util.GenerateRequestId()
    request = self.messages.BackupdrProjectsLocationsBackupVaultsPatchRequest(
        backupVault=backup_vault,
        name=resource.RelativeName(),
        updateMask=update_mask,
        requestId=request_id,
    )
    return self.service.Patch(request)
