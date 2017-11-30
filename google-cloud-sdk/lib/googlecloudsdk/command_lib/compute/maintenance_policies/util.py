# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Utility functions for Google Compute Engine maintenance policies."""
from googlecloudsdk.core.util import times


def FormatStartTime(dt):
  return times.FormatDateTime(dt, '%H:%M', times.UTC)


def MakeMaintenancePolicy(policy_ref, args, messages):
  start_time = FormatStartTime(args.start_time)
  region = policy_ref.region
  vm_policy = messages.VmMaintenancePolicy(
      maintenanceWindow=messages.MaintenanceWindow(
          dailyMaintenanceWindow=messages.DailyMaintenanceWindow(
              daysInCycle=args.days_in_cycle,
              startTime=start_time)))
  return messages.MaintenancePolicy(
      name=policy_ref.Name(),
      description=args.description,
      region=region,
      vmMaintenancePolicy=vm_policy)


def GetRegionFromZone(zone):
  return '-'.join(zone.split('-')[:-1])


def ParseMaintenancePolicy(resources, name, project=None, region=None):
  return resources.Parse(
      name, {'project': project, 'region': region},
      collection='compute.maintenancePolicies')
