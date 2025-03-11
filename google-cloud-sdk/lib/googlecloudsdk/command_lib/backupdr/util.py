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

import math
import uuid

from dateutil import tz
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core.util import iso_duration
from googlecloudsdk.core.util import times


def GenerateRequestId():
  return str(uuid.uuid4())


def ConvertIntToStr(duration):
  return str(duration) + 's'


def VerifyDateInFuture(date, flag):
  """Verify that the date is in the future."""
  if date is None:
    return None
  if date < times.Now():
    raise exceptions.InvalidArgumentException(
        flag,
        'Date must be in the future: {0}'.format(date)
    )
  date = date.astimezone(tz.tzutc())
  return date.strftime('%Y-%m-%dT%H:%M:%SZ')


def ResetEnforcedRetention():
  return '0001-01-01T00:00:00.000Z'


class OptionsMapValidator(object):
  """Option that are passed as key(alternative) value(actual) pairs are validated on the args."""

  def __init__(self, options):
    self.options = {opt.upper(): options[opt] for opt in options}

  def Parse(self, s):
    if s.upper() in self.options.keys():
      return self.options[s.upper()]
    elif s in self.options.values():
      return s
    else:
      raise arg_parsers.ArgumentTypeError(
          'Failed to parse the arg ({}). Value should be one of {}'.format(
              s,
              ', '.join(
                  list(self.options.keys()) + list(self.options.values())
              ),
          )
      )


def TransformEnforcedRetention(backup_vault):
  """Transforms the backup vault enforced retention to a human readable format.

  Args:
    backup_vault: type of backup_vault can be either a Backup vault object or a
      dict.

  Returns:
    Human readable format of backup vault enforced retention.
  """

  if isinstance(backup_vault, dict):
    backup_min_enforced_retention = backup_vault.get(
        'backupMinimumEnforcedRetentionDuration', {}
    )
  else:
    backup_min_enforced_retention = (
        backup_vault.backupMinimumEnforcedRetentionDuration
    )

  if not backup_min_enforced_retention:
    return ''

  seconds_in_hour = 3600
  seconds_in_day = 86400
  seconds_in_month = 2629744
  seconds_in_year = 31556926

  seconds = times.ParseDuration(backup_min_enforced_retention).total_seconds

  year = math.floor(seconds / seconds_in_year)
  remaining_seconds = seconds % seconds_in_year
  month = math.floor(remaining_seconds / seconds_in_month)
  remaining_seconds %= seconds_in_month
  day = math.floor(remaining_seconds / seconds_in_day)
  remaining_seconds %= seconds_in_day
  hour = math.ceil(remaining_seconds / seconds_in_hour)
  duration = iso_duration.Duration(
      years=year, months=month, days=day, hours=hour
  )
  return times.FormatDuration(duration, parts=-1)


def GetOneOfValidator(name, options):
  validtor = arg_parsers.CustomFunctionValidator(
      lambda arg: arg in options,
      '{} should be one of the following: '.format(name) + ', '.join(options),
      str,
  )
  return validtor


class EnumMapper(object):
  """Maps the args to Enum values."""

  def __init__(self, enum_mapping):
    self.enum_mapping = enum_mapping

  def Parse(self, s):
    if s in self.enum_mapping:
      return self.enum_mapping[s]
    else:
      raise arg_parsers.ArgumentTypeError(
          'Failed to parse the arg ({}). Value should be one of {}'.format(
              s,
              ', '.join(list(self.enum_mapping.keys())),
          )
      )
