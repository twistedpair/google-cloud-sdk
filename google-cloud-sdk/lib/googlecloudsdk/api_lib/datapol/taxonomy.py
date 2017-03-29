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
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.api_lib.datapol import utils
from googlecloudsdk.command_lib.projects import util as projects_util
from googlecloudsdk.core import properties

# Organization Id place holder for projects that do not belong to any
# organizations.
_ORG_ID_PLACE_HOLDER = '_NO_ORGS_'


def _GetProjectName():
  """Gets name of the current project."""
  return properties.VALUES.core.project.Get(required=True)


def _GetOrganizationId():
  """Gets id of current organization."""
  proj = projects_api.Get(projects_util.ParseProject(_GetProjectName()))
  return (proj.parent.id if proj.parent and proj.parent.type == 'organization'
          else _ORG_ID_PLACE_HOLDER)


_ORG_PATTERN = 'orgs/{0}'


def _GetService():
  """Gets the data policy taxonomiy service."""
  return utils.GetClientInstance().orgs_policyTaxonomies


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
  org_id = _GetOrganizationId()
  return _GetService().Create(
      messages.DatapolOrgsPolicyTaxonomiesCreateRequest(
          parent=_ORG_PATTERN.format(org_id),
          policyTaxonomy=messages.PolicyTaxonomy(
              orgId=org_id, taxonomyName=taxonomy_name, description=
              description)))


def Delete(name):
  """Makes an API call to delete a taxonomy.

  Args:
    name: Resource name of the taxonomy.

  Returns:
    An Operation message which can be used to check on the progress of the
    project creation.
  """
  return _GetService().Delete(
      utils.GetMessagesModule().DatapolOrgsPolicyTaxonomiesDeleteRequest(
          name=name))


def Get(name):
  """Makes an API call to get the definition of a taxonomy.

  Args:
    name: Resource name of the taxonomy.

  Returns:
    A Taxonomy message.
  """
  return _GetService().Get(utils.GetMessagesModule()
                           .DatapolOrgsPolicyTaxonomiesGetRequest(name=name))


def List(limit=None):
  """Makes API calls to list taxonomies under the current organization.

  Args:
    limit: The number of taxonomies to limit the resutls to.

  Returns:
    Generator that yields taxonomies
  """
  request = utils.GetMessagesModule().DatapolOrgsPolicyTaxonomiesListRequest(
      parent=_ORG_PATTERN.format(_GetOrganizationId()))
  return list_pager.YieldFromList(
      _GetService(),
      request,
      limit=limit,
      field='taxonomies',
      batch_size_attribute='pageSize')


def GetIamPolicy(resource):
  """Gets IAM policy for a given taxonomy.

  Args:
    resource: Resource name of the taxonomy.

  Returns:
    An IamPolicy message.
  """
  messages = utils.GetMessagesModule()
  return _GetService().GetIamPolicy(
      messages.DatapolOrgsPolicyTaxonomiesGetIamPolicyRequest(
          resource=resource, getIamPolicyRequest=
          messages.GetIamPolicyRequest()))


def SetIamPolicy(resource, policy):
  """Sets IAM policy, for a given taxonomy.

  Args:
    resource: Resource name of the taxonomy.
    policy: An IamPolicy message.

  Returns:
    An IamPolicy message.
  """
  messages = utils.GetMessagesModule()
  return _GetService().SetIamPolicy(
      messages.DatapolOrgsPolicyTaxonomiesSetIamPolicyRequest(
          resource=resource,
          setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy)))
