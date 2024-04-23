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
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core.util import times


def GenerateRequestId():
  return str(uuid.uuid4())


def ConvertIntToStr(duration):
  return str(duration) + 's'


def TransformTo12AmUtcTime(effective_time):
  """Transforms the datetime object to UTC time string fixed at 12AM.

  Args:
    effective_time: Date to be converted to UTC time string fixed at 12AM.

  Returns:
    UTC time.

  Raises:
    ArgumentTypeError: If the date is not in the future.
  """
  if effective_time is None:
    return None
  if effective_time < times.Now().date():
    raise exceptions.InvalidArgumentException(
        'Date must be in the future: {0}'.format(effective_time),
        'effective_time',
    )
  year = effective_time.year
  month = effective_time.month
  day = effective_time.day
  effective_time = datetime.datetime(
      year, month, day, 0, 0, 0, 0, datetime.timezone.utc
  ).strftime('%Y-%m-%dT%H:%M:%SZ')
  return effective_time


def ResetEnforcedRetention():
  return '0001-01-01T00:00:00.000Z'


# TODO: b/332661929 - Add unit tests for this class.
class OptionsMapValidator(object):
  """Option that are passed as key(alternative) value(actual) pairs are validated on the args."""

  def __init__(self, options):
    self.key_len = max(len(option) for option in options.keys())
    self.options = options

  def IsValid(self, s):
    if not s:
      return False
    return s[: self.key_len].upper() in self.options.keys()

  def Parse(self, s):
    if not self.IsValid(s):
      raise arg_parsers.ArgumentTypeError(
          'Failed to parse the arg ({}). Value should be one of {}'.format(
              s, ', '.join(self.options.keys())
          )
      )
    return self.options.get(s[: self.key_len].upper(), 'UNKNOWN')
