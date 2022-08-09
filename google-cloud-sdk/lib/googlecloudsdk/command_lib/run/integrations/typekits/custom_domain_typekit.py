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
"""Base ResourceBuilder for Cloud Run Integrations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.command_lib.run.integrations.typekits import base


class CustomDomainTypeKit(base.TypeKit):
  """The custom domain integration typekit."""

  def UpdateResourceConfig(self, parameters, resource_config):
    """Updates the resource config according to the parameters.

    Args:
      parameters: dict, parameters from the command
      resource_config: dict, the resource config object of the integration
    """
    if 'dns-zone' in parameters:
      resource_config['dns-zone'] = parameters['dns-zone']
    if 'domain' in parameters:
      resource_config['domain'] = parameters['domain']

  def BindServiceToIntegration(self, integration_name, resource_config,
                               service_name, service_config, parameters):
    """Binds a service to the custom domain integration.

    If paths is given, it will be added to the 'routes' array.
    If paths is not given, it will be set as default route, replacing existing
    value.

    Args:
      integration_name: str, name of the integration
      resource_config: dict, the resource config object of the integration
      service_name: str, name of the service
      service_config: dict, the resouce config object of the service
      parameters: dict, parameters from the command
    """
    route = {'ref': 'service/{}'.format(service_name)}
    if 'paths' in parameters:
      route['paths'] = parameters['paths']
      resource_config.setdefault('routes', []).append(route)
    else:
      resource_config['default-route'] = route

  def UnbindServiceFromIntegration(self, integration_name, resource_config,
                                   service_name, service_config, parameters):
    """Unbinds a service from the custom domain integration.

    It's not allowed to unbind service configured as the default-route.


    Args:
      integration_name: str, name of the integration
      resource_config: dict, the resource config object of the integration
      service_name: str, name of the service
      service_config: dict, the resouce config object of the service
      parameters: dict, parameters from the command

    Raises:
      exceptions.ArgumentError: if the service to unbind is on default route.
    """
    ref = 'service/{}'.format(service_name)
    if resource_config.get('default-route', {}).get('ref') == ref:
      raise exceptions.ArgumentError(
          'Cannot remove service associated with the default path (/*)')

    resource_config['routes'] = [
        x for x in resource_config.get('routes', []) if x['ref'] != ref
    ]

  def NewIntegrationName(self, service, parameters, resources_map):
    """Returns a name for a new custom domain integration.

    The name will be domain-[domain with . replaced by -]. For example,
    test.example.com will get a name domain-test-example-com.
    Also it won't generate a different name if it's already exists. Thus
    if creating multiple integrations with the same domain, it will failed
    from name conflict. It's the desired behavior.

    Args:
      service: str, name of the service
      parameters: dict, parameters from the command
      resources_map: the map of all resources in the application

    Raises:
      exceptions.ArgumentError: if 'domain' does not exist in parameters.

    Returns:
      str, a new name for the integration.
    """
    del resources_map  # Not used here.
    domain = parameters.get('domain')
    if not domain:
      raise exceptions.ArgumentError('domain is required in "PARAMETERS" '
                                     'for integration type "custom-domain"')
    return 'domain-{}'.format(domain.replace('.', '-'))

  def GetCreateSelectors(self,
                         integration_name,
                         add_service_name,
                         remove_service_name=None):
    """Returns create selectors for creating or updating custom domain.

    It will add 'add_service_name' to the selectors. But it won't add
    'add_service_name' to the selectors.

    Args:
      integration_name: str, name of integration.
      add_service_name: str, name of the service being added.
      remove_service_name: str, name of the service being removed.

    Returns:
      list of dict typed names.
    """
    selectors = [{'type': self.resource_type, 'name': integration_name}]

    # Router should not add remove service to selector.
    if add_service_name:
      selectors.append({'type': 'service', 'name': add_service_name})

    return selectors

  def GetRefServices(self, name, resource_config, all_resources):
    """Returns list of cloud run service that is binded to this resource.

    Args:
      name: str, name of the resource.
      resource_config: dict, config of the resource.
      all_resources: dict, all the resources in the application.

    Returns:
      list cloud run service names
    """
    services = []
    if resource_config.get('default-route', {}).get('ref'):
      services.append(resource_config['default-route']['ref'].replace(
          'service/', ''))

    if resource_config.get('routes'):
      for route in resource_config['routes']:
        if route.get('ref'):
          services.append(route['ref'].replace('service/', ''))

    return services
