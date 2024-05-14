# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Common validators for cloud ops agents policy create and update commands."""

import enum
import re
import sys
from typing import Set

from googlecloudsdk.api_lib.compute.instances.ops_agents import cloud_ops_agents_exceptions as exceptions
from googlecloudsdk.api_lib.compute.instances.ops_agents import cloud_ops_agents_policy as agents_policy
from googlecloudsdk.api_lib.compute.instances.ops_agents import cloud_ops_agents_util as util
from googlecloudsdk.core import log
from googlecloudsdk.generated_clients.apis.osconfig.v1 import osconfig_v1_messages as osconfig


_VERSION_RE = re.compile(
    '|'.join((
        'latest',
        r'2\.\*\.\*',  # Pinned major version.
        r'2\.\d+\.\d+',  # Pinned version.
    ))
)
_SUPPORTED_OS_SHORT_NAMES_AND_VERSIONS = {
    'centos': {
        '7',
        '8',
    },
    'rhel': {
        '7',
        '8',
        '9',
    },
    'rocky': {
        '8',
        '9',
    },
    'sles': {
        '12',
        '15',
    },
    'debian': {
        '10',
        '11',
        '12',
    },
    'ubuntu': {
        '18.04',
        '20.04',
        '22.04',
        '23.10',
    },
    'windows': {
        '10',
        '6',
    },
}

_SUPPORTED_PACKAGE_STATE = frozenset({
    'installed',
    'removed',
})

_StrEnum = (
    (enum.StrEnum,) if sys.version_info[:2] >= (3, 11) else (str, enum.Enum)
)


class AgentsInstanceFilterConflictErrorMessage(*_StrEnum):
  ALL_TRUE = (
      'No other values can be declared under instanceFilter if all is set'
      ' to true'
  )
  EMPTY_INSTANCE_FILTER = (
      'There should be at least a single value in either'
      ' instanceFilter.inclusionLabels, instanceFilter.exclusionLabels or'
      ' instanceFilter.inventories'
  )


class AgentsVersionInvalidFormatError(exceptions.PolicyValidationError):
  """Raised when agents version format is invalid."""

  def __init__(self, version):
    super(AgentsVersionInvalidFormatError, self).__init__(
        'The agents version [{}] is not allowed. Expected values: [latest], '
        'or anything in the format of '
        '[MAJOR_VERSION.MINOR_VERSION.PATCH_VERSION] or '
        '[MAJOR_VERSION.*.*].'.format(version)
    )


class AgentsPackageStateInvalidFormatError(exceptions.PolicyValidationError):
  """Raised when agents package_state format is invalid."""

  def __init__(self, package_state):
    super(AgentsPackageStateInvalidFormatError, self).__init__(
        'The agents packageState [{}] is not allowed. Expected values:'
        ' [installed] or [removed] '.format(package_state)
    )


class AgentsInstanceFilterEmptyError(exceptions.PolicyValidationError):
  """Raised when instance_filter is empty."""

  def __init__(self):
    super(AgentsInstanceFilterEmptyError, self).__init__(
        'instanceFilter cannot be empty'
    )


class AgentsInstanceFilterConflictError(exceptions.PolicyValidationError):
  """Raised when an invalid instance_filter is created."""

  def __init__(self, error_message: AgentsInstanceFilterConflictErrorMessage):
    super(AgentsInstanceFilterConflictError, self).__init__(
        'Invalid instanceFilter: {}'.format(error_message)
    )


class AgentsOsTypeNotSupportedError(exceptions.PolicyValidationError):
  """Raised when agents OS type is not supported."""

  def __init__(self, short_name: str, version: str):
    super(AgentsOsTypeNotSupportedError, self).__init__(
        'The combination of short name [{}] and version [{}] is not supported. '
        'The supported versions are: {}.'.format(
            short_name,
            version,
            '; '.join(
                '%s %s' % (k, ','.join(sorted(v)))
                for k, v in sorted(
                    _SUPPORTED_OS_SHORT_NAMES_AND_VERSIONS.items()
                )
            ),
        )
    )


def ValidateOpsAgentsPolicy(policy: agents_policy.OpsAgentsPolicy):
  """Validates semantics of a Cloud Ops agents policy.

  This validation happens after the arg parsing stage. At this point, we can
  assume that the field is an OpsAgentsPolicy object.

  Args:
    policy: ops_agents.OpsAgentPolicy. The policy that manages Ops agents.

  Raises:
    PolicyValidationMultiError that contains a list of validation
    errors from the following list.
    * AgentsVersionInvalidFormatError:
      Agents version format is invalid.
    * AgentsPackageStateInvalidFormatError:
      Agents package_state format is invalid.
    * AgentsInstanceFilterEmptyError:
      Instance filter format is empty.
    * AgentsInstanceFilterConflictError:
      Instance filter must have all set to true with nothing else added or there
      should be at least a single value in either
      inclusionLabels, exclusionLabels or
      inventories
    * AgentsOsTypeNotSupportedError:
      The combination of the OS short name and version is not supported.
  """
  errors = _ValidateAgentRules(policy.agents_rule) + _ValidateInstanceFilter(
      policy.instance_filter
  )
  if errors:
    raise exceptions.PolicyValidationMultiError(errors)
  log.debug(f'Cloud Ops Agents policy validation passed.\n{policy}')


def _ValidateAgentRules(agents_rule: agents_policy.OpsAgentsPolicy.AgentsRule):
  return _ValidateAgentsRuleVersion(
      agents_rule.version, agents_rule.package_state
  ) + _ValidateAgentsRulePackageState(agents_rule.package_state)


def _ValidateAgentsRuleVersion(
    version: str,
    package_state: str,
) -> Set[AgentsVersionInvalidFormatError]:
  if not (
      (package_state == 'removed' and not version)
      or _VERSION_RE.fullmatch(version)
  ):
    return [AgentsVersionInvalidFormatError(version)]
  return []


def _ValidateAgentsRulePackageState(
    package_state: str,
) -> Set[AgentsPackageStateInvalidFormatError]:
  if package_state not in _SUPPORTED_PACKAGE_STATE:
    return [AgentsPackageStateInvalidFormatError(package_state)]
  return []


def _ValidateInstanceFilter(
    instance_filter: osconfig.OSPolicyAssignmentInstanceFilter,
):
  return (
      _ValidateInstanceFilterIsNotEmpty(instance_filter)
      + _ValidateInstanceFilterAllTrue(instance_filter)
      + _ValidateInstanceFilterAllFalse(instance_filter)
      + _ValidateInventories(instance_filter)
  )


def _ValidateInstanceFilterIsNotEmpty(
    instance_filter: osconfig.OSPolicyAssignmentInstanceFilter,
) -> Set[AgentsInstanceFilterEmptyError]:
  return [] if instance_filter else [AgentsInstanceFilterEmptyError()]


def _ValidateInstanceFilterAllTrue(
    instance_filter: osconfig.OSPolicyAssignmentInstanceFilter,
) -> Set[AgentsInstanceFilterConflictError]:
  """Validates that if instance_filter.all is true no other values are present.

  Args:
    instance_filter: cloud ops agents instance filter.

  Returns:
  An empty list if the validation passes. A singleton list with the following
  error if the validation fails.
    * AgentsInstanceFilterConflictError:
      Instance filter must have all set to true with nothing else added or there
      should be at least a single value in either inclusionLabels,
      exclusionLabels or inventories.
  """
  if instance_filter.all and (
      instance_filter.inclusionLabels
      or instance_filter.exclusionLabels
      or instance_filter.inventories
  ):
    return [
        AgentsInstanceFilterConflictError(
            AgentsInstanceFilterConflictErrorMessage.ALL_TRUE
        )
    ]
  return []


def _ValidateInstanceFilterAllFalse(
    instance_filter: osconfig.OSPolicyAssignmentInstanceFilter,
) -> Set[AgentsInstanceFilterConflictError]:
  """Validates that if instance_filter.all is false that there is a value in either inclusionLabels, exclusionLabels, or inventories.

  Args:
    instance_filter: cloud ops agents instance filter.

  Returns:
  An empty list if the validation passes. A singleton list with the following
  error if the validation fails.
    * AgentsInstanceFilterConflictError:
    There should be at least a single value in either inclusionLabels,
    exclusionLabels or inventories.
  """
  if (
      not instance_filter.all
      and not instance_filter.inclusionLabels
      and not instance_filter.exclusionLabels
      and not instance_filter.inventories
  ):
    return [
        AgentsInstanceFilterConflictError(
            AgentsInstanceFilterConflictErrorMessage.EMPTY_INSTANCE_FILTER
        )
    ]
  return []


def _ValidateInventories(
    instance_filter: osconfig.OSPolicyAssignmentInstanceFilter,
) -> Set[AgentsOsTypeNotSupportedError]:
  """Validates that inventories only contain Ops Agents supported OS types and version.

  Args:
    instance_filter: cloud ops agents instance filter.

  Returns:
  An empty list if the validation passes. A list with the following
  error if the validation fails.
    * AgentsOsTypeNotSupportedError:
    The combination of the OS short name and version is not supported.
  """
  errors = []
  for inventory in instance_filter.inventories:
    if not (
        inventory.osShortName in _SUPPORTED_OS_SHORT_NAMES_AND_VERSIONS
        and inventory.osVersion
        in _SUPPORTED_OS_SHORT_NAMES_AND_VERSIONS[inventory.osShortName]
    ):
      errors.append(
          AgentsOsTypeNotSupportedError(
              inventory.osShortName, inventory.osVersion
          )
      )
  return errors


def IsCloudOpsAgentsPolicy(policy: osconfig.OSPolicyAssignment) -> bool:
  """Returns whether the policy was created with the Ops Agent command.
  """
  instance_filter = policy.instanceFilter
  if len(policy.osPolicies) > 1:
    return False

  agents_rule = util.GetAgentsRuleFromDescription(
      policy.osPolicies[0].description
  )
  if agents_rule is None:
    return False

  try:
    ValidateOpsAgentsPolicy(
        agents_policy.OpsAgentsPolicy(agents_rule, instance_filter)
    )
  except exceptions.PolicyValidationError:
    return False
  return True
