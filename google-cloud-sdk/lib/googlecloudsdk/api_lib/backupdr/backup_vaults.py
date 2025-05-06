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
from __future__ import annotations
from __future__ import division
from __future__ import unicode_literals

from collections.abc import Mapping, Sequence
import enum
from typing import Any

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.backupdr import util
from googlecloudsdk.command_lib.backupdr import util as command_util


class AccessRestriction(enum.Enum):
  WITHIN_PROJECT = 'within-project'
  WITHIN_ORGANIZATION = 'within-org'
  UNRESTRICTED = 'unrestricted'
  WITHIN_ORG_BUT_UNRESTRICTED_FOR_BA = 'within-org-but-unrestricted-for-ba'


class BackupVaultsClient(util.BackupDrClientBase):
  """Cloud Backup and DR Backup Vault client."""

  def __init__(self):
    super(BackupVaultsClient, self).__init__()
    self.service = self.client.projects_locations_backupVaults

  def Create(
      self,
      resource,
      backup_min_enforced_retention: str,
      description: str | None,
      labels: Mapping[str, str] | None,
      effective_time: str | None,
      access_restriction: str | None,
  ) -> Any:

    parent = resource.Parent().RelativeName()
    backup_vault_id = resource.Name()
    backup_vault = self.messages.BackupVault(
        backupMinimumEnforcedRetentionDuration=backup_min_enforced_retention,
        description=description,
        labels=labels,
        effectiveTime=effective_time,
        accessRestriction=self.ParseAccessRestrictionEnum(access_restriction),
    )
    request_id = command_util.GenerateRequestId()

    request = self.messages.BackupdrProjectsLocationsBackupVaultsCreateRequest(
        backupVault=backup_vault,
        backupVaultId=backup_vault_id,
        parent=parent,
        requestId=request_id,
    )
    return self.service.Create(request)

  def ParseAccessRestrictionEnum(self, access_restriction_str: str | None):
    if access_restriction_str is None:
      return (
          self.messages.BackupVault.AccessRestrictionValueValuesEnum.WITHIN_ORGANIZATION
      )

    access_restriction = AccessRestriction(access_restriction_str)

    if access_restriction == AccessRestriction.WITHIN_PROJECT:
      return (
          self.messages.BackupVault.AccessRestrictionValueValuesEnum.WITHIN_PROJECT
      )
    elif access_restriction == AccessRestriction.WITHIN_ORGANIZATION:
      return (
          self.messages.BackupVault.AccessRestrictionValueValuesEnum.WITHIN_ORGANIZATION
      )
    elif access_restriction == AccessRestriction.UNRESTRICTED:
      return (
          self.messages.BackupVault.AccessRestrictionValueValuesEnum.UNRESTRICTED
      )
    elif (
        access_restriction
        == AccessRestriction.WITHIN_ORG_BUT_UNRESTRICTED_FOR_BA
    ):
      return (
          self.messages.BackupVault.AccessRestrictionValueValuesEnum.WITHIN_ORG_BUT_UNRESTRICTED_FOR_BA
      )
    else:
      raise ValueError(f'Invalid access restriction: {access_restriction_str}')

  def Delete(
      self,
      resource,
      ignore_inactive_datasources: bool,
      ignore_backup_plan_references: bool,
      allow_missing: bool,
  ) -> Any:
    request_id = command_util.GenerateRequestId()
    request = self.messages.BackupdrProjectsLocationsBackupVaultsDeleteRequest(
        name=resource.RelativeName(),
        force=ignore_inactive_datasources,
        ignoreBackupPlanReferences=ignore_backup_plan_references,
        allowMissing=allow_missing,
        requestId=request_id,
    )

    return self.service.Delete(request)

  def List(
      self,
      parent_ref,
      limit=None,
      page_size: int = 100,
  ) -> Sequence[Any]:
    request = self.messages.BackupdrProjectsLocationsBackupVaultsListRequest(
        parent=parent_ref.RelativeName()
    )

    return list_pager.YieldFromList(
        self.service,
        request,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        limit=limit,
        field='backupVaults',
    )

  def ParseUpdate(
      self,
      description: str | None,
      effective_time: str | None,
      backup_min_enforced_retention: str | None,
      access_restriction: str | None,
  ):
    updated_bv = self.messages.BackupVault()
    if description is not None:
      updated_bv.description = description
    if effective_time is not None:
      updated_bv.effectiveTime = effective_time
    if backup_min_enforced_retention != 'Nones':
      updated_bv.backupMinimumEnforcedRetentionDuration = (
          backup_min_enforced_retention
      )
    if access_restriction is not None:
      access_restriction_enum = self.ParseAccessRestrictionEnum(
          access_restriction
      )
      updated_bv.accessRestriction = access_restriction_enum
    return updated_bv

  def Update(
      self,
      resource,
      backup_vault,
      force_update: bool,
      update_mask: str | None,
  ) -> Any:
    request_id = command_util.GenerateRequestId()
    request = self.messages.BackupdrProjectsLocationsBackupVaultsPatchRequest(
        backupVault=backup_vault,
        name=resource.RelativeName(),
        updateMask=update_mask,
        requestId=request_id,
        force=force_update,
    )
    return self.service.Patch(request)

  def Describe(self, resource) -> Any:
    request = self.messages.BackupdrProjectsLocationsBackupVaultsGetRequest(
        name=resource.RelativeName(),
    )

    return self.service.Get(request)
