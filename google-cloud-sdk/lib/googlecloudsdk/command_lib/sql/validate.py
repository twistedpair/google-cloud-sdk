# -*- coding: utf-8 -*- #
# Copyright 2017 Google LLC. All Rights Reserved.
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
"""Common validation methods for some SQL commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re
from googlecloudsdk.api_lib.sql import validate as api_validate
from googlecloudsdk.calliope import arg_parsers


def InstanceNameRegexpValidator():
  """Returns a function that validates an instance name using predefined rules.

  Returns:
    function: str -> str, usable as an argparse type
  """

  # : and . are not valid characters, but we allow them through this regex so
  # that we can give a better error message using ValidateInstanceName, below.
  pattern = r'^[a-z][a-z0-9-:.]*'
  description = ('must be composed of lowercase letters, numbers, and hyphens; '
                 'must start with a letter.')

  def Parse(value):
    if not re.match(pattern + '$', value):
      raise arg_parsers.ArgumentTypeError(
          'Bad value [{0}]: {1}'.format(value, description))
    api_validate.ValidateInstanceName(value)
    return value

  return Parse


def IsProjectLevelBackupRequest(backup_id):
  """Checks if the backup request is project level.

  Project level requests will have backup_id in string format whearas they will
  be integer values for instance level backup requests.

  Args:
    backup_id: The id of the requested backup.

  Returns:
    True if is a project level backup request.
  """
  try:
    int(backup_id)
  except ValueError:
    return True
  else:
    return False


def IsBackupDrBackupRequest(backup_id: str) -> bool:
  """Checks if the backup request is a backupdr backup by checking if the backup id contains /backupVaults.

  A backupdr backup will have the backup in the format of
  projects/{project}/locations/{location}/backupVaults/{backup_vault}/dataSources/{data_source}/backups/{backup}.

  Args:
    backup_id: The id of the requested backup.

  Returns:
    True if the request is a backupdr backup request.
  """
  return backup_id and '/backupVaults' in backup_id
