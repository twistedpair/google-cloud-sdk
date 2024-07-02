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

from googlecloudsdk.api_lib.backupdr import util


class BackupPlansClient(util.BackupDrClientBase):
  """Cloud Backup Plans client."""

  def __init__(self):
    super(BackupPlansClient, self).__init__()
    self.service = self.client.projects_locations_backupPlans

  def Create(
      self,
      resource,
      backup_vault,
      resource_type,
      backup_rules,
      description,
      labels,
  ):
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
      backup_plan.backupRules.append(backup_rule_message)
    request = self.messages.BackupdrProjectsLocationsBackupPlansCreateRequest(
        parent=parent,
        backupPlan=backup_plan,
        backupPlanId=backup_plan_id,
    )
    return self.service.Create(request)

  def Delete(self, resource):
    request = self.messages.BackupdrProjectsLocationsBackupPlansDeleteRequest(
        name=resource.RelativeName()
    )
    return self.service.Delete(request)
