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
"""Cloud Backup and DR Backup plan associations client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.backupdr import util
from googlecloudsdk.core import resources
from googlecloudsdk.generated_clients.apis.backupdr.v1 import backupdr_v1_messages


class BackupPlanAssociationsClient(util.BackupDrClientBase):
  """Cloud Backup and DR Backup plan associations client."""

  def __init__(self):
    super(BackupPlanAssociationsClient, self).__init__()
    self.service = self.client.projects_locations_backupPlanAssociations

  def Create(self, bpa_resource, backup_plan, workload_resource):
    parent = bpa_resource.Parent().RelativeName()
    bpa_id = bpa_resource.Name()
    bpa = self.messages.BackupPlanAssociation(
        backupPlan=backup_plan.RelativeName(),
        resource=workload_resource,
    )

    request = self.messages.BackupdrProjectsLocationsBackupPlanAssociationsCreateRequest(
        parent=parent,
        backupPlanAssociation=bpa,
        backupPlanAssociationId=bpa_id,
    )
    return self.service.Create(request)

  def Delete(self, resource):
    request = self.messages.BackupdrProjectsLocationsBackupPlanAssociationsDeleteRequest(
        name=resource.RelativeName()
    )
    return self.service.Delete(request)

  def TriggerBackup(
      self, resource: resources.Resource, backup_rule: str
  ) -> backupdr_v1_messages.Operation:
    """Triggers an on demand backup according to the given backup rule.

    Args:
      resource: The backup plan association resource.
      backup_rule: The backup rule to be used for the adhoc backup

    Returns:
      A long running operation
    """
    trigger_backup_request = self.messages.TriggerBackupRequest(
        ruleId=backup_rule,
    )
    request = self.messages.BackupdrProjectsLocationsBackupPlanAssociationsTriggerBackupRequest(
        name=resource.RelativeName(),
        triggerBackupRequest=trigger_backup_request,
    )
    return self.service.TriggerBackup(request)
