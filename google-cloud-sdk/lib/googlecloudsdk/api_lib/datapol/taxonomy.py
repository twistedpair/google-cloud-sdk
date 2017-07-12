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
"""Helpers to interact with the Taxonomy serivce via the Cloud Datapol API."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.datapol import utils
from googlecloudsdk.core import resources


def _GetService():
  """Gets the data policy taxonomiy service."""
  return utils.GetClientInstance().taxonomyStores_dataTaxonomies


def Create(taxonomy_name, description):
  """Makes an API call to create a taxonomy.

  Args:
    taxonomy_name: Name of the taxononmy. Needs to be unique within the
      organization.
    description: A short description to the taxonomy.

  Returns:
    A Taxonomy message.
  """
  messages = utils.GetMessagesModule()
  return _GetService().Create(
      messages.DatapolTaxonomyStoresDataTaxonomiesCreateRequest(
          parent=resources.REGISTRY.Create(
              'datapol.taxonomyStores',
              taxonomyStoresId=utils.GetTaxonomyStoresId()).RelativeName(),
          dataTaxonomy=messages.DataTaxonomy(
              displayName=taxonomy_name, description=description)))


def Delete(taxonomy_id):
  """Makes an API call to delete a taxonomy.

  Args:
    taxonomy_id: Id of the taxonomy.

  Returns:
    An Operation message which can be used to check on the progress of taxonomy
    deletion.
  """
  return _GetService().Delete(utils.GetMessagesModule(
  ).DatapolTaxonomyStoresDataTaxonomiesDeleteRequest(
      name=utils.GetTaxonomyRelativeName(taxonomy_id)))


def Get(taxonomy_id):
  """Makes an API call to get the definition of a taxonomy.

  Args:
    taxonomy_id: Name of the taxonomy.

  Returns:
    A Taxonomy message.
  """
  return _GetService().Get(
      utils.GetMessagesModule().DatapolTaxonomyStoresDataTaxonomiesGetRequest(
          name=utils.GetTaxonomyRelativeName(taxonomy_id)))


def List(limit=None):
  """Makes API calls to list taxonomies under the current organization.

  Args:
    limit: The number of taxonomies to limit the resutls to.

  Returns:
    Generator that yields taxonomies
  """
  request = utils.GetMessagesModule(
  ).DatapolTaxonomyStoresDataTaxonomiesListRequest(
      parent=resources.REGISTRY.Create(
          'datapol.taxonomyStores',
          taxonomyStoresId=utils.GetTaxonomyStoresId()).RelativeName())
  return list_pager.YieldFromList(
      _GetService(),
      request,
      limit=limit,
      field='taxonomies',
      batch_size_attribute='pageSize')


def GetIamPolicy(taxonomy_id):
  """Gets IAM policy for a given taxonomy.

  Args:
    taxonomy_id: Id of the taxonomy.

  Returns:
    An IamPolicy message.
  """
  messages = utils.GetMessagesModule()
  return _GetService().GetIamPolicy(
      messages.DatapolTaxonomyStoresDataTaxonomiesGetIamPolicyRequest(
          resource=utils.GetTaxonomyRelativeName(taxonomy_id),
          getIamPolicyRequest=messages.GetIamPolicyRequest()))


def SetIamPolicy(taxonomy_id, policy):
  """Sets IAM policy, for a given taxonomy.

  Args:
    taxonomy_id: Id of the taxonomy.
    policy: An IamPolicy message.

  Returns:
    An IamPolicy message.
  """
  messages = utils.GetMessagesModule()
  return _GetService().SetIamPolicy(
      messages.DatapolTaxonomyStoresDataTaxonomiesSetIamPolicyRequest(
          resource=utils.GetTaxonomyRelativeName(taxonomy_id),
          setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy)))
