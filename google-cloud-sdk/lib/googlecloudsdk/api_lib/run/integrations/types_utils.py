# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Functionality related to Cloud Run Integration API clients."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import yaml

BASELINE_APIS = ('runapps.googleapis.com',)
LATEST_DEPLOYMENT_FIELD = 'latestDeployment'
_TYPE_METADATA = None


class UpdateExclusiveGroup:
  def __init__(self, params, required=False):
    self.params = params
    self.required = required


class ServiceType:
  """Types of services supported by runapps."""
  BACKING = 'backing'
  INGRESS = 'ingress'


def _ServiceTypeFromStr(s):
  """Converts string into service type."""
  types = {
      'backing': ServiceType.BACKING,
      'ingress': ServiceType.INGRESS,
  }

  service_type = types.get(s.lower(), None)
  if service_type is None:
    raise exceptions.ArgumentError('Service type {} is not supported'.format(s))

  return service_type


class Parameters:
  """Each integration has a list of parameters that are stored in this class.

  Types denoted here for when Python2 is no longer supported and we can have
  the types defined directly in code.
    name: str
    description: str
    data_type: str
    update_allowed: typing.Optional[bool] = True
    required: typing.Optional[bool] = False
    hidden: typing.Optional[bool] = False
    create_allowed: typing.Optional[bool] = True
    default: typing.Optional[any] = None

  Attributes:
    name: Name of the parameter.
    description: Explanation of the parameter that is visible to the
      customer.
    data_type: Denotes what values are acceptable for the parameter.
    update_allowed: If false, the param can not be provided in an update
      command.
    required:  If true, the param must be provided on a create command.
    hidden: If true, the param will not show up in error messages, but can
      be provided by the user.
    create_allowed: If false, the param cannot be provided on a create
      command.
    default: The value provided for the param if the user has not provided one.
  """

  def __init__(self, name, description, data_type, update_allowed=True,
               required=False, hidden=False, create_allowed=True, default=None):
    self.name = name
    self.description = description
    self.data_type = data_type
    self.update_allowed = update_allowed
    self.required = required
    self.hidden = hidden
    self.create_allowed = create_allowed
    self.default = default


class TypeMetadata:
  """Metadata for each integration type supported by Runapps.

  Types denoted here for when Python2 is no longer supported and we can have
  the types defined directly in code.
    integration_type: str
    resource_type: str
    description: str
    example_command: str
    service_type: ServiceType
    required_apis: set[str]
    parameters: list[Parameters]
    update_exclusive_groups: typing.Optional[list[UpdateExclusiveGroup]] = None
    disable_service_flags: typing.Optional[bool] = False
    singleton_name: typing.Optional[str] = None
    required_field: typing.Optional[str] = None
    visible: typing.Optional[bool] = False

  Attributes:
    integration_type: Name of integration type.
    resource_type: Name of resource type.
    description: Description of the integration that is visible to the user.
    example_command: Example commands that will be provided to the user.
    required_field: Field that must exist in the resource config.
    service_type: Denotes what type of service the integration is.
    parameters: What users can provide for the given integration.
    update_exclusive_groups: A list of groups, where each group contains
      parameters that cannot be provided at the same time.  Only one in the set
      can be provided by the user for each command.
    disable_service_flags: If true, the --service flag cannot be provided.
    singleton_name: If this field is provided, then the integration can only be
      a singleton.  The name is used as an identifier in the resource config.
    required_apis: APIs required for the integration to work.  The user will be
      prompted to enable these APIs if they are not already enabled.
    visible: If true, then the integration is useable by anyone without any
      special configuration.
  """

  def __init__(self, integration_type, resource_type, description,
               example_command, service_type, required_apis, parameters,
               update_exclusive_groups=None, disable_service_flags=False,
               singleton_name=None, required_field=None, visible=False):
    self.integration_type = integration_type
    self.resource_type = resource_type
    self.description = description
    self.example_command = example_command
    self.service_type = _ServiceTypeFromStr(service_type)
    self.required_apis = required_apis
    self.parameters = [Parameters(**param) for param in parameters]
    self.disable_service_flags = disable_service_flags
    self.singleton_name = singleton_name
    self.required_field = required_field
    self.visible = visible

    if update_exclusive_groups is None:
      update_exclusive_groups = []

    self.update_exclusive_groups = [
        UpdateExclusiveGroup(**group) for group in update_exclusive_groups]


def _GetTypeMetadata():
  """Returns metadata for each integration type.

  This loads the metadata from a yaml file at most once and will return the
  same data stored in memory upon future calls.

  Returns:
    array, the type metadata list
  """
  global _TYPE_METADATA
  if not _TYPE_METADATA:
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, 'metadata.yaml')
    metadata = yaml.load_path(filename)
    _TYPE_METADATA = [
        TypeMetadata(**integ) for integ in metadata['integrations']
    ]

  return _TYPE_METADATA


def IntegrationTypes(client):
  """Gets the type definitions for Cloud Run Integrations.

  Currently it's just returning some builtin defnitions because the API is
  not implemented yet.

  Args:
    client: GAPIC API client, the api client to use.

  Returns:
    array of integration type.
  """
  del client

  return [
      integration for integration in _GetTypeMetadata()
      if _IntegrationVisible(integration)
  ]


def GetTypeMetadata(integration_type):
  """Returns metadata associated to an integration type.

  Args:
    integration_type: str

  Returns:
    If the integration does not exist or is not visible to the user,
    then None is returned.
  """
  for integration in _GetTypeMetadata():
    if (integration.integration_type == integration_type and
        _IntegrationVisible(integration)):
      return integration
  return None


def _IntegrationVisible(integration):
  """Returns whether or not the integration is visible.

  Args:
    integration: Each entry is defined in _INTEGRATION_TYPES

  Returns:
    True if the integration is set to visible, or if the property
      is set to true.  Otherwise it is False.
  """
  show_experimental_integrations = (
      properties.VALUES.runapps.experimental_integrations.GetBool())
  return integration.visible or show_experimental_integrations


def GetResourceTypeFromConfig(resource_config):
  """Gets the resource type.

  The input is converted from proto with potentially two fields.
  One of them is the latestDeployment field (may not be present) and the other
  is a "oneof" property.  Thus the dictionary is expected to have one or
  two keys and we only want the one with the "oneof" property.

  Args:
    resource_config: dict, the resource configuration.

  Returns:
    str, the integration type.
  """
  if resource_config is None:
    raise exceptions.ConfigurationError('resource config is none.')

  keys = [
      key for key in resource_config.keys() if key != LATEST_DEPLOYMENT_FIELD
  ]
  if len(keys) != 1:
    # We should never gets here, because having more than one key in a
    # oneof field in not allowed in proto.
    raise exceptions.ConfigurationError(
        'resource config is invalid: {}.'.format(resource_config))
  return keys[0]


def GetIntegrationFromResource(resource_config):
  """Returns the integration type definition associated to the given resource.

  Args:
    resource_config: dict, the resource configuration.

  Returns:
    The integration type definition.
  """
  resource_type = GetResourceTypeFromConfig(resource_config)
  config = resource_config[resource_type]
  match = None
  for integration_type in _GetTypeMetadata():
    if not _IntegrationVisible(integration_type):
      continue
    if integration_type.resource_type == resource_type:
      must_have_field = integration_type.required_field
      if must_have_field:
        if config.get(must_have_field, None):
          return integration_type
      else:
        match = integration_type
  return match


def GetIntegrationType(resource_config):
  """Returns the integration type associated to the given resource type.

  Args:
    resource_config: dict, the resource configuration.

  Returns:
    The integration type.
  """
  type_def = GetIntegrationFromResource(resource_config)
  if type_def is None:
    return GetResourceTypeFromConfig(resource_config)
  return type_def.integration_type


def CheckValidIntegrationType(integration_type):
  """Checks if IntegrationType is supported.

  Args:
    integration_type: str, integration type to validate.
  Rasies: ArgumentError
  """
  if GetTypeMetadata(integration_type) is None:
    raise exceptions.ArgumentError(
        'Integration of type {} is not supported'.format(integration_type))
