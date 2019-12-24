# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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

"""A library that is used to support Functions commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis


def GetResourceManagerApiClientInstance():
  return apis.GetClientInstance('cloudresourcemanager', 'v1')


def CanSetProjectIamPolicyBinding(project):
  """Returns True iff the caller can set policy bindings for project."""
  client = GetResourceManagerApiClientInstance()
  messages = client.MESSAGES_MODULE
  needed_permissions = [
      'resourcemanager.projects.getIamPolicy',
      'resourcemanager.projects.setIamPolicy']
  iam_request = messages.CloudresourcemanagerProjectsTestIamPermissionsRequest(
      resource=project,
      testIamPermissionsRequest=messages.TestIamPermissionsRequest(
          permissions=needed_permissions))
  iam_response = client.projects.TestIamPermissions(iam_request)
  for needed_permission in needed_permissions:
    if needed_permission not in iam_response.permissions:
      return False
  return True
