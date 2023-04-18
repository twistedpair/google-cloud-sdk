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
"""This typekit represents the Firebase Hosting integration.

The base functions from the TypeKit class can be overridden here if more
functionality is needed.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.command_lib.run.integrations.typekits import base


class FirebaseHostingTypeKit(base.TypeKit):
  """The Firebase Hosting integration typekit."""

  def GetDeployMessage(self, create=False):
    return 'This might take up to 5 minutes.'

  def UpdateResourceConfig(self, parameters, resource_config):
    """Updates the existing resource config with the parameters provided.

    Args:
      parameters: dict, user provided parameters from the command.
      resource_config: dict, resource config associated with the integration.
    """
    config = resource_config.setdefault('config', {})
    if 'site-id' in parameters:
      config['site-id'] = parameters['site-id']

  def BindServiceToIntegration(
      self,
      integration_name,
      resource_config,
      service_name,
      service_config,
      parameters,
  ):
    """Binds a service to the integration.

    Args:
      integration_name: str, name of the integration
      resource_config: dict, the resource config object of the integration
      service_name: str, name of the service
      service_config: dict, the resource config object of the service
      parameters: dict, parameters from the command

    Raises:
      exceptions.ArgumentError: raises this execption if a service is already
      bound by the FirebaseHosting integration.
    """
    services = self._GetAllServices(resource_config)
    if services:
      raise exceptions.ArgumentError(
          'cannot modify the bound service for firebase-hosting integration'
      )
    resources = resource_config.setdefault('resources', [])
    resources.append({'ref': 'service/' + service_name})

  def UnbindServiceFromIntegration(
      self,
      integration_name,
      resource_config,
      service_name,
      service_config,
      parameters,
  ):
    """Unbinds a service from the integration.

    Args:
      integration_name: str, name of the integration
      resource_config: dict, the resource config object of the integration
      service_name: str, name of the service
      service_config: dict, the resource config object of the service
      parameters: dict, parameters from the command

    Raises:
      exceptions.ArgumentError: always raise this exception because unbinding
      service is not supported in FirebaseHosting integration.
    """
    raise exceptions.ArgumentError(
        '--remove-service is not supported in firebase-hosting integration'
    )

  def GetRefServices(self, name, resource_config, all_resources):
    """Returns list of cloud run service that is binded to this resource.

    Args:
      name: str, name of the resource.
      resource_config: dict, the resource config object of the integration
      all_resources: dict, all the resources in the application.

    Returns:
      list cloud run service names
    """
    return self._GetAllServices(resource_config)

  def _GetAllServices(self, resource_config):
    services = []
    for resource in resource_config.get('resources', []):
      ref = resource.get('ref')
      if ref:
        services.append(ref.replace('service/', ''))

    return services
