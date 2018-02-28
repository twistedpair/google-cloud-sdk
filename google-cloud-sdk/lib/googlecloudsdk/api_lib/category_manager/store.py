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
"""Helpers for taxonomy store related operations in Cloud Category Manager."""

from googlecloudsdk.api_lib.category_manager import utils


def GetTaxonomyStoreFromOrgRef(org_ref):
  """Gets a taxonomy store from an organization reference.

  Args:
    org_ref: An organization reference object.

  Returns:
    A TaxonomyStore message.
  """
  messages = utils.GetMessagesModule()
  req = messages.CategorymanagerOrganizationsGetTaxonomyStoreRequest(
      parent=org_ref.RelativeName())
  return utils.GetClientInstance().organizations.GetTaxonomyStore(request=req)


def GetIamPolicy(store_ref):
  """Gets IAM policy for a given taxonomy store.

  Args:
    store_ref: a taxonomy store resource reference.

  Returns:
    An IamPolicy message.
  """
  messages = utils.GetMessagesModule()
  return utils.GetClientInstance().taxonomyStores.GetIamPolicy(
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
  return utils.GetClientInstance().taxonomyStores.SetIamPolicy(
      messages.CategorymanagerTaxonomyStoresSetIamPolicyRequest(
          resource=store_ref.RelativeName(),
          setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy)))
