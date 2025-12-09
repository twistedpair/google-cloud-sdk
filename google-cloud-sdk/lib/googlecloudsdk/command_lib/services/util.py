# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Utilities for services commands."""


_SERVICE_RESOURCE = 'services/'
_GROUP_RESOURCE = 'groups/'


def GetGroupName(service, group):
  """Constructs the group resource name.

  Args:
    service: The service name.
    group: The group name.

  Returns:
    The full group resource name.
  """
  if not service.startswith(_SERVICE_RESOURCE):
    service = _SERVICE_RESOURCE + service
  if not group.startswith(_GROUP_RESOURCE):
    group = _GROUP_RESOURCE + group
  return f'{service}/{group}'


def IsValidGroupName(service, group):
  """Validates the group name.

  Args:
    service: The service name.
    group: The group name.

  Returns:
    True if the group name is valid, False otherwise.
  """
  group_name = GetGroupName(service, group)
  split_group_name = group_name.split('/')
  return (
      len(split_group_name) == 4
      and split_group_name[0] == 'services'
      and split_group_name[2] == 'groups'
  )
