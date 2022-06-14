# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Used to validate integrations are setup correctly for deployment."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.run.integrations import types_utils
from googlecloudsdk.api_lib.services import enable_api
from googlecloudsdk.api_lib.services import services_util
from googlecloudsdk.api_lib.services import serviceusage
from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io


def GetIntegrationValidator(integration_type):
  """Gets the integration validator based on the integration type."""
  integration = types_utils.GetIntegration(integration_type)

  if integration is None:
    raise ValueError(
        'Integration type: [{}] has not been defined in types_utils'
        .format(integration_type))

  return Validator(integration)


class Validator:
  """Validates an integration is setup correctly for deployment."""

  def __init__(self, integration):
    self.integration = integration

  def ValidateEnabledGcpApis(self):
    """Validates user has all GCP APIs enabled for an integration.

    If the user does not have all the GCP APIs enabled they will
    be prompted to enable them.  If they do not want to enable them,
    then the process will exit.
    """
    project_id = properties.VALUES.core.project.Get()
    apis_not_enabled = self._GetDisabledGcpApis(project_id)

    if apis_not_enabled:
      apis_to_enable = '\n\t'.join(apis_not_enabled)
      console_io.PromptContinue(
          default=False,
          cancel_on_no=True,
          message=
          'The following APIs are not enabled on project [{0}]:\n\t{1}'.format(
              project_id, apis_to_enable
          ),
          prompt_string='Do you want enable these APIs to ' +
          'continue (this will take a few minutes)?'
      )

      log.status.Print(
          'Enabling APIs on project [{0}]...'.format(project_id))
      op = serviceusage.BatchEnableApiCall(project_id, apis_not_enabled)
      if not op.done:
        op = services_util.WaitOperation(op.name, serviceusage.GetOperation)
        services_util.PrintOperation(op)

  def _GetDisabledGcpApis(self, project_id):
    """Returns all GCP APIs needed for an integration.

    Args:
      project_id: The project's ID as a string.

    Returns:
      A list of strings.  Each item is a GCP API that is not enabled.
    """
    required_apis = self.integration['required_apis'].union(
        types_utils.BASELINE_APIS)
    project_id = properties.VALUES.core.project.Get()
    apis_not_enabled = [
        # iterable is sorted for scenario tests.  The order of API calls
        # should happen in the same order each time for the scenario tests.
        api for api in sorted(required_apis)
        if not enable_api.IsServiceEnabled(project_id, api)
    ]
    return apis_not_enabled

  def ValidateCreateParameters(self, parameters):
    """Validates parameters provided for creating an integration.

    Three things are done for all integrations created:
      1. Check that parameters passed in are valid (exist in types_utils
        mapping) and are not misspelled. These are parameters that will
        be recognized by the control plane.
      2. Check that all required parameters are provided.
      3. Check that default values are set for parameters
        that are not provided.

    Note that user provided params may be modified in place
    if default values are missing.

    Args:
      parameters: A dict where the key, value mapping is provided by the user.
    """
    self._ValidateProvidedParams(parameters)
    self._ValidateRequiredParams(parameters)
    self._SetupDefaultParams(parameters)

  def ValidateUpdateParameters(self, parameters):
    """Checks that certain parameters have not been updated.

    This firstly checks that the parameters provided exist in the mapping
    and thus are recognized the control plane.

    Args:
      parameters: A dict where the key, value mapping is provided by the user.
    """
    self._ValidateProvidedParams(parameters)
    self._CheckForInvalidUpdateParameters(parameters)

  def _CheckForInvalidUpdateParameters(self, user_provided_params):
    """Raises an exception that lists the parameters that can't be changed."""
    invalid_params = []
    for param_name, param in self.integration['parameters'].items():
      update_allowed = param.get('update_allowed', True)
      if not update_allowed and param_name in user_provided_params:
        invalid_params.append(param_name)

    if invalid_params:
      raise exceptions.ArgumentError(
          ('The following parameters: {} cannot be changed once the ' +
           'integration has been created')
          .format(self._RemoveEncoding(invalid_params))
      )

  def _ValidateProvidedParams(self, user_provided_params):
    """Checks that the user provided parameters exist in the mapping."""
    invalid_params = []
    for param in user_provided_params:
      if param not in self.integration['parameters']:
        invalid_params.append(param)

    if invalid_params:
      raise exceptions.ArgumentError(
          'The following parameters: {} are not allowed'.format(
              self._RemoveEncoding(invalid_params))
      )

  def _ValidateRequiredParams(self, user_provided_params):
    """Checks that required parameters are provided by the user."""
    missing_required_params = []
    for param_name, param in self.integration['parameters'].items():
      required = param.get('required', False)

      if required and param_name not in user_provided_params:
        missing_required_params.append(param_name)

    if missing_required_params:
      raise exceptions.ArgumentError(
          ('The following parameters: {} are required to create an ' +
           'integration of type [{}]')
          .format(
              self._RemoveEncoding(missing_required_params),
              self.integration['name'])
      )

  def _RemoveEncoding(self, elements):
    """Removes encoding for each element in the list.

    This causes inconsistencies in the scenario test when the output
    looks like [u'domain'] instead of ['domain']

    Args:
      elements: list

    Returns:
      list[str], encoding removed from each element.
    """
    return [str(x) for x in elements]

  def _SetupDefaultParams(self, user_provided_params):
    """Ensures that default parameters have a value if not set."""
    for param_name, param in self.integration['parameters'].items():
      if ('default' in param and
          param_name not in user_provided_params):
        user_provided_params[param_name] = param['default']
