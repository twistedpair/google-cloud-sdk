# -*- coding: utf-8 -*- #
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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.category_manager import utils


def GetTaxonomyStoreFromOrgResource(org_resource):
  """Gets a taxonomy store from an organization resource.

  Args:
    org_resource: A cloudresourcemanager.organizations core.Resource object.

  Returns:
    A TaxonomyStore message.
  """
  messages = utils.GetMessagesModule()
  req = messages.CategorymanagerOrganizationsGetTaxonomyStoreRequest(
      parent=org_resource.RelativeName())
  return utils.GetClientInstance().organizations.GetTaxonomyStore(request=req)


def GetIamPolicy(taxonomy_store_resource):
  """Gets IAM policy for a given taxonomy store.

  Args:
    taxonomy_store_resource: A categorymanager.taxonomyStores core.Resource
      object.

  Returns:
    An IamPolicy message.
  """
  messages = utils.GetMessagesModule()
  return utils.GetClientInstance().taxonomyStores.GetIamPolicy(
      messages.CategorymanagerTaxonomyStoresGetIamPolicyRequest(
          resource=taxonomy_store_resource.RelativeName(),
          getIamPolicyRequest=messages.GetIamPolicyRequest()))


def SetIamPolicy(taxonomy_store_resource, policy):
  """Sets IAM policy on a taxonomy store.

  Args:
    taxonomy_store_resource: A categorymanager.taxonomyStores core.Resource
      object.
    policy: An IamPolicy message.

  Returns:
    An IamPolicy message.
  """
  messages = utils.GetMessagesModule()
  return utils.GetClientInstance().taxonomyStores.SetIamPolicy(
      messages.CategorymanagerTaxonomyStoresSetIamPolicyRequest(
          resource=taxonomy_store_resource.RelativeName(),
          setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy)))


def GetCommonStore():
  """Gets the common taxonomy store."""
  messages = utils.GetMessagesModule()
  return utils.GetClientInstance().taxonomyStores.GetCommon(
      messages.CategorymanagerTaxonomyStoresGetCommonRequest())
