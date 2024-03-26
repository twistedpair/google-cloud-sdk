# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Utilities for Backup and DR commands."""

import datetime
import uuid

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import times


def SetGlobalLocation():
  """Set default location to global."""
  return '-'


def SetDefaultBackupVault():
  """Set default backup vault value to use wildcards."""
  project = properties.VALUES.core.project.Get()
  return 'projects/{}/locations/-/backupVaults/-'.format(project)


def GenerateRequestId():
  return str(uuid.uuid4())


def ConvertIntToStr(duration):
  return str(duration) + 's'


def ConvertUtcTime(effective_time):
  """Converts the date to UTC time.

  Args:
    effective_time: Date to be converted to UTC time.

  Returns:
    UTC time.

  Raises:
    ArgumentTypeError: If the date is not in the future.
  """
  if effective_time is None:
    return None
  if effective_time < times.Now().date():
    raise arg_parsers.ArgumentTypeError(
        'Date must be in the future: {0}'.format(effective_time)
    )
  year = effective_time.year
  month = effective_time.month
  day = effective_time.day
  effective_time = datetime.datetime(
      year, month, day, 0, 0, 0, 0, datetime.timezone.utc
  ).strftime('%Y-%m-%dT%H:%M:%SZ')
  return effective_time
