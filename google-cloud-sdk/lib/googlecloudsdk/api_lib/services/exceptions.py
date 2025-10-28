# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Wrapper for user-visible error exceptions to raise in the CLI."""
from googlecloudsdk.api_lib.util import exceptions as api_lib_exceptions
from googlecloudsdk.core import exceptions as core_exceptions


class Error(core_exceptions.Error):
  """Base class for Services errors."""


class EnableServiceException(Error):
  """Exception for enable service command."""


class ListServicesException(Error):
  """List services command."""


class ListMcpServicesException(Error):
  """List MCP services command."""


class GetServicePermissionDeniedException(Error):
  """Permission denied exception for get service command."""


class CreateQuotaOverridePermissionDeniedException(Error):
  """Permission denied exception for create quota override command."""


class UpdateQuotaOverridePermissionDeniedException(Error):
  """Permission denied exception for update quota override command."""


class DeleteQuotaOverridePermissionDeniedException(Error):
  """Permission denied exception for delete quota override command."""


class CreateConnectionsPermissionDeniedException(Error):
  """Permission denied exception for create connection command."""


class DeleteConnectionsPermissionDeniedException(Error):
  """Permission denied exception for create connection command."""


class UpdateConnectionsPermissionDeniedException(Error):
  """Permission denied exception for list connections command."""


class ListConnectionsPermissionDeniedException(Error):
  """Permission denied exception for list connections command."""


class EnableVpcServiceControlsPermissionDeniedException(Error):
  """Permission denied exception for enable vpc service controls command."""


class GetVpcServiceControlsPermissionDeniedException(Error):
  """Permission denied exception for get vpc service controls command."""


class DisableVpcServiceControlsPermissionDeniedException(Error):
  """Permission denied exception for disable vpc service controls command."""


class CreatePeeredDnsDomainPermissionDeniedException(Error):
  """Permission denied exception for create peered dns domain command."""


class DeletePeeredDnsDomainPermissionDeniedException(Error):
  """Permission denied exception for delete peered dns domain command."""


class ListPeeredDnsDomainsPermissionDeniedException(Error):
  """Permission denied exception for list peered dns domains command."""


class GenerateServiceIdentityPermissionDeniedException(Error):
  """Permission denied exception for generate service identitiy command."""


class GetConsumerPolicyException(Error):
  """Exception for get consumer policy."""


class UpdateConsumerPolicyException(Error):
  """Update consumer policy."""


class GetReverseDependencyClosurePermissionDeniedException(Error):
  """Permission denied exception for get reverse dependency closure."""


class ListFlattenedMembersPermissionDeniedException(Error):
  """Permission denied exception for list flattened members."""


class ListGroupMembersException(Error):
  """Exception for list group members."""


class FetchValueInfoPermissionDeniedException(Error):
  """Permission denied exception for fetch value info group members."""


class GetEffectivePolicyException(Error):
  """Exception for get effective policy."""


class FetchPublicValueInfoPermissionDeniedException(Error):
  """Permission denied exception for fetch public value info group members."""


class TestEnabledException(Error):
  """Exception for test enabled."""


class ListDescendantServicesException(Error):
  """Exception for list descendant services."""


class ListExpandedMembersException(Error):
  """Exception for list expanded members."""


class ListAncestorGroupsPermissionDeniedException(Error):
  """Permission denied exception for list ancestor groups."""


class BatchGetServiceException(Error):
  """Batch get service."""


class GetServiceException(Error):
  """Get service."""


class ListCategoryServicesException(Error):
  """List category service."""


class ListPublicServicesException(Error):
  """List public service."""


class ListSharedServicesException(Error):
  """List shared service."""


class AnalyzeConsumerPolicyException(Error):
  """Analyze consumer policy."""


class TestMcpEnabledException(Error):
  """Exception for test MCP enabled."""


class GetMcpPolicyException(Error):
  """Exception for get MCP policy."""


class GetContentSecurityPolicyException(Error):
  """Exception for get content security policy."""


class UpdateContentSecurityPolicyException(Error):
  """Exception for update content security policy."""


class AddContentSecurityProviderException(Error):
  """Exception for add content security provider."""


class RemoveContentSecurityProviderException(Error):
  """Exception for remove content security provider."""


class GetEffectiveMcpPolicyException(Error):
  """Exception for get effective MCP policy."""


class UpdateMcpPolicyException(Error):
  """Exception for update MCP policy."""


class EnableMcpServiceException(Error):
  """Exception for enable MCP service."""


class OperationErrorException(Error):
  """Operation error."""


class TimeoutError(Error):
  """Timeout error."""


def ReraiseError(err, klass):
  """Transform and re-raise error helper."""
  core_exceptions.reraise(klass(api_lib_exceptions.HttpException(err)))


class ConfigError(Error):
  """Raised when unable to parse a config file."""

  def __init__(self, message=None, **kwargs):
    message = message or 'Config Error.'
    super(ConfigError, self).__init__(message, **kwargs)
