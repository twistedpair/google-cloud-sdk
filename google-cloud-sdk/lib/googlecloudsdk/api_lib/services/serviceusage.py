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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import copy
import enum
import sys

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.services import exceptions
from googlecloudsdk.api_lib.util import apis_internal
from googlecloudsdk.api_lib.util import http_retry
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import transport
from googlecloudsdk.core.credentials import transports

_PROJECT_RESOURCE = 'projects/%s'
_FOLDER_RESOURCE = 'folders/%s'
_ORGANIZATION_RESOURCE = 'organizations/%s'
_PROJECT_SERVICE_RESOURCE = 'projects/%s/services/%s'
_FOLDER_SERVICE_RESOURCE = 'folders/%s/services/%s'
_ORG_SERVICE_RESOURCE = 'organizations/%s/services/%s'
_SERVICE_RESOURCE = 'services/%s'
_DEPENDENCY_GROUP = '/groups/dependencies'
_REVERSE_CLOSURE = '/reverseClosure'
_CONSUMER_SERVICE_RESOURCE = '%s/services/%s'
_CONSUMER_POLICY_DEFAULT = '/consumerPolicies/%s'
_EFFECTIVE_POLICY = '/effectivePolicy'
_GOOGLE_GROUP_RESOURCE = 'groups/googleServices'
_LIMIT_OVERRIDE_RESOURCE = '%s/consumerOverrides/%s'
_VALID_CONSUMER_PREFIX = frozenset({'projects/', 'folders/', 'organizations/'})
_V1_VERSION = 'v1'
_V2_VERSION = 'v2'
_V1BETA1_VERSION = 'v1beta1'
_V1ALPHA_VERSION = 'v1alpha'
_V2ALPHA_VERSION = 'v2alpha'
_TOO_MANY_REQUESTS = 429

# Map of services which should be protected from being disabled by
# prompting the user for  confirmation
_PROTECTED_SERVICES = {
    'anthos.googleapis.com': ('Warning: Disabling this service will '
                              'also automatically disable any running '
                              'Anthos clusters.')
}


class ContainerType(enum.Enum):
  PROJECT_SERVICE_RESOURCE = 1
  FOLDER_SERVICE_RESOURCE = 2
  ORG_SERVICE_RESOURCE = 3


def GetProtectedServiceWarning(service_name):
  """Return the warning message associated with a protected service."""
  return _PROTECTED_SERVICES.get(service_name)


def GetConsumerPolicyV2Alpha(policy_name):
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
    The consumer policy
  """
  client = _GetClientInstance('v2alpha')
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageConsumerPoliciesGetRequest(name=policy_name)

  try:
    return client.consumerPolicies.Get(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.GetConsumerPolicyPermissionDeniedException
    )


# TODO(b/309115642) Remove after the migration is completed.
def GetConsumerPolicyV2(policy_name):
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
    The consumer policy
  """
  client = _GetClientInstance('v2')
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageConsumerPoliciesGetRequest(name=policy_name)

  try:
    return client.consumerPolicies.Get(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.GetConsumerPolicyPermissionDeniedException
    )


def CheckValue(name, service):
  """Make API call to check value.

  Args:
    name: Parent resource to check the value against hierarchically.
      format-"projects/100", "folders/101" or "organizations/102".
    service: Service name to check if the targeted resource can use this
      service. Current supported value: SERVICE (format: "services/{service}").

  Raises:
    exceptions.CheckValuePermissionDeniedException: when checking value for a
      service and resource.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Checked Value.
  """
  client = _GetClientInstance('v2')
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageCheckValueRequest(
      name=name,
      checkValueRequest=messages.CheckValueRequest(checkedValue=service),
  )

  try:
    return client.v2.CheckValue(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.CheckValuePermissionDeniedException)


def GetEffectivePolicy(name):
  """Make API call to get a effective policy.

  Args:
    name: The name of the effective policy.Currently supported format
      '{resource_type}/{resource_name}/effectivePolicy'. For example,
      'projects/100/effectivePolicy'.

  Raises:
    exceptions.GetEffectiverPolicyPermissionDeniedException: when getting a
      effective policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The Effective Policy
  """
  client = _GetClientInstance('v2')
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageGetEffectivePolicyRequest(name=name)

  try:
    return client.v2.GetEffectivePolicy(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.GetEffectiverPolicyPermissionDeniedException
    )


def FetchValueInfo(resource, values):
  """Make API call to fetch value info for the services.

  Args:
    resource: The target resource.
    values: The name of the value to get metadata. A single request can get a
      maximum of 20 services at a time. If more than 20 services are specified,
      the request will fail.

  Raises:
    exceptions.FetchValueInfoPermissionDeniedException: when
      fetching  value info fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Value Info for the specificed values.
  """
  client = _GetClientInstance('v2')
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageFetchValueInfoRequest(
      fetchValueInfoRequest=messages.FetchValueInfoRequest(values=values),
      name=resource,
  )

  try:
    return client.v2.FetchValueInfo(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.FetchValueInfoPermissionDeniedException
    )


def FetchPublicValueInfo(values):
  """Make API call to fetch public value info for the services.

  Args:
    values: The name of the value to get metadata. A single request can get a
      maximum of 20 services at a time. If more than 20 services are specified,
      the request will fail.

  Raises:
    exceptions.FetchPublicValueInfoPermissionDeniedException: when
      fetching public value info fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
   Public Value Info for the specificed values.
  """
  client = _GetClientInstance('v2')
  messages = client.MESSAGES_MODULE

  request = messages.FetchPublicValueInfoRequest(
      values=values,
  )

  try:
    return client.publicValueInfo.Fetch(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.FetchPublicValueInfoPermissionDeniedException
    )


def UpdateConsumerPolicy(consumerpolicy, name, force=False):
  """Make API call to update a consumer policy.

  Args:
    consumerpolicy: The consumer policy to update.
    name: The resource name of the policy. Currently supported format
      '{resource_type}/{resource_name}/consumerPolicies/default. For example,
      'projects/100/consumerPolicies/default'.
    force: Disable service with usage within last 30 days or disable recently
      enabled service.

  Raises:
    exceptions.UpdateConsumerPolicyPermissionDeniedException: when updating a
      consumer policy fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Updated consumer policy
  """
  client = _GetClientInstance('v2')
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageUpdateConsumerPolicyRequest(
      consumerPolicy=consumerpolicy, name=name, force=force
  )

  try:
    return client.v2.UpdateConsumerPolicy(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.UpdateConsumerPolicyPermissionDeniedException
    )
  except apitools_exceptions.HttpBadRequestError as e:
    log.status.Print(
        'Provide the --force flag if you wish to force disable services.'
    )
    exceptions.ReraiseError(e, exceptions.Error)


def GetReverseClosure(resource, service):
  """Make API call to get reverse dependency of a specific service.

  Args:
    resource: The target resource.
    service: The identifier of the service to get reversed depenedency of.

  Raises:
    exceptions.GetReverseDependencyClosurePermissionDeniedException: when
      getting a reverse dependency closure for resource and service fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Reverse dependency closure
  """
  client = _GetClientInstance('v2')
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesGetReverseClosureRequest(
      name=resource + '/' + _SERVICE_RESOURCE % service + _REVERSE_CLOSURE
  )

  try:
    return client.services.GetReverseClosure(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.GetReverseDependencyClosurePermissionDeniedException
    )


def ListFlattenedMembers(resource, service_group):
  """Make API call to list flattened members of a specific service group.

  Args:
    resource: The target resource.
    service_group: Service group which owns this collection of flattened
      members, for example,
      'services/compute.googleapis.com/groups/dependencies'.

  Raises:
    exceptions.ListFlattenedMembersPermissionDeniedException: when listing
      flattened members fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Flattened members in the given service group.
  """
  client = _GetClientInstance('v2')
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesGroupsFlattenedMembersListRequest(
      parent=resource + '/' + service_group
  )

  try:
    return client.services_groups_flattenedMembers.List(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.ListFlattenedMembersPermissionDeniedException
    )


def ListGroupMembers(resource, service_group, page_size=50, limit=sys.maxsize):
  """Make API call to list group members of a specific service group.

  Args:
    resource: The target resource.
    service_group: Service group which owns a collection of group members, for
      example, 'services/compute.googleapis.com/groups/dependencies'.
    page_size: The page size to list.default=50
    limit: The max number of services to display.

  Raises:
    exceptions.ListGroupMembersPermissionDeniedException: when listing
      group members fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    Group members in the given service group.
  """
  client = _GetClientInstance('v2')
  messages = client.MESSAGES_MODULE

  request = messages.ServiceusageServicesGroupsMembersListRequest(
      parent=resource + '/' + service_group
  )

  try:
    return list_pager.YieldFromList(
        _Lister(client.services_groups_members),
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='groupMembers',
    )
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.ListGroupMembersPermissionDeniedException
    )


def ListDescendantServices(resource, service_group):
  """Make API call to list descendant services of a specific service group.

  Args:
    resource: The target resource.
    service_group: Service group, for example,
      'services/compute.googleapis.com/groups/dependencies'.

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
    return client.services_groups_descendantServices.List(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.ListDescendantServicesPermissionDeniedException
    )


def AddEnableRule(
    services,
    project,
    consumer_policy_name='default',
    folder=None,
    organization=None,
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

  Raises:
    exceptions.EnableServicePermissionDeniedException: when enabling API fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The result of the operation
  """
  client = _GetClientInstance('v2')
  messages = client.MESSAGES_MODULE

  resource_name = _PROJECT_RESOURCE % project

  if folder:
    resource_name = _FOLDER_RESOURCE % folder

  if organization:
    resource_name = _ORGANIZATION_RESOURCE % organization

  policy_name = resource_name + _CONSUMER_POLICY_DEFAULT % consumer_policy_name

  try:
    policy = GetConsumerPolicyV2(policy_name)

    services_to_enabled = set()

    for service in services:
      services_to_enabled.add(_SERVICE_RESOURCE % service)
      list_flatterned_members = ListFlattenedMembers(
          resource_name, _SERVICE_RESOURCE % service + _DEPENDENCY_GROUP
      )
      for member in list_flatterned_members.flattenedMembers:
        services_to_enabled.add(member.name)

    if policy.enableRules:
      policy.enableRules[0].values.extend(list(services_to_enabled))
    else:
      policy.enableRules.append(
          messages.EnableRule(values=list(services_to_enabled))
      )

    return UpdateConsumerPolicy(policy, policy_name)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.EnableServicePermissionDeniedException
    )


def RemoveEnableRule(
    project,
    service,
    consumer_policy_name='default',
    force=False,
    folder=None,
    organization=None,
):
  """Make API call to disable a specific service.

  Args:
    project: The project for which to disable the service.
    service: The identifier of the service to disable, for example
      'serviceusage.googleapis.com'.
    consumer_policy_name: Name of consumer policy. The default name is
      "default".
    force: Disable service with usage within last 30 days or disable recently
      enabled service or disable the service even if there are enabled services
      which depend on it. This also disables the services which depend on the
      service to be disabled.
    folder: The folder for which to disable the service.
    organization: The organization for which to disable the service.

  Raises:
    exceptions.EnableServicePermissionDeniedException: when disabling API fails.
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
    current_policy = GetConsumerPolicyV2(policy_name)

    reverse_closure = GetReverseClosure(resource_name, service)

    if not force:
      enabled = set()

      for enable_rule in current_policy.enableRules:
        enabled.update(enable_rule.values)

      enabled_dependents = set()

      for value in reverse_closure.values:
        if value in enabled:
          enabled_dependents.add(value)

      if enabled_dependents:
        enabled_dependents = ','.join(enabled_dependents)
        raise exceptions.ConfigError(
            'The service '
            + service
            + ' is depended on by the following active service(s) '
            + enabled_dependents
            + ' . Provide the --force flag if you wish to force disable'
            ' services.'
        )

    to_remove = {reverse_closure.service}
    to_remove.update(reverse_closure.values)

    updated_consumer_poicy = copy.deepcopy(current_policy)
    updated_consumer_poicy.enableRules.clear()

    for enable_rule in current_policy.enableRules:
      rule = copy.deepcopy(enable_rule)
      for value in enable_rule.values:
        if value in to_remove:
          rule.values.remove(value)
      if rule.values:
        updated_consumer_poicy.enableRules.append(rule)

    return UpdateConsumerPolicy(
        updated_consumer_poicy, policy_name, force=force
    )
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.EnableServicePermissionDeniedException
    )
  except apitools_exceptions.HttpBadRequestError as e:
    log.status.Print(
        'Provide the --force flag if you wish to force disable services.'
    )
    # TODO(b/274633761) Repharse error message to avoid showing internal
    # flags in the error message.
    exceptions.ReraiseError(e, exceptions.Error)


def EnableApiCall(project, service):
  """Make API call to enable a specific service.

  Args:
    project: The project for which to enable the service.
    service: The identifier of the service to enable, for example
      'serviceusage.googleapis.com'.

  Raises:
    exceptions.EnableServicePermissionDeniedException: when enabling API fails.
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
    exceptions.ReraiseError(e,
                            exceptions.EnableServicePermissionDeniedException)


def BatchEnableApiCall(project, services):
  """Make API call to batch enable services.

  Args:
    project: The project for which to enable the services.
    services: Iterable of identifiers of services to enable.

  Raises:
    exceptions.EnableServicePermissionDeniedException: when enabling API fails.
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
    exceptions.ReraiseError(e,
                            exceptions.EnableServicePermissionDeniedException)


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
    exceptions.EnableServicePermissionDeniedException: when disabling API fails.
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
    exceptions.ReraiseError(e,
                            exceptions.EnableServicePermissionDeniedException)
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


def ListServicesV2(
    project,
    enabled,
    page_size,
    limit=sys.maxsize,
    folder=None,
    organization=None,
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
    exceptions.ListServicesPermissionDeniedException: when listing services
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
  try:
    if enabled:
      policy_name = resource_name + _EFFECTIVE_POLICY
      consumerpolicy = GetEffectivePolicy(policy_name).consumerPolicy

      for rules in consumerpolicy.enableRules:
        for value in rules.values:
          if limit == 0:
            break
          services[value] = ''
          limit -= 1

      service_list = list(services.keys())
      for value in range(0, len(service_list), 20):
        response = FetchValueInfo(
            resource_name, values=service_list[value : value + 20]
        )
        for value_info in response.valueInfos:
          services[value_info.serviceValue.name] = value_info.title

    else:
      for members_info in ListGroupMembers(
          resource_name, _GOOGLE_GROUP_RESOURCE, page_size, limit
      ):
        services[members_info.name] = ''

      service_list = list(services.keys())
      # TODO(b/274633761)Switch to FetchValueInfo once the IAM permission manual
      # check issue is fixed and test it.
      for value in range(0, len(service_list), 20):
        response = FetchPublicValueInfo(values=service_list[value : value + 20])
        for value_info in response.valueInfos:
          services[value_info.serviceValue.name] = value_info.title

    result = []
    service_info = collections.namedtuple('ServiceList', ['name', 'title'])
    for service in service_list:
      result.append(service_info(name=service, title=services[service]))

    return result
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(
        e, exceptions.EnableServicePermissionDeniedException
    )


def ListServices(project, enabled, page_size, limit):
  """Make API call to list services.

  Args:
    project: The project for which to list services.
    enabled: List only enabled services.
    page_size: The page size to list.
    limit: The max number of services to display.

  Raises:
    exceptions.ListServicesPermissionDeniedException: when listing services
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
    exceptions.ReraiseError(e,
                            exceptions.EnableServicePermissionDeniedException)


def GetOperation(name):
  """Make API call to get an operation.

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


def GetOperationV2(name):
  """Make API call to get an operation.

  Args:
    name: The name of operation.

  Raises:
    exceptions.OperationErrorException: when the getting operation API fails.
    apitools_exceptions.HttpError: Another miscellaneous error with the service.

  Returns:
    The result of the operation
  """
  client = _GetClientInstance('v2')
  messages = client.MESSAGES_MODULE
  request = messages.ServiceusageOperationsGetRequest(name=name)
  try:
    return client.operations.Get(request)
  except (
      apitools_exceptions.HttpForbiddenError,
      apitools_exceptions.HttpNotFoundError,
  ) as e:
    exceptions.ReraiseError(e, exceptions.OperationErrorException)


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


def _GetClientInstance(version='v1'):
  """Get a client instance for service usage."""
  # pylint:disable=protected-access
  # Specifically disable resource quota in all cases for service management.
  # We need to use this API to turn on APIs and sometimes the user doesn't have
  # this API turned on. We should always use the shared project to do this
  # so we can bootstrap users getting the appropriate APIs enabled. If the user
  # has explicitly set the quota project, then respect that.
  enable_resource_quota = (
      properties.VALUES.billing.quota_project.IsExplicitlySet())
  http_client = transports.GetApitoolsTransport(
      response_encoding=transport.ENCODING,
      enable_resource_quota=enable_resource_quota)
  return apis_internal._GetClientInstance(
      'serviceusage', version, http_client=http_client)
