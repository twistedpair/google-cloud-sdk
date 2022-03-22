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
"""Used for validating parameters provided to create and update integrations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.run.integrations import types_utils
from googlecloudsdk.command_lib.run import exceptions


def GetIntegrationValidator(integration_type, parameters):
  """Gets the integration validator based on the integration type."""
  integration = types_utils.GetIntegration(integration_type)

  if integration is None:
    raise ValueError(
        'Integration type: [{}] has not been defined in types_utils'
        .format(integration_type))

  return Validator(integration, parameters)


class Validator:
  """Validates parameters for creating and updating integrations."""

  def __init__(self, integration, parameters):
    self.integration = integration
    self.user_provided_params = parameters

  def ValidateCreateParameters(self):
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
    """
    self._ValidateProvidedParams()
    self._ValidateRequiredParams()
    self._SetupDefaultParams()

  def ValidateUpdateParameters(self):
    """Checks that certain parameters have not been updated.

    This firstly checks that the parameters provided exist in the mapping
    and thus are recognized the control plane.
    """
    self._ValidateProvidedParams()
    self._CheckForInvalidUpdateParameters()

  def _CheckForInvalidUpdateParameters(self):
    """Raises an exception that lists the parameters that can't be changed."""
    invalid_params = []
    for param_name, param in self.integration['parameters'].items():
      update_allowed = param.get('update_allowed', True)
      if not update_allowed and param_name in self.user_provided_params:
        invalid_params.append(param_name)

    if invalid_params:
      raise exceptions.ArgumentError(
          ('The following parameters: {} cannot be changed once the ' +
           'integration has been created')
          .format(self._RemoveEncoding(invalid_params))
      )

  def _ValidateProvidedParams(self):
    """Checks that the user provided parameters exist in the mapping."""
    invalid_params = []
    for param in self.user_provided_params:
      if param not in self.integration['parameters']:
        invalid_params.append(param)

    if invalid_params:
      raise exceptions.ArgumentError(
          'The following parameters: {} are not allowed'.format(
              self._RemoveEncoding(invalid_params))
      )

  def _ValidateRequiredParams(self):
    """Checks that required parameters are provided by the user."""
    missing_required_params = []
    for param_name, param in self.integration['parameters'].items():
      required = param.get('required', False)

      if required and param_name not in self.user_provided_params:
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

  def _SetupDefaultParams(self):
    """Ensures that default parameters have a value if not set."""
    for param_name, param in self.integration['parameters'].items():
      if ('default' in param and
          param_name not in self.user_provided_params):
        self.user_provided_params[param_name] = param['default']
