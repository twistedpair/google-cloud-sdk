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
"""Helpers for taxonomy store related operations in Cloud Categoty Manager."""

from googlecloudsdk.api_lib.category_manager import utils
from googlecloudsdk.core import resources


def _GetService():
  """Gets the data policy annotation service."""
  return utils.GetClientInstance().taxonomyStores


def GetDefault(project_ref):
  """Makes an API call to the default taxonomy store for a project.

  Args:
    project_ref: A resource reference of a project. Use the current active
      project if not provided.

  Returns:
    A taxonomy store.
  """
  return _GetService().GetDefault(
      utils.GetMessagesModule().CategorymanagerTaxonomyStoresGetDefaultRequest(
          projectId=project_ref.projectId))


def GetDefaultStoreId(project_ref):
  """Get Id of the default store.

  Args:
    project_ref: A resource reference of a project. Use the current active
      project if not provided.

  Returns:
    Id of a taxonomy store.
  """
  return resources.REGISTRY.ParseRelativeName(
      GetDefault(project_ref).name,
      'categorymanager.taxonomyStores',
  ).taxonomyStoresId


def GetIamPolicy(store_ref):
  """Gets IAM policy for a given taxonomy store.

  Args:
    store_ref: a taxonomy store resource reference.

  Returns:
    An IamPolicy message.
  """
  messages = utils.GetMessagesModule()
  return _GetService().GetIamPolicy(
      messages.CategorymanagerTaxonomyStoresGetIamPolicyRequest(
          resource=store_ref.RelativeName(),
          getIamPolicyRequest=messages.GetIamPolicyRequest()))


def SetIamPolicy(store_ref, policy):
  """Sets IAM policy on a taxonomy store.

  Args:
    store_ref: a taxonomy store resource reference.
    policy: An IamPolicy message.

  Returns:
    An IamPolicy message.
  """
  messages = utils.GetMessagesModule()
  return _GetService().SetIamPolicy(
      messages.CategorymanagerTaxonomyStoresSetIamPolicyRequest(
          resource=store_ref.RelativeName(),
          setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy)))
