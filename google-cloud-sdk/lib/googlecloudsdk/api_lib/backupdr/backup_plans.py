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
"""Cloud Backup Plans client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from googlecloudsdk.api_lib.backupdr import util
from googlecloudsdk.command_lib.backupdr import util as command_util

# TODO: b/416214401 - Add type annotations.


class BackupPlansClient(util.BackupDrClientBase):
  """Cloud Backup Plans client."""

  def __init__(self):
    super(BackupPlansClient, self).__init__()
    self.service = self.client.projects_locations_backupPlans

  def _ParseBackupRules(self, backup_rules):
    backup_rules_message = []
    for backup_rule in backup_rules:
      standard_schedule = self.messages.StandardSchedule()
      standard_schedule.timeZone = (
          'UTC' if 'time-zone' not in backup_rule else backup_rule['time-zone']
      )
      standard_schedule.backupWindow = self.messages.BackupWindow(
          startHourOfDay=backup_rule['backup-window-start'],
          endHourOfDay=backup_rule['backup-window-end'],
      )
      standard_schedule.recurrenceType = (
          self.messages.StandardSchedule.RecurrenceTypeValueValuesEnum(
              backup_rule['recurrence']
          )
      )
      if 'hourly-frequency' in backup_rule:
        standard_schedule.hourlyFrequency = backup_rule['hourly-frequency']
      if 'days-of-week' in backup_rule:
        standard_schedule.daysOfWeek = [
            self.messages.StandardSchedule.DaysOfWeekValueListEntryValuesEnum(
                day
            )
            for day in backup_rule['days-of-week']
        ]
      if 'week-day-of-month' in backup_rule:
        week_day_of_month = backup_rule['week-day-of-month'].split('-')
        standard_schedule.weekDayOfMonth = self.messages.WeekDayOfMonth(
            weekOfMonth=self.messages.WeekDayOfMonth.WeekOfMonthValueValuesEnum(
                week_day_of_month[0]
            ),
            dayOfWeek=self.messages.WeekDayOfMonth.DayOfWeekValueValuesEnum(
                week_day_of_month[1]
            ),
        )
      if 'days-of-month' in backup_rule:
        standard_schedule.daysOfMonth = backup_rule['days-of-month']
      if 'months' in backup_rule:
        standard_schedule.months = [
            self.messages.StandardSchedule.MonthsValueListEntryValuesEnum(month)
            for month in backup_rule['months']
        ]
      backup_rule_message = self.messages.BackupRule(
          ruleId=backup_rule['rule-id'],
          backupRetentionDays=backup_rule['retention-days'],
          standardSchedule=standard_schedule,
      )
      backup_rules_message.append(backup_rule_message)
    return backup_rules_message

  def Create(
      self,
      resource,
      backup_vault,
      resource_type,
      backup_rules,
      log_retention_days,
      description,
      labels,
  ):
    """Creates a Backup Plan.

    Args:
      resource: The Backup Plan resource.
      backup_vault: The Backup Vault resource.
      resource_type: The resource type of the Backup Plan.
      backup_rules: The backup rules of the Backup Plan.
      log_retention_days: The log retention days of the Backup Plan.
      description: The description of the Backup Plan.
      labels: The labels of the Backup Plan.

    Returns:
      The created Backup Plan.
    """
    parent = resource.Parent().RelativeName()
    backup_plan_id = resource.Name()
    backup_plan = self.messages.BackupPlan(
        resourceType=resource_type,
        backupVault=backup_vault,
    )
    if description is not None:
      backup_plan.description = description
    if labels is not None:
      backup_plan.labels = self.messages.BackupPlan.LabelsValue(
          additionalProperties=[
              self.messages.BackupPlan.LabelsValue.AdditionalProperty(
                  key=key, value=value
              )
              for key, value in labels.items()
          ]
      )
    backup_plan.backupRules = self._ParseBackupRules(backup_rules)
    if log_retention_days is not None:
      backup_plan.logRetentionDays = log_retention_days
    request = self.messages.BackupdrProjectsLocationsBackupPlansCreateRequest(
        parent=parent,
        backupPlan=backup_plan,
        backupPlanId=backup_plan_id,
    )
    return self.service.Create(request)

  def Describe(self, resource):
    """Describes a Backup Plan.

    Args:
      resource: The Backup Plan resource.

    Returns:
      The described Backup Plan.
    """
    request = self.messages.BackupdrProjectsLocationsBackupPlansGetRequest(
        name=resource.RelativeName()
    )
    return self.service.Get(request)

  def ParseUpdate(
      self,
      description,
      new_backup_rules_from_file,
      update_backup_rules,
      add_backup_rules,
      remove_backup_rules,
      current_backup_plan,
      log_retention_days,
  ):
    """Parses the update request for a Backup Plan.

    Args:
      description: The description of the Backup Plan.
      new_backup_rules_from_file: The backup rules to update from file in the
        Backup Plan.
      update_backup_rules: The backup rules to update in the Backup Plan.
      add_backup_rules: The backup rules to add to the Backup Plan.
      remove_backup_rules: The backup rules to remove from the Backup Plan.
      current_backup_plan: The current Backup Plan.
      log_retention_days: The log retention days of the Backup Plan.

    Returns:
      The updated Backup Plan.

    Raises:
      ValueError: If the backup rules are invalid.
    """
    if current_backup_plan is None:
      raise ValueError('Could not find the backup plan.')
    updated_backup_plan = self.messages.BackupPlan(
        resourceType=current_backup_plan.resourceType
    )
    if description is not None:
      updated_backup_plan.description = description
    if log_retention_days is not None:
      updated_backup_plan.logRetentionDays = log_retention_days
    current_rule_ids = {rule.ruleId for rule in current_backup_plan.backupRules}
    if new_backup_rules_from_file is not None:
      updated_backup_plan.backupRules = self._ParseBackupRules(
          new_backup_rules_from_file
      )
      return updated_backup_plan
    if update_backup_rules is not None:
      rule_ids = collections.Counter(
          [rule['rule-id'] for rule in update_backup_rules]
      )
      duplicate_rule_ids = [
          rule_id for rule_id, count in rule_ids.items() if count > 1
      ]
      if duplicate_rule_ids:
        raise ValueError(
            f'Rules {duplicate_rule_ids} found in more than one '
            '--backup-rule flag.'
        )
      not_found_rule_ids = list(set([
          rule['rule-id']
          for rule in update_backup_rules
          if rule['rule-id'] not in current_rule_ids
      ]))
      if not_found_rule_ids:
        raise ValueError(
            f'Rules {not_found_rule_ids} not found in the backup plan.'
        )
      update_rule_ids = [rule['rule-id'] for rule in update_backup_rules]
      updated_backup_plan.backupRules = [
          rule
          for rule in current_backup_plan.backupRules
          if rule.ruleId not in update_rule_ids
      ]
      updated_backup_plan.backupRules.extend(
          self._ParseBackupRules(update_backup_rules)
      )
    else:
      updated_backup_plan.backupRules = current_backup_plan.backupRules
    if add_backup_rules is not None:
      updated_backup_plan.backupRules.extend(
          self._ParseBackupRules(add_backup_rules)
      )
    if remove_backup_rules is not None:
      not_found_rule_ids = list(set([
          rule_id
          for rule_id in remove_backup_rules
          if rule_id not in current_rule_ids
      ]))
      if not_found_rule_ids:
        raise ValueError(
            f'Rules {not_found_rule_ids} not found in the backup plan.'
        )
      updated_backup_plan.backupRules = [
          rule for rule in updated_backup_plan.backupRules
          if rule.ruleId not in remove_backup_rules
      ]
    return updated_backup_plan

  def Update(self, resource, backup_plan, update_mask):
    """Updates a Backup Plan.

    Args:
      resource: The Backup Plan resource.
      backup_plan: The updated Backup Plan.
      update_mask: The update mask to edit the Backup Plan.

    Returns:
      The updated Backup Plan.
    """
    request_id = command_util.GenerateRequestId()
    request = self.messages.BackupdrProjectsLocationsBackupPlansPatchRequest(
        backupPlan=backup_plan,
        name=resource.RelativeName(),
        requestId=request_id,
        updateMask=update_mask,
    )
    return self.service.Patch(request)

  def Delete(self, resource):
    """Deletes a Backup Plan.

    Args:
      resource: The Backup Plan resource.

    Returns:
      The deleted Backup Plan.
    """
    request = self.messages.BackupdrProjectsLocationsBackupPlansDeleteRequest(
        name=resource.RelativeName()
    )
    return self.service.Delete(request)
