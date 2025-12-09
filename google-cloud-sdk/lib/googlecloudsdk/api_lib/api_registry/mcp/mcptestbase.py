# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Base class for MCP command tests."""

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py.testing import mock
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.core import properties
from tests.lib import cli_test_base
from tests.lib import parameterized
from tests.lib import sdk_test_base


class McpTestBaseForEnableDisableTests(
    sdk_test_base.WithFakeAuth,
    parameterized.TestCase,
    cli_test_base.CliTestBase,
):
  """Base class for MCP enable and disable command tests."""

  def SetUp(self):
    self.project = 'test-gcp-project-12345'
    properties.VALUES.core.project.Set(self.project)
    self.su_messages = core_apis.GetMessagesModule('serviceusage', 'v2beta')
    self.mocked_su_client = mock.Client(
        core_apis.GetClientClass('serviceusage', 'v2beta'),
        real_client=core_apis.GetClientInstance(
            'serviceusage', 'v2beta', no_http=True))
    self.mocked_su_client.Mock()
    self.addCleanup(self.mocked_su_client.Unmock)

  def _MakeHttpError(self, status, message='error'):
    return apitools_exceptions.HttpError({'status': status}, message, '')

  def _expectGetMcpPolicyCall(self, project, policy_old, exception=None):
    expected_name = f'projects/{project}/mcpPolicies/default'
    expected_request = self.su_messages.ServiceusageMcpPoliciesGetRequest(
        name=expected_name
    )
    self.mocked_su_client.mcpPolicies.Get.Expect(
        request=expected_request,
        response=policy_old if not exception else None,
        exception=exception,
    )

  def _expectUpdateMcpPolicyCall(
      self, policy_new, operation_name, exception=None):
    expected_request = self.su_messages.ServiceusageMcpPoliciesPatchRequest(
        mcpPolicy=policy_new,
        force=False,
        name='projects/test-gcp-project-12345/mcpPolicies/default',
        validateOnly=False,
    )
    mock_operation = self.su_messages.Operation(
        name=operation_name,
        done=False  # Typically starts as not done
    )
    self.mocked_su_client.mcpPolicies.Patch.Expect(
        request=expected_request,
        response=mock_operation if not exception else None,
        exception=exception,
    )

  def _expectGetOperationCall(self, operation_name, policy_new, exception=None):
    expected_request = self.su_messages.ServiceusageOperationsGetRequest(
        name=operation_name
    )
    response_value = encoding.PyValueToMessage(
        self.su_messages.Operation.ResponseValue,
        encoding.MessageToPyValue(policy_new)
    )
    response_op = None
    if not exception:
      response_op = self.su_messages.Operation(
          name=operation_name,
          done=True,
          response=response_value
      )
    self.mocked_su_client.operations.Get.Expect(
        request=expected_request,
        response=response_op,
        exception=exception,
    )

  def _expectGetServiceCall(self, project, service_name, service_state,
                            exception=None):
    expected_name = f'projects/{project}/services/{service_name}'
    expected_request = self.su_messages.ServiceusageServicesGetRequest(
        name=expected_name,
        view=self.su_messages.ServiceusageServicesGetRequest.ViewValueValuesEnum.SERVICE_STATE_VIEW_FULL
    )
    self.mocked_su_client.services.Get.Expect(
        request=expected_request,
        response=service_state if not exception else None,
        exception=exception,
    )


class McpAlphaForEnableDisableTests(McpTestBaseForEnableDisableTests):
  """Base class for MCP enable and disable command tests in alpha track."""

  def PreSetUp(self):
    self.track = calliope_base.ReleaseTrack.ALPHA


class McpBetaForEnableDisableTests(McpTestBaseForEnableDisableTests):
  """Base class for MCP enable and disable command tests in beta track."""

  def PreSetUp(self):
    self.track = calliope_base.ReleaseTrack.BETA
