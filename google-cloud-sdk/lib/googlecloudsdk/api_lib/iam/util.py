# Copyright 2018 Google Inc. All Rights Reserved.
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

"""Utilities for IAM commands to call IAM APIs."""

from apitools.base.py import list_pager
from googlecloudsdk.command_lib.iam import iam_util


def GetTestablePermissions(iam_client, messages, resource):
  """Returns the testable permissions for a resource.

  Args:
    iam_client: The iam client.
    messages: The iam messages.
    resource: Resource reference.

  Returns:
    List of permissions.
  """
  return list_pager.YieldFromList(
      iam_client.permissions,
      messages.QueryTestablePermissionsRequest(
          fullResourceName=iam_util.GetResourceName(resource), pageSize=1000),
      batch_size=1000,
      method='QueryTestablePermissions',
      field='permissions',
      batch_size_attribute='pageSize')


def GetTestingPermissions(iam_client, messages, resource, permissions):
  """Returns the TESTING permissions among the permissions provided.

  Args:
    iam_client: The iam client.
    messages: The iam messages.
    resource: Resource reference for the project/organization whose permissions
    are being inspected.
    permissions: A list of permissions to inspect.

  Returns:
    List of TESTING permissions among the given permissions.
  """
  return GetValidAndTestingPermissions(iam_client, messages, resource,
                                       permissions)[1]


def GetValidAndTestingPermissions(iam_client, messages, resource, permissions):
  """Returns the valid and TESTING permissions among the permissions provided.

  Args:
    iam_client: The iam client.
    messages: The iam messages.
    resource: Resource reference for the project/organization whose permissions
    are being inspected.
    permissions: A list of permissions to inspect.

  Returns:
    List of valid permissions to create among the given permissions.
    List of TESTING permissions among the given permissions.
  """
  if not permissions:
    return [], []
  valid_permissions = []
  testing_permissions = []
  source_permissions = set(permissions)
  testable_permissions = GetTestablePermissions(iam_client, messages, resource)
  for testable_permission in testable_permissions:
    if (testable_permission.name in source_permissions and
        (testable_permission.customRolesSupportLevel !=
         messages.Permission.CustomRolesSupportLevelValueValuesEnum.
         NOT_SUPPORTED)):
      valid_permissions.append(testable_permission.name)
    if (testable_permission.name in source_permissions and
        (testable_permission.customRolesSupportLevel == messages.
         Permission.CustomRolesSupportLevelValueValuesEnum.TESTING)):
      testing_permissions.append(testable_permission.name)
  return valid_permissions, testing_permissions
