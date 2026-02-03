# -*- coding: utf-8 -*- #
# Copyright 2018 Google LLC. All Rights Reserved.
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
"""services helper functions."""
import collections
import copy
import enum
import json
import sys
from typing import List

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.services import exceptions
from googlecloudsdk.api_lib.services import services_util
from googlecloudsdk.api_lib.util import apis_internal
from googlecloudsdk.api_lib.util import http_retry
from googlecloudsdk.command_lib.services import util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import transport

_PROJECT_RESOURCE = 'projects/%s'
_FOLDER_RESOURCE = 'folders/%s'
_ORGANIZATION_RESOURCE = 'organizations/%s'
_PROJECT_SERVICE_RESOURCE = 'projects/%s/services/%s'
_FOLDER_SERVICE_RESOURCE = 'folders/%s/services/%s'
_ORG_SERVICE_RESOURCE = 'organizations/%s/services/%s'
_SERVICE_RESOURCE = 'services/%s'
_REVERSE_CLOSURE = '/reverseClosure'
_CONSUMER_SERVICE_RESOURCE = '%s/services/%s'
_CONSUMER_POLICY_DEFAULT = '/consumerPolicies/%s'
_MCP_POLICY_DEFAULT = '/mcpPolicies/%s'
# MCPListFilter is the filter for listing services with MCP endpoint.
_MCP_LIST_FILTER = 'mcp_server:urls'
_EFFECTIVE_POLICY = '/effectivePolicy'
_EFFECTIVE_MCP_POLICY = '/effectiveMcpPolicy'
_GOOGLE_CATEGORY_RESOURCE = 'categories/google'
_LIMIT_OVERRIDE_RESOURCE = '%s/consumerOverrides/%s'
_VALID_CONSUMER_PREFIX = frozenset({'projects/', 'folders/', 'organizations/'})
_V1_VERSION = 'v1'
_V1BETA1_VERSION = 'v1beta1'
_V1ALPHA_VERSION = 'v1alpha'
_V2ALPHA_VERSION = 'v2alpha'
_V2BETA_VERSION = 'v2beta'
_TOO_MANY_REQUESTS = 429

# Map of services which should be protected from being disabled by
# prompting the user for  confirmation
_PROTECTED_SERVICES = {
    'anthos.googleapis.com': ('Warning: Disabling this service will '
                              'also automatically disable any running '
                              'Anthos clusters.')
}

# Set of wave 0 services to be listed in --available
_MCP_LIST_WAVE_0_SERVICES = frozenset({
    'services/bigquery.googleapis.com',
    'services/compute.googleapis.com',
    'services/container.googleapis.com',
    'services/mapstools.googleapis.com',
})

# Set of wave 1 services to be listed in --available
_MCP_LIST_WAVE_1_SERVICES = frozenset({
    'services/run.googleapis.com',
    'services/alloydb.googleapis.com',
    'services/sqladmin.googleapis.com',
    'services/spanner.googleapis.com',
    'services/androidmanagement.googleapis.com',
    'services/developerknowledge.googleapis.com',
    'services/chronicle.googleapis.com',
    'services/monitoring.googleapis.com',
    'services/logging.googleapis.com',
    'services/cloudresourcemanager.googleapis.com',
    'services/discoveryengine.googleapis.com',
    'services/bigquerymigration.googleapis.com',
    'services/aiplatform.googleapis.com',
})


class ContainerType(enum.Enum):
  """Return the container type."""
  PROJECT_SERVICE_RESOURCE = 1
  FOLDER_SERVICE_RESOURCE = 2
  ORG_SERVICE_RESOURCE = 3


def GetProtectedServiceWarning(service_name):
  """Return the warning message associated with a protected service."""
  return _PROTECTED_SERVICES.get(service_name)


def GetMcpEnabledError(resource_name):
  """Return the error message associated with a MCP enabled service."""
  return (
      'To enable the MCP endpoint, the service must be enabled first. '
      'Do you want to enable the service for the resource'
      f' {resource_name}?'
  )


def GetConsumerPolicyV2Beta(policy_name):
  """Make API call to get a consumer policy.

  Args:
    policy_name: The name of a consumer policy. Currently supported format
      '{resource_type}/{resource_name}/consumerPolicies/default'. For example,
      'projects/100/consumerPolicies/default'.

  Raises:
    exceptions.GetConsumerPolicyPermissionDeniedException: when getting a
      consumer policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    message.GoogleApiServiceusageV2betaConsumerPolicy: The consumer policy
  """
  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageConsumerPoliciesGetRequest(name=policy_name)

  try:
    return client.consumerPolicies.Get(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.GetConsumerPolicyException)


def GetMcpPolicy(policy_name):
  """Make API call to get a MCP policy.

  Args:
    policy_name: The name of a MCP policy. Currently supported format
      '{resource_type}/{resource_name}/mcpPolicies/default'. For example,
      'projects/100/mcpPolicies/default'.

  Raises:
    exceptions.GetMcpPolicyException: when getting a
      MCP policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The MCP policy
  """
  client = _GetClientInstance(_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageMcpPoliciesGetRequest(name=policy_name)

  try:
    return client.mcpPolicies.Get(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.GetMcpPolicyException)


def GetContentSecurityPolicy(name):
  """Make API call to get the content security policy for a given project, folder or organization.

  Args:
    name: The name of a content security policy. Currently supported format
      '{resource_type}/{resource_name}/contentSecurityPolicies/default'. For
      example, 'projects/100/contentSecurityPolicies/default'.

  Raises:
    exceptions.GetContentSecurityPolicyException: when getting a
      content security policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The content security policy.
  """
  client = _GetClientInstance(_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageContentSecurityPoliciesGetRequest(name=name)

  try:
    return client.contentSecurityPolicies.Get(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.GetContentSecurityPolicyException)


def UpdateContentSecurityPolicy(name, content_security_policy):
  """Make API call to update the content security policy for a given project, folder or organization.

  Args:
    name: The name of a content security policy. Currently supported format
      '{resource_type}/{resource_name}/contentSecurityPolicies/default'. For
      example, 'projects/100/contentSecurityPolicies/default'.
    content_security_policy: The content security policy to update.

  Raises:
    exceptions.UpdateContentSecurityPolicyException: when updating a
      content security policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The content security policy.
  """
  client = _GetClientInstance(_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageContentSecurityPoliciesPatchRequest(
      name=name, contentSecurityPolicy=content_security_policy
  )

  try:
    return client.contentSecurityPolicies.Patch(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.UpdateContentSecurityPolicyException)


def TestMcpEnabled(name: str, service: str):
  """Make API call to test MCP enabled.

  Args:
    name: Parent resource to test a value against the result of merging MCP
      policies in the resource hierarchy. Format: "projects/{PROJECT_ID}" (e.g.,
      "projects/foo-bar"), "projects/{PROJECT_NUMBER}" (e.g.,
      "projects/12345678"), "folders/{FOLDER_NUMBER}" (e.g., "folders/1234567")
      , "organizations/{ORGANIZATION_NUMBER}" (e.g., "organizations/123456").
    service: Service name to check if the targeted resource can use this service
      for MCP. Current supported value: services/{SERVICE_NAME} (format:
      "services/{service}").

  Raises:
    exceptions.TestMcpEnabledException: when testing value for a
      service and resource.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Message.State: The state of the service.
  """
  client = _GetClientInstance(_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageTestMcpEnabledRequest(
      name=name,
      testMcpEnabledRequest=messages.TestMcpEnabledRequest(serviceName=service),
  )

  try:
    return client.v2beta.TestMcpEnabled(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.TestMcpEnabledException)


def TestEnabled(name: str, service: str):
  """Make API call to test enabled.

  Args:
    name: Parent resource to test a value against the result of merging consumer
      policies in the resource hierarchy. format-"projects/100", "folders/101"
      or "organizations/102".
    service: Service name to check if the targeted resource can use this
      service. Current supported value: SERVICE (format: "services/{service}").

  Raises:
    exceptions.TestEnabledPermissionDeniedException: when testing value for a
      service and resource.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Message.State: The state of the service.
  """
  client = _GetClientInstance(_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageTestEnabledRequest(
      name=name,
      testEnabledRequest=messages.TestEnabledRequest(serviceName=service),
  )

  try:
    return client.v2beta.TestEnabled(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.TestEnabledException)


def GetEffectivePolicyV2Beta(name: str, view: str = 'BASIC'):
  """Make API call to get a effective policy.

  Args:
    name: The name of the effective policy.Currently supported format
      '{resource_type}/{resource_name}/effectivePolicy'. For example,
      'projects/100/effectivePolicy'.
    view: The view of the effective policy to use. The default view is 'BASIC'.

  Raises:
    exceptions.GetEffectivePolicyException: when getting a
      effective policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    message.EffectivePolicy: The effective policy
  """
  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE
  if view == 'BASIC':
    view_type = (
        messages.ServiceusageGetEffectivePolicyRequest.ViewValueValuesEnum.EFFECTIVE_POLICY_VIEW_BASIC
    )
  else:
    view_type = (
        messages.ServiceusageGetEffectivePolicyRequest.ViewValueValuesEnum.EFFECTIVE_POLICY_VIEW_FULL
    )

  request = messages.ServiceusageGetEffectivePolicyRequest(
      name=name, view=view_type
  )

  try:
    return client.v2beta.GetEffectivePolicy(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.GetEffectivePolicyException)


def GetEffectiveMcpPolicy(name: str, view: str = 'BASIC'):
  """Make API call to get a effective MCP policy.

  Args:
    name: The name of the effective MCP policy. Currently supported format
      '{resource_type}/{resource_name}/effectiveMcpPolicy'. For example,
      'projects/100/effectivePolicy'.
    view: The view of the effective MCP policy to use. The default view is
      'BASIC'.

  Raises:
    exceptions.GetEffectiveMcpPolicyException: when getting a
      effective policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    message.EffectiveMcpPolicy: The effective MCP policy
  """
  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE
  if view == 'BASIC':
    view_type = (
        messages.ServiceusageGetEffectiveMcpPolicyRequest.ViewValueValuesEnum.EFFECTIVE_MCP_POLICY_VIEW_BASIC
    )
  else:
    view_type = (
        messages.ServiceusageGetEffectiveMcpPolicyRequest.ViewValueValuesEnum.EFFECTIVE_MCP_POLICY_VIEW_FULL
    )

  request = messages.ServiceusageGetEffectiveMcpPolicyRequest(
      name=name, view=view_type
  )

  try:
    return client.v2beta.GetEffectiveMcpPolicy(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.GetEffectiveMcpPolicyException)


def GetServiceV2Beta(service):
  """Make API call to get service state for a service .

  Args:
    service: Service. Current supported value:(format:
      "{resource}/{resource_Id}/services/{service}").

  Raises:
    exceptions.GetServiceException: when getting service
      service state for service in the resource.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Message.GetServicesResponse: Service state of the given resource.
  """
  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesGetRequest(
      name=service,
      view=messages.ServiceusageServicesGetRequest.ViewValueValuesEnum.SERVICE_STATE_VIEW_FULL,
  )

  try:
    return client.services.Get(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.GetServiceException)


def BatchGetService(parent, services):
  """Make API call to get service state for multiple services .

  Args:
    parent: Parent resource to get service state for. format-"projects/100",
      "folders/101" or "organizations/102".
    services: Services. Current supported value:(format:
      "{resource}/{resource_Id}/services/{service}").

  Raises:
    exceptions.BatchGetServiceException: when getting batch
      service state for services in the resource.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Message.BatchGetServicesResponse: Service state of the given resource.
  """
  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesBatchGetRequest(
      parent=parent,
      services=services,
      view=messages.ServiceusageServicesBatchGetRequest.ViewValueValuesEnum.SERVICE_STATE_VIEW_FULL,
  )

  try:
    return client.services.BatchGet(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.BatchGetServiceException)


def ListCategoryServices(resource, category, page_size=200, limit=sys.maxsize):
  """Make API call to list category services .

  Args:
    resource: resource to get list for. format-"projects/100", "folders/101" or
      "organizations/102".
    category: category to get list for. format-"catgeory/<category>".
    page_size: The page size to list.default=200
    limit: The max number of services to display.

  Raises:
    exceptions.ListCategoryServicesException: when listing the
    services the parent category includes.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Message.ListCategoryServicesResponse: The services the parent category
    includes.
  """
  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageCategoriesCategoryServicesListRequest(
      parent='{}/{}'.format(resource, category),
  )

  try:
    return list_pager.YieldFromList(
        _Lister(client.categories_categoryServices),
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='services',
    )
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.ListCategoryServicesException)


def UpdateConsumerPolicyV2Alpha(
    consumerpolicy, name, force=False, validateonly=False
):
  """Make API call to update a consumer policy.

  Args:
    consumerpolicy: The consumer policy to update.
    name: The resource name of the policy. Currently supported format
      '{resource_type}/{resource_name}/consumerPolicies/default. For example,
      'projects/100/consumerPolicies/default'.
    force: Disable service with usage within last 30 days or disable recently
      enabled service.
    validateonly: If set, validate the request and preview the result but do not
      actually commit it. The default is false.

  Raises:
    exceptions.UpdateConsumerPolicyPermissionDeniedException: when updating a
      consumer policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Updated consumer policy
  """
  client = _GetClientInstance('v2alpha')
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageConsumerPoliciesPatchRequest(
      googleApiServiceusageV2alphaConsumerPolicy=consumerpolicy,
      name=name,
      force=force,
      validateOnly=validateonly,
  )

  try:
    return client.consumerPolicies.Patch(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.UpdateConsumerPolicyException)
  except apitools_exceptions.HttpBadRequestError as e:
    log.status.Print(
        'Provide the --force flag if you wish to force disable services.'
    )
    exceptions.ReraiseError(e, exceptions.Error)


def UpdateMcpPolicy(policy, name, force=False, validateonly=False):
  """Make API call to update a MCP policy.

  Args:
    policy: The MCP policy to update.
    name: The resource name of the MCP policy. Currently supported format
      '{resource_type}/{resource_name}/mcpPolicies/default. For example,
      'projects/100/mcpPolicies/default'.
    force: Disable service with usage within last 30 days or disable recently
      enabled service.(not supported during MVP.)
    validateonly: If set, validate the request and preview the result but do not
      actually commit it. The default is false.(not supported during MVP.)

  Raises:
    exceptions.class UpdateMcpPolicyException: when getting a
      MCP policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The MCP policy
  """
  client = _GetClientInstance(_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageMcpPoliciesPatchRequest(
      mcpPolicy=policy, name=name, force=force, validateOnly=validateonly
  )

  try:
    return client.mcpPolicies.Patch(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.UpdateMcpPolicyException)


def UpdateConsumerPolicyV2Beta(
    consumerpolicy, name, force=False, validateonly=False
):
  """Make API call to update a consumer policy.

  Args:
    consumerpolicy: The consumer policy to update.
    name: The resource name of the policy. Currently supported format
      '{resource_type}/{resource_name}/consumerPolicies/default. For example,
      'projects/100/consumerPolicies/default'.
    force: Disable service with usage within last 30 days or disable recently
      enabled service.
    validateonly: If set, validate the request and preview the result but do not
      actually commit it. The default is false.

  Raises:
    exceptions.UpdateConsumerPolicyException: when updating a
      consumer policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Updated consumer policy
  """
  client = _GetClientInstance(_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageConsumerPoliciesPatchRequest(
      googleApiServiceusageV2betaConsumerPolicy=consumerpolicy,
      name=name,
      force=force,
      validateOnly=validateonly,
  )

  try:
    return client.consumerPolicies.Patch(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.UpdateConsumerPolicyException)
  except apitools_exceptions.HttpBadRequestError as e:
    log.status.Print(
        'Provide the --force flag if you wish to force disable services.'
    )
    exceptions.ReraiseError(e, exceptions.Error)


def ListGroupMembers(
    resource: str,
    service_group: str,
    page_size: int = 50,
    limit: int = sys.maxsize,
):
  """Make API call to list group members of a specific service group.

  Args:
    resource: The target resource.
    service_group: Service group which owns a collection of group members, for
      example, 'services/compute.googleapis.com/groups/dependencies'.
    page_size: The page size to list. The default page_size is 50.
    limit: The max number of services to display.

  Raises:
    exceptions.ListGroupMembersPermissionDeniedException: when listing
      group members fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Message.ListGroupMembersResponse : Group members in the given service group.
  """
  client = _GetClientInstance(_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesGroupsMembersListRequest(
      parent=resource + '/' + service_group
  )

  try:
    response = list_pager.YieldFromList(
        _Lister(client.services_groups_members),
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='memberStates',
    )
    member_states = []
    for member_state in response:
      member_states.append(member_state)
    return member_states
  except (
      apitools_exceptions.HttpBadRequestError,
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    if 'SU_GROUP_NOT_FOUND' in str(e):
      return []
    else:
      exceptions.ReraiseError(e, exceptions.ListGroupMembersException)


def ListDescendantServices(
    resource: str, service_group: str, page_size: int = 50
):
  """Make API call to list descendant services of a specific service group.

  Args:
    resource: The target resource in the format:
      '{resource_type}/{resource_name}'.
    service_group: Service group, for example,
      'services/compute.googleapis.com/groups/dependencies'.
    page_size: The page size to list. The default page_size is 50.

  Raises:
    exceptions.ListDescendantServicesPermissionDeniedException: when listing
      descendant services fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Descendant services in the given service group.
  """
  client = _GetClientInstance('v2alpha')
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesGroupsDescendantServicesListRequest(
      parent='{}/{}'.format(resource, service_group)
  )

  try:
    return list_pager.YieldFromList(
        _Lister(client.services_groups_descendantServices),
        request,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='services',
    )
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.ListDescendantServicesException)


def ListExpandedMembers(resource: str, service_group: str, page_size: int = 50):
  """Make API call to list expanded members of a specific service group.

  Args:
    resource: The target resource in the format:
      '{resource_type}/{resource_name}'.
    service_group: Service group, for example,
      'services/compute.googleapis.com/groups/dependencies'.
    page_size: The page size to list. The default page_size is 50.

  Raises:
    exceptions.ListExpandedMembersException: when listing
      expanded members fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Message. ExpandedMember.serviceName : Service names of the expanded members
    of the service group.
  """
  client = _GetClientInstance(_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesGroupsExpandedMembersListRequest(
      parent='{}/{}'.format(resource, service_group)
  )

  try:
    response = list_pager.YieldFromList(
        _Lister(client.services_groups_expandedMembers),
        request,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='members',
    )
    service_names = []
    for member in response:
      service_names.append(member.serviceName)
    return service_names
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    if 'SU_GROUP_NOT_FOUND' in str(e):
      return []
    else:
      exceptions.ReraiseError(e, exceptions.ListExpandedMembersException)


def ListAncestorGroups(resource: str, service: str, page_size: int = 50):
  """Make API call to list ancestor groups that depend on the service.

  Args:
    resource: The target resource.format : '{resource_type}/{resource_name}'.
    service: The identifier of the service to get ancestor groups of, for
      example, 'services/compute.googleapis.com'.
    page_size: The page size to list.The default page_size is 50.

  Raises:
    exceptions.ListAncestorGroupsPermissionDeniedException: when listing
      ancestor group fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Ancestor groups that depend on the service.
  """
  client = _GetClientInstance('v2alpha')
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesAncestorGroupsListRequest(
      name=f'{resource}/{service}'
  )

  try:
    return list_pager.YieldFromList(
        _Lister(client.services_ancestorGroups),
        request,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='groups',
    )
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.ListAncestorGroupsPermissionDeniedException
    )


def AnalyzeConsumerPolicy(
    proposed_policy,
):
  """Make API call to analyze a consumer policy for dependencies.

  Args:
    proposed_policy: The consumer policy to analyze. type :
      message.GoogleApiServiceusageV2alphaConsumerPolicy

  Raises:
    exceptions.AnalyzeConsumerPolicyException: when analyzing a
      consumer policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    message.
  """
  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageConsumerPoliciesAnalyzeRequest(
      analyzeConsumerPolicyRequest=messages.AnalyzeConsumerPolicyRequest(
          proposedPolicy=proposed_policy,
          analysisTypes=[
              messages.AnalyzeConsumerPolicyRequest.AnalysisTypesValueListEntryValuesEnum.ANALYSIS_TYPE_DEPENDENCY,
          ],
      ),
      name=proposed_policy.name,
  )
  try:
    return client.consumerPolicies.Analyze(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.AnalyzeConsumerPolicyException)


def UpdateConsumerPolicy(
    consumerpolicy,
    validate_only: bool = False,
    bypass_dependency_check: bool = False,
    force: bool = False,
):
  """Make API call to update a consumer policy.

  Args:
    consumerpolicy: The consumer policy to update.
    validate_only: If True, the action will be validated and result will be
      preview but not exceuted.
    bypass_dependency_check: If True, dependencies check will be bypassed.
    force: If True, the system will bypass usage checks for services that are
      being removed.

  Raises:
    exceptions.UpdateConsumerPolicyException: when updating policy API fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The result of the operation
  """

  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  try:

    policy = messages.GoogleApiServiceusageV2betaConsumerPolicy(
        name=consumerpolicy['name']
    )

    if (
        'enableRules' in consumerpolicy.keys()
        and consumerpolicy['enableRules'] is not None
    ):
      for enable_rule in consumerpolicy['enableRules']:
        if 'services' in enable_rule:
          policy.enableRules.append(
              messages.GoogleApiServiceusageV2betaEnableRule(
                  services=enable_rule['services']
              )
          )

    if not bypass_dependency_check:
      op = AnalyzeConsumerPolicy(policy)

      op = services_util.WaitOperation(op.name, GetOperationV2Beta)

      analysis_reponse = encoding.MessageToDict(op.response)

      missing_dependencies = {}

      if 'analysis' in analysis_reponse:
        for analysis in analysis_reponse['analysis']:
          for warning in analysis['analysisResult']['warnings']:
            if analysis['service'] not in missing_dependencies.keys():
              missing_dependencies[analysis['service']] = [
                  warning['missingDependency']
              ]
            else:
              missing_dependencies[analysis['service']].append(
                  warning['missingDependency']
              )

      if missing_dependencies:
        error_message = 'Policy cannot be updated as \n'
        for service in missing_dependencies:
          for dependency in missing_dependencies[service]:
            error_message += (
                service + ' is missing service dependency ' + dependency + '\n'
            )

        raise exceptions.ConfigError(error_message)

    return UpdateConsumerPolicyV2Beta(
        policy,
        policy.name,
        validateonly=validate_only,
        force=force,
    )
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.UpdateConsumerPolicyException)


def AddContentSecurityProvider(
    content_security_provider: str,
    resource_name: str,
):
  """Make API call to add a content security provider.

  Args:
    content_security_provider: The content security provider to add.
    resource_name: The resource name of the content security policy.

  Raises:
    exceptions.AddContentSecurityProviderException: when adding content security
    provider to content security policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The result of the operation
  """

  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  try:
    content_security_policy = GetContentSecurityPolicy(resource_name)

    if not content_security_provider.startswith('services/'):
      content_security_provider = f'services/{content_security_provider}'

    mcp_content_security = content_security_policy.mcpContentSecurity

    existing_content_security_providers = [
        p.name for p in mcp_content_security.contentSecurityProviders
    ]

    if content_security_provider in existing_content_security_providers:
      log.warning(
          f'The content security provider {content_security_provider} already'
          ' exists.'
      )
      return None

    update_policy = copy.deepcopy(content_security_policy)

    update_policy.mcpContentSecurity.contentSecurityProviders.append(
        messages.ContentSecurityProvider(name=content_security_provider)
    )

    return UpdateContentSecurityPolicy(
        resource_name,
        update_policy,
    )

  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.AddContentSecurityProviderException)


def RemoveContentSecurityProvider(
    content_security_provider: str,
    resource_name: str,
):
  """Make API call to remove a content security provider.

  Args:
    content_security_provider: The content security provider to remove.
    resource_name: The resource name of the content security policy.

  Raises:
    exceptions.RemoveContentSecurityProviderException: when removing content
    security
    provider from content security policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The result of the operation
  """

  try:
    content_security_policy = GetContentSecurityPolicy(resource_name)

    if not content_security_provider.startswith('services/'):
      content_security_provider = f'services/{content_security_provider}'

    update_policy = copy.deepcopy(content_security_policy)
    mcp_content_security = update_policy.mcpContentSecurity

    updated_content_security_providers = []
    is_present = False

    for p in mcp_content_security.contentSecurityProviders:
      if p.name == content_security_provider:
        is_present = True
      else:
        updated_content_security_providers.append(p)

    if not is_present:
      log.warning(
          f'The content security provider {content_security_provider} does not'
          ' exist.'
      )
      return None

    mcp_content_security.contentSecurityProviders = (
        updated_content_security_providers
    )

    return UpdateContentSecurityPolicy(
        resource_name,
        update_policy,
    )

  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.RemoveContentSecurityProviderException
    )


def AddEnableRule(
    services: List[str],
    project: str,
    consumer_policy_name: str = 'default',
    folder: str = None,
    organization: str = None,
    validate_only: bool = False,
    skip_dependency: bool = False,
    group: str = 'dependencies',
    inputted_group: bool = False,
):
  """Make API call to enable a specific service.

  Args:
    services: The identifier of the service to enable, for example
      'serviceusage.googleapis.com'.
    project: The project for which to enable the service.
    consumer_policy_name: Name of consumer policy. The default name is
      "default".
    folder: The folder for which to enable the service.
    organization: The organization for which to enable the service.
    validate_only: If True, the action will be validated and result will be
      preview but not exceuted.
    skip_dependency: If True, the dependencies of the service to be enabled will
      not be enabled.
    group: The group to check for dependencies.
    inputted_group: If True, the group is inputted by the user. If False, the
      group is automatically set to 'dependencies'.

  Raises:
    exceptions.EnableServiceException: when enabling API fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The result of the operation
  """
  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  resource_name = _PROJECT_RESOURCE % project

  if folder:
    resource_name = _FOLDER_RESOURCE % folder

  if organization:
    resource_name = _ORGANIZATION_RESOURCE % organization

  policy_name = resource_name + _CONSUMER_POLICY_DEFAULT % consumer_policy_name

  try:
    policy = GetConsumerPolicyV2Beta(policy_name)

    prefixed_services = _GetPrefixedServiceNames(services)
    services_to_enabled = set()
    existing_services = set()
    if policy.enableRules:
      existing_services = set(policy.enableRules[0].services)

    for service in prefixed_services:
      # Check if services to add is not already present in the policy.
      if service not in existing_services:
        services_to_enabled.add(service)

    if not group.startswith('groups/'):
      prefixed_group = f'groups/{group}'
    else:
      prefixed_group = group

    dependent_services = set()

    if not skip_dependency:
      for service in prefixed_services:
        list_expanded_members = ListExpandedMembers(
            resource_name, f'{service}/{prefixed_group}'
        )
        if not list_expanded_members and inputted_group:
          if prefixed_group != 'groups/dependencies':
            raise exceptions.EmptyMembersError(
                util.GetGroupName(service, prefixed_group)
            )
          else:
            log.warning(
                f'The service {service} does not have dependencies for the '
                f'group {prefixed_group}.'
            )

        for dependent_service in list_expanded_members:
          # dependent_service is in format services/{service_name}
          dependent_service_name = dependent_service.split('/')[-1]
          # Check if dependent services to add is not already present in the
          # input services.
          if dependent_service_name not in services:
            dependent_services.add(dependent_service)

      for service in list(dependent_services):
        # check if dependent services are already enabled
        if service not in existing_services:
          services_to_enabled.add(service)

    if not services_to_enabled:
      if skip_dependency:
        log.warning(
            'The service(s) '
            + ','.join(services)
            + ' are already enabled and present in the consumer policy.'
        )
        return None, []
      else:
        service_list_str = ','.join(services)
        message = f'The service(s) {service_list_str}'

        if dependent_services:
          # if dependent services are present and not in services,
          # add them to the error message.

          dependent_list_str = ','.join(list(dependent_services))
          message += f' and their dependencies {dependent_list_str}'

        message += ' are already enabled and present in the consumer policy'
        log.warning(message)
        return None, []

    if policy.enableRules:
      for service in list(services_to_enabled):
        policy.enableRules[0].services.append(service)
    else:
      policy.enableRules.append(
          messages.GoogleApiServiceusageV2betaEnableRule(
              services=list(services_to_enabled)
          )
      )

    return UpdateConsumerPolicyV2Beta(
        policy, policy_name, validateonly=validate_only
    ), list(services_to_enabled)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.EnableServiceException)


def AddMcpEnableRule(
    service: str,
    project: str,
    folder: str = None,
    organization: str = None,
):
  """Make API call to enable a specific service in mcp policy.

  Args:
    service: The identifier of the service to enable, for example
      'serviceusage.googleapis.com'.
    project: The project for which to enable the service.
    folder: The folder for which to enable the service.
    organization: The organization for which to enable the service.

  Raises:
    exceptions.EnableServiceException: when enabling API fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The result of the operation
  """
  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  resource_name = _PROJECT_RESOURCE % project

  if folder:
    resource_name = _FOLDER_RESOURCE % folder

  if organization:
    resource_name = _ORGANIZATION_RESOURCE % organization

  policy_name = resource_name + _MCP_POLICY_DEFAULT % 'default'

  try:
    policy = GetMcpPolicy(policy_name)

    if policy.mcpEnableRules:
      for mcp_service in policy.mcpEnableRules[0].mcpServices:
        if mcp_service.service == _SERVICE_RESOURCE % service:
          log.warning(f'The service {service} is already enabled for MCP.')
          return None

      policy.mcpEnableRules[0].mcpServices.append(
          messages.McpService(service=_SERVICE_RESOURCE % service)
      )
    else:
      policy.mcpEnableRules.append(
          messages.McpEnableRule(
              mcpServices=[
                  messages.McpService(service=_SERVICE_RESOURCE % service)
              ]
          )
      )

    return UpdateMcpPolicy(policy, policy_name)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.EnableMcpServiceException)


def RemoveEnableRule(
    project: str,
    services: List[str],
    consumer_policy_name: str = 'default',
    force: bool = False,
    folder: str = None,
    organization: str = None,
    validate_only: bool = False,
    skip_dependency_check: bool = False,
    disable_dependency_services: bool = False,
):
  """Make API call to disable a specific service.

  Args:
    project: The project for which to disable the service.
    services: The list of identifiers of the services to disable, for example
      ['serviceusage.googleapis.com', 'apikeys.googleapis.com'].
    consumer_policy_name: Name of consumer policy. The default name is
      "default".
    force: Disable service with usage within last 30 days or disable recently
      enabled service or disable the service even if there are enabled services
      which depend on it. This also disables the services which depend on the
      service to be disabled.
    folder: The folder for which to disable the service.
    organization: The organization for which to disable the service.
    validate_only: If True, the action will be validated and result will be
      preview but not exceuted.`
    skip_dependency_check: If True, the enabled dependent services of the
      service to be disabled will remian enabled.
    disable_dependency_services: If True, the services which depend on the
      service to be disabled will also be disabled.

  Raises:
    exceptions.EnableServiceException: when disabling API fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The result of the operation
  """
  resource_name = _PROJECT_RESOURCE % project

  if folder:
    resource_name = _FOLDER_RESOURCE % folder

  if organization:
    resource_name = _ORGANIZATION_RESOURCE % organization

  policy_name = resource_name + _CONSUMER_POLICY_DEFAULT % consumer_policy_name

  try:
    current_policy = GetConsumerPolicyV2Beta(policy_name)

    prefixed_services = _GetPrefixedServiceNames(services)
    services_to_remove = {
        service
        for service in prefixed_services
        if any(
            service in enable_rule.services
            for enable_rule in current_policy.enableRules
        )
    }

    if not services_to_remove:
      log.warning(
          'The service(s) '
          + ','.join(prefixed_services)
          + ' are not enabled in the consumer policy.'
      )
      return None

    proposed_policy = copy.deepcopy(current_policy)
    for enable_rule in proposed_policy.enableRules:
      for service in services_to_remove:
        if service in enable_rule.services:
          enable_rule.services.remove(service)

    to_remove = []

    if not skip_dependency_check:

      op = AnalyzeConsumerPolicy(proposed_policy)

      op = services_util.WaitOperation(op.name, GetOperationV2Beta)

      analysis_reponse = encoding.MessageToDict(op.response)

      missing_dependency = {}

      if 'analysis' in analysis_reponse:
        for analysis in analysis_reponse['analysis']:
          for warning in analysis['analysisResult']['warnings']:
            for service in services_to_remove:
              ## check if analysis is related to service to be removed.
              if service == warning['missingDependency']:
                if service not in missing_dependency:
                  missing_dependency[service] = []
                missing_dependency[service].append(analysis['service'])
                to_remove.append(analysis['service'])

      if not disable_dependency_services and to_remove:
        json_string = json.dumps(missing_dependency)
        raise exceptions.ConfigError(
            'The services are depended on by the following active service(s) '
            + json_string
            + ' . Please remove the active dependent services or provide the'
            ' --disable-dependency-services flag to disable them, or'
            ' --bypass-dependency-service-check to ignore this check.'
        )

    to_remove = set(to_remove)

    updated_consumer_poicy = copy.deepcopy(proposed_policy)
    updated_consumer_poicy.enableRules.clear()

    for enable_rule in proposed_policy.enableRules:
      rule = copy.deepcopy(enable_rule)
      for service_name in enable_rule.services:
        if service_name in to_remove:
          rule.services.remove(service_name)
      if rule.services:
        updated_consumer_poicy.enableRules.append(rule)

    return UpdateConsumerPolicyV2Beta(
        updated_consumer_poicy,
        policy_name,
        force=force,
        validateonly=validate_only,
    )
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.EnableServiceException)
  except apitools_exceptions.HttpBadRequestError as e:
    log.status.Print(
        'Provide the --force flag if you wish to force disable services.'
    )
    exceptions.ReraiseError(e, exceptions.Error)


def RemoveMcpEnableRule(
    project: str,
    service: str,
    mcp_policy_name: str = 'default',
    folder: str = None,
    organization: str = None,
):
  """Make API call to disable a service for MCP.

  Args:
    project: The project for which to disable the service for MCP.
    service: The service to disable for MCP, for example
      'serviceusage.googleapis.com'.
    mcp_policy_name: Name of MCP policy. The default name is "default".
    folder: The folder for which to disable the service.
    organization: The organization for which to disable the service.

  Raises:
    exceptions.EnableMcpServiceException: when disabling API fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The result of the operation
  """

  resource_name = _PROJECT_RESOURCE % project

  if folder:
    resource_name = _FOLDER_RESOURCE % folder

  if organization:
    resource_name = _ORGANIZATION_RESOURCE % organization

  policy_name = resource_name + _MCP_POLICY_DEFAULT % mcp_policy_name

  try:
    policy = GetMcpPolicy(policy_name)

    already_disabled = True

    updated_mcp_policy = copy.deepcopy(policy)
    updated_mcp_policy.mcpEnableRules.clear()

    if policy.mcpEnableRules:
      for mcp_enable_rule in policy.mcpEnableRules:
        rule = copy.deepcopy(mcp_enable_rule)
        for mcp_service in rule.mcpServices:
          if mcp_service.service == _SERVICE_RESOURCE % service:
            already_disabled = False
            rule.mcpServices.remove(mcp_service)
        if rule.mcpServices:
          updated_mcp_policy.mcpEnableRules.append(rule)

    if already_disabled:
      log.warning(f'The service {service} is not enabled for MCP.')
      return None

    return UpdateMcpPolicy(updated_mcp_policy, policy_name)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.EnableMcpServiceException)
  except apitools_exceptions.HttpBadRequestError as e:
    exceptions.ReraiseError(e, exceptions.Error)


def EnableApiCall(project, service):
  """Make API call to enable a specific service.

  Args:
    project: The project for which to enable the service.
    service: The identifier of the service to enable, for example
      'serviceusage.googleapis.com'.

  Raises:
    exceptions.EnableServiceException: when enabling API fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The result of the operation
  """
  client = _GetClientInstance()
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesEnableRequest(
      name=_PROJECT_SERVICE_RESOURCE % (project, service))
  try:
    return client.services.Enable(request)
  except (apitools_exceptions.HttpForbiddenError,
          apitools_exceptions.HttpNotFoundError) as e:
    exceptions.ReraiseError(e, exceptions.EnableServiceException)


def BatchEnableApiCall(project, services):
  """Make API call to batch enable services.

  Args:
    project: The project for which to enable the services.
    services: Iterable of identifiers of services to enable.

  Raises:
    exceptions.EnableServiceException: when enabling API fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The result of the operation
  """
  client = _GetClientInstance()
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesBatchEnableRequest(
      batchEnableServicesRequest=messages.BatchEnableServicesRequest(
          serviceIds=services),
      parent=_PROJECT_RESOURCE % project)
  try:
    return client.services.BatchEnable(request)
  except (apitools_exceptions.HttpForbiddenError,
          apitools_exceptions.HttpNotFoundError) as e:
    exceptions.ReraiseError(e, exceptions.EnableServiceException)


def DisableApiCall(project, service, force=False):
  """Make API call to disable a specific service.

  Args:
    project: The project for which to enable the service.
    service: The identifier of the service to disable, for example
      'serviceusage.googleapis.com'.
    force: disable the service even if there are enabled services which depend
      on it. This also disables the services which depend on the service to be
      disabled.

  Raises:
    exceptions.EnableServiceException: when disabling API fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The result of the operation
  """
  client = _GetClientInstance()
  messages = client.MESSAGES_MODULE

  check = messages.DisableServiceRequest.CheckIfServiceHasUsageValueValuesEnum.CHECK
  if force:
    check = messages.DisableServiceRequest.CheckIfServiceHasUsageValueValuesEnum.SKIP
  request = messages.ServiceusageServicesDisableRequest(
      name=_PROJECT_SERVICE_RESOURCE % (project, service),
      disableServiceRequest=messages.DisableServiceRequest(
          disableDependentServices=force,
          checkIfServiceHasUsage=check,
      ),
  )
  try:
    return client.services.Disable(request)
  except (apitools_exceptions.HttpForbiddenError,
          apitools_exceptions.HttpNotFoundError) as e:
    exceptions.ReraiseError(e, exceptions.EnableServiceException)
  except apitools_exceptions.HttpBadRequestError as e:
    log.status.Print('Provide the --force flag if you wish to force disable '
                     'services.')
    exceptions.ReraiseError(e, exceptions.Error)


def GetService(project, service):
  """Get a service.

  Args:
    project: The project for which to get the service.
    service: The service to get.

  Raises:
    exceptions.GetServicePermissionDeniedException: when getting service fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The service configuration.
  """
  client = _GetClientInstance()
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesGetRequest(
      name=_PROJECT_SERVICE_RESOURCE % (project, service))
  try:
    return client.services.Get(request)
  except (apitools_exceptions.HttpForbiddenError,
          apitools_exceptions.HttpNotFoundError) as e:
    exceptions.ReraiseError(e, exceptions.GetServicePermissionDeniedException)


def IsServiceEnabled(service):
  client = _GetClientInstance()
  messages = client.MESSAGES_MODULE
  return service.state == messages.GoogleApiServiceusageV1Service.StateValueValuesEnum.ENABLED


class _Lister:

  def __init__(self, service_usage):
    self.service_usage = service_usage

  @http_retry.RetryOnHttpStatus(_TOO_MANY_REQUESTS)
  def List(self, request, global_params=None):
    return self.service_usage.List(request, global_params=global_params)


def ListServicesV2Beta(
    project: str,
    enabled: bool,
    page_size: int,
    limit: int,
    folder: str = None,
    organization: str = None,
):
  """Make API call to list services.

  Args:
    project: The project for which to list services.
    enabled: List only enabled services.
    page_size: The page size to list.
    limit: The max number of services to display.
    folder: The folder for which to list services.
    organization: The organization for which to list services.

  Raises:
    exceptions.ListServicesException: when listing services
    fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The list of services
  """
  resource_name = _PROJECT_RESOURCE % project
  if folder:
    resource_name = _FOLDER_RESOURCE % folder

  if organization:
    resource_name = _ORGANIZATION_RESOURCE % organization

  services = {}
  parent = []
  try:
    if enabled:
      policy_name = resource_name + _EFFECTIVE_POLICY
      effectivepolicy = GetEffectivePolicyV2Beta(policy_name)

      for rules in effectivepolicy.enableRules:
        for value in rules.services:
          if limit == 0:
            break
          parent.append(f'{resource_name}/{value}')
          services[value] = ''
          limit -= 1

      for value in range(0, len(parent), 20):
        response = BatchGetService(resource_name, parent[value : value + 20])
        for service_state in response.services:
          service_name = '/'.join(service_state.name.split('/')[2:])
          services[service_name] = service_state.service.displayName

    else:
      for public_service in _ListPublicServices(
          page_size=page_size, limit=limit
      ):
        services[public_service.name] = public_service.displayName
      for shared_service in _ListSharedServices(
          resource_name, page_size=page_size, limit=limit
      ):
        services[shared_service.service.name] = (
            shared_service.service.displayName
        )

    result = []
    service_info = collections.namedtuple('ServiceList', ['name', 'title'])
    for service in services:
      result.append(service_info(name=service, title=services[service]))

    return result
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.ListServicesException)


def ListMcpServicesV2Beta(
    project: str,
    enabled: bool,
    page_size: int,
    limit: int,
    folder: str = None,
    organization: str = None,
):
  """Make API call to list services.

  Args:
    project: The project for which to list MCP services.
    enabled: List only enabled  MCP services.
    page_size: The page size to list.
    limit: The max number of services to display.
    folder: The folder for which to list MCP services.
    organization: The organization for which to list MCP services.

  Raises:
    exceptions.ListMcpServicesException: when listing MCP services
    fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The list of MCP services
  """

  resource_name = _PROJECT_RESOURCE % project
  if folder:
    resource_name = _FOLDER_RESOURCE % folder

  if organization:
    resource_name = _ORGANIZATION_RESOURCE % organization

  service_to_endpoint = {}
  parent = []
  try:
    if enabled:
      policy_name = resource_name + _EFFECTIVE_MCP_POLICY
      effectivemcppolicy = GetEffectiveMcpPolicy(policy_name)

      for rules in effectivemcppolicy.mcpEnableRules:
        for mcp_service in rules.mcpServices:
          parent.append(f'{resource_name}/{mcp_service.service}')
          service_to_endpoint[mcp_service.service] = ''

      for value in range(0, len(parent), 20):
        response = BatchGetService(resource_name, parent[value : value + 20])
        for service_state in response.services:
          if limit == 0:
            break
          service_name = '/'.join(service_state.name.split('/')[2:])
          # Only return services that have MCP endpoints.
          if (
              service_state.service.mcpServer
              and service_state.service.mcpServer.urls
          ):
            service_to_endpoint[service_name] = (
                service_state.service.mcpServer.urls[0]
            )
          limit -= 1

    else:
      allowed_services = _MCP_LIST_WAVE_0_SERVICES | _MCP_LIST_WAVE_1_SERVICES
      for public_service in _ListPublicServices(
          page_size, _MCP_LIST_FILTER, limit
      ):
        if public_service.name in allowed_services:
          service_to_endpoint[public_service.name] = (
              public_service.mcpServer.urls[0]
          )
    result = []
    service_info = collections.namedtuple(
        'ServiceList', ['name', 'mcp_endpoint']
    )
    for service in service_to_endpoint:
      result.append(
          service_info(name=service, mcp_endpoint=service_to_endpoint[service])
      )

    return result
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.ListMcpServicesException)


def ListServices(project, enabled, page_size, limit):
  """Make API call to list services.

  Args:
    project: The project for which to list services.
    enabled: List only enabled services.
    page_size: The page size to list.
    limit: The max number of services to display.

  Raises:
    exceptions.ListServicesException: when listing services
    fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The list of services
  """
  client = _GetClientInstance()
  messages = client.MESSAGES_MODULE

  if enabled:
    service_filter = 'state:ENABLED'
  else:
    service_filter = None
  request = messages.ServiceusageServicesListRequest(
      filter=service_filter, parent=_PROJECT_RESOURCE % project)
  try:
    return list_pager.YieldFromList(
        _Lister(client.services),
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='services')
  except (apitools_exceptions.HttpForbiddenError,
          apitools_exceptions.HttpNotFoundError) as e:
    exceptions.ReraiseError(e, exceptions.ListServicesException)


def GetOperation(name: str):
  """Make API call to get an operation using serviceusageV1 api.

  Args:
    name: The name of operation.

  Raises:
    exceptions.OperationErrorException: when the getting operation API fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The result of the operation
  """
  client = _GetClientInstance()
  messages = client.MESSAGES_MODULE
  request = messages.ServiceusageOperationsGetRequest(name=name)
  try:
    return client.operations.Get(request)
  except (apitools_exceptions.HttpForbiddenError,
          apitools_exceptions.HttpNotFoundError) as e:
    exceptions.ReraiseError(e, exceptions.OperationErrorException)


def GetOperationV2Alpha(name: str):
  """Make API call to get an operation using serviceusageV2alpha api.

  Args:
    name: The name of the operation resource. Format
      'operations/<operation_id>'.

  Raises:
    exceptions.OperationErrorException: when the getting operation API fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The message.Operation object with response and error.
  """
  client = _GetClientInstance('v2alpha')
  messages = client.MESSAGES_MODULE
  request = messages.ServiceusageOperationsGetRequest(name=name)
  try:
    return client.operations.Get(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.OperationErrorException)


def GetOperationV2Beta(name: str):
  """Make API call to get an operation using serviceusageV2beta api.

  Args:
    name: The name of the operation resource. Format
      'operations/<operation_id>'.

  Raises:
    exceptions.OperationErrorException: when the getting operation API fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The message.Operation object with response and error.
  """
  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE
  request = messages.ServiceusageOperationsGetRequest(name=name)
  try:
    return client.operations.Get(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.OperationErrorException)


def GenerateServiceIdentityForEnabledService(
    container, enabled_services: list[str]
):
  """Generate a service identity for an enabled service.

  Args:
    container: The container to generate a service identity for.
    enabled_services: The services to generate a service identity for.

  Raises:
    exceptions.GenerateServiceIdentityPermissionDeniedException: when
    generating
    service identity fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the
    service.

  Returns:
    A dict with the email and uniqueId of the generated service identity. If
    service does not have a default identity, the response will be an empty
    dictionary.
  """
  client = _GetClientInstance(version=_V1BETA1_VERSION)
  messages = client.MESSAGES_MODULE

  # Generate service identity for all the services to be enabled.
  for service in sorted(list(enabled_services)):
    request = messages.ServiceusageServicesGenerateServiceIdentityRequest(
        parent=f'projects/{container}/{service}'
    )
    try:
      _ = client.services.GenerateServiceIdentity(request)
    except apitools_exceptions.HttpBadRequestError:
      # Bad request error is thrown if the service does not have a default
      # identity.
      continue  # Proceed to the next service.
    except (
        apitools_exceptions.HttpForbiddenError,
        apitools_exceptions.HttpNotFoundError,
    ) as e:
      exceptions.ReraiseError(
          e, exceptions.GenerateServiceIdentityPermissionDeniedException
      )


def GenerateServiceIdentity(
    container, service, container_type=ContainerType.PROJECT_SERVICE_RESOURCE
):
  """Generate a service identity.

  Args:
    container: The container to generate a service identity for.
    service: The service to generate a service identity for.
    container_type: The type of container, default to be project.

  Raises:
    exceptions.GenerateServiceIdentityPermissionDeniedException: when generating
    service identity fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    A dict with the email and uniqueId of the generated service identity. If
    service does not have a default identity, the response will be an empty
    dictionary.
  """
  client = _GetClientInstance(version=_V1BETA1_VERSION)
  messages = client.MESSAGES_MODULE

  if container_type == ContainerType.PROJECT_SERVICE_RESOURCE:
    parent = _PROJECT_SERVICE_RESOURCE % (container, service)
  elif container_type == ContainerType.FOLDER_SERVICE_RESOURCE:
    parent = _FOLDER_SERVICE_RESOURCE % (container, service)
  elif container_type == ContainerType.ORG_SERVICE_RESOURCE:
    parent = _ORG_SERVICE_RESOURCE % (container, service)
  else:
    raise ValueError('Invalid container type specified.')
  request = messages.ServiceusageServicesGenerateServiceIdentityRequest(
      parent=parent
  )
  try:
    op = client.services.GenerateServiceIdentity(request)
    response = encoding.MessageToDict(op.response)
    # Only keep email and uniqueId from the response.
    # If the response doesn't contain these keys, the returned dictionary will
    # not contain them either.
    return {k: response[k] for k in ('email', 'uniqueId') if k in response}
  except (apitools_exceptions.HttpForbiddenError,
          apitools_exceptions.HttpNotFoundError) as e:
    exceptions.ReraiseError(
        e, exceptions.GenerateServiceIdentityPermissionDeniedException)


def ListQuotaMetrics(consumer, service, page_size=None, limit=None):
  """List service quota metrics for a consumer.

  Args:
    consumer: The consumer to list metrics for, e.g. "projects/123".
    service: The service to list metrics for.
    page_size: The page size to list.
    limit: The max number of metrics to return.

  Raises:
    exceptions.PermissionDeniedException: when listing metrics fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The list of quota metrics
  """
  _ValidateConsumer(consumer)
  client = _GetClientInstance(version=_V1BETA1_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesConsumerQuotaMetricsListRequest(
      parent=_CONSUMER_SERVICE_RESOURCE % (consumer, service))
  return list_pager.YieldFromList(
      client.services_consumerQuotaMetrics,
      request,
      limit=limit,
      batch_size_attribute='pageSize',
      batch_size=page_size,
      field='metrics')


def UpdateQuotaOverrideCall(consumer,
                            service,
                            metric,
                            unit,
                            dimensions,
                            value,
                            force=False):
  """Update a quota override.

  Args:
    consumer: The consumer to update a quota override for, e.g. "projects/123".
    service: The service to update a quota override for.
    metric: The quota metric name.
    unit: The unit of quota metric.
    dimensions: The dimensions of the override in dictionary format. It can be
      None.
    value: The override integer value.
    force: Force override update even if the change results in a substantial
      decrease in available quota.

  Raises:
    exceptions.UpdateQuotaOverridePermissionDeniedException: when updating an
    override fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The quota override operation.
  """
  _ValidateConsumer(consumer)
  client = _GetClientInstance(version=_V1BETA1_VERSION)
  messages = client.MESSAGES_MODULE

  dimensions_message = _GetDimensions(messages, dimensions)
  request = messages.ServiceusageServicesConsumerQuotaMetricsImportConsumerOverridesRequest(
      parent=_CONSUMER_SERVICE_RESOURCE % (consumer, service),
      importConsumerOverridesRequest=messages.ImportConsumerOverridesRequest(
          inlineSource=messages.OverrideInlineSource(
              overrides=[
                  messages.QuotaOverride(
                      metric=metric,
                      unit=unit,
                      overrideValue=value,
                      dimensions=dimensions_message)
              ],),
          force=force),
  )
  try:
    return client.services_consumerQuotaMetrics.ImportConsumerOverrides(request)
  except (apitools_exceptions.HttpForbiddenError,
          apitools_exceptions.HttpNotFoundError) as e:
    exceptions.ReraiseError(
        e, exceptions.UpdateQuotaOverridePermissionDeniedException)


def DeleteQuotaOverrideCall(consumer,
                            service,
                            metric,
                            unit,
                            override_id,
                            force=False):
  """Delete a quota override.

  Args:
    consumer: The consumer to delete a quota override for, e.g. "projects/123".
    service: The service to delete a quota aoverride for.
    metric: The quota metric name.
    unit: The unit of quota metric.
    override_id: The override ID.
    force: Force override deletion even if the change results in a substantial
      decrease in available quota.

  Raises:
    exceptions.DeleteQuotaOverridePermissionDeniedException: when deleting an
    override fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The quota override operation.
  """
  _ValidateConsumer(consumer)
  client = _GetClientInstance(version=_V1BETA1_VERSION)
  messages = client.MESSAGES_MODULE

  parent = _GetMetricResourceName(consumer, service, metric, unit)
  name = _LIMIT_OVERRIDE_RESOURCE % (parent, override_id)
  request = messages.ServiceusageServicesConsumerQuotaMetricsLimitsConsumerOverridesDeleteRequest(
      name=name,
      force=force,
  )
  try:
    return client.services_consumerQuotaMetrics_limits_consumerOverrides.Delete(
        request)
  except (apitools_exceptions.HttpForbiddenError,
          apitools_exceptions.HttpNotFoundError) as e:
    exceptions.ReraiseError(
        e, exceptions.DeleteQuotaOverridePermissionDeniedException)


def _GetDimensions(messages, dimensions):
  if dimensions is None:
    return None
  dt = messages.QuotaOverride.DimensionsValue
  # sorted by key strings to maintain the unit test behavior consistency.
  return dt(
      additionalProperties=[
          dt.AdditionalProperty(key=k, value=dimensions[k])
          for k in sorted(dimensions.keys())
      ],)


def _GetMetricResourceName(consumer, service, metric, unit):
  """Get the metric resource name from metric name and unit.

  Args:
    consumer: The consumer to manage an override for, e.g. "projects/123".
    service: The service to manage an override for.
    metric: The quota metric name.
    unit: The unit of quota metric.

  Raises:
    exceptions.Error: when the limit with given metric and unit is not found.

  Returns:
    The quota override operation.
  """
  metrics = ListQuotaMetrics(consumer, service)
  for m in metrics:
    if m.metric == metric:
      for q in m.consumerQuotaLimits:
        if q.unit == unit:
          return q.name
  raise exceptions.Error('limit not found with name "%s" and unit "%s".' %
                         (metric, unit))


def _ValidateConsumer(consumer):
  for prefix in _VALID_CONSUMER_PREFIX:
    if consumer.startswith(prefix):
      return
  raise exceptions.Error('invalid consumer format "%s".' % consumer)


def _ListPublicServices(page_size=1000, list_filter='', limit=sys.maxsize):
  """Make API call to list public services.

  Args:
    page_size: The page size to list. default=1000
    list_filter: The filter to list public services.
    limit: The max number of services to display.

  Raises:
    exceptions.ListPublicServicesException: when listing public services fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Message.ListPublicServicesResponse: The public services.
  """
  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesListRequest(filter=list_filter)

  try:
    return list_pager.YieldFromList(
        _Lister(client.services),
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='services',
    )
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.ListPublicServicesException)


def _ListSharedServices(
    parent, page_size=1000, list_filter='', limit=sys.maxsize
):
  """Make API call to list shared services.

  Args:
    parent: The parent for which to list shared services.
    page_size: The page size to list. default=1000
    list_filter: The filter to list shared services.
    limit: The max number of services to display.

  Raises:
    exceptions.ListSharedServicesException: when listing shared services fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Message.ListSharedServicesResponse: The shared services.
  """
  client = _GetClientInstance(version=_V2BETA_VERSION)
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageSharedServicesListRequest(
      parent=parent, filter=list_filter
  )

  try:
    return list_pager.YieldFromList(
        _Lister(client.sharedServices),
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='sharedServices',
    )
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.ListSharedServicesException)


def _GetClientInstance(version='v1'):
  """Get a client instance for service usage."""
  # pylint:disable=protected-access
  # Specifically disable resource quota in all cases for service management.
  # We need to use this API to turn on APIs and sometimes the user doesn't have
  # this API turned on. We should always use the shared project to do this
  # so we can bootstrap users getting the appropriate APIs enabled. If the user
  # has explicitly set the quota project, then respect that.
  # pylint: disable=g-import-not-at-top
  from googlecloudsdk.core.credentials import transports
  # pylint: enable=g-import-not-at-top
  enable_resource_quota = (
      properties.VALUES.billing.quota_project.IsExplicitlySet())
  http_client = transports.GetApitoolsTransport(
      response_encoding=transport.ENCODING,
      enable_resource_quota=enable_resource_quota)
  return apis_internal._GetClientInstance(
      'serviceusage', version, http_client=http_client)


def _GetPrefixedServiceNames(services: List[str]) -> List[str]:
  """Prefixes service names with 'services/' if not already present."""
  return [
      f'services/{s}' if not s.startswith('services/') else s for s in services
  ]
