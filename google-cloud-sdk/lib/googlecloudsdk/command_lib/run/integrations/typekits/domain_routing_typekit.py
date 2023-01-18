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


class DomainRoutingTypeKit(base.TypeKit):
  """The domain routing integration typekit."""

  def GetDeployMessage(self, create=False):
    message = 'This might take up to 5 minutes.'

    if create:
      message += ' Manual DNS configuration will be required after completion.'
    return message

  def UpdateResourceConfig(self, parameters, resource_config):
    """Updates the resource config according to the parameters.

    Args:
      parameters: dict, parameters from the command
      resource_config: dict, the resource config object of the integration

    Returns:
      list of services referred in parameters.
    """
    domains = resource_config.setdefault('domains', [])
    services = []
    if 'set-mapping' in parameters:
      url, service = self._ParseMappingNotation(parameters.get('set-mapping'))
      services.append(service)
      service_ref = 'service/' + service
      domain, path = self._ParseDomainPath(url)
      domain_config = self._FindDomainConfig(domains, domain)
      if domain_config is None:
        domain_config = {'domain': domain}
        domains.append(domain_config)
      routes = domain_config.setdefault('routes', [])
      if path != '/*' and not routes:
        raise exceptions.ArgumentError('New domain must map to root path')
      # If path already set to other service, remove it.
      self._RemovePath(routes, path)
      for route in routes:
        if route.get('ref') == service_ref:
          route.setdefault('paths', []).append(path)
          break
      else:
        routes.append({'ref': service_ref, 'paths': [path]})
    elif 'remove-mapping' in parameters:
      url = parameters.get('remove-mapping')
      if ':' in url:
        raise exceptions.ArgumentError(
            'Service notion not allowed in remove-mapping')
      domain, path = self._ParseDomainPath(url)
      domain_config = self._FindDomainConfig(domains, domain)
      if domain_config is None:
        raise exceptions.ArgumentError(
            'Domain "{}" does not exist'.format(domain))
      routes = domain_config.get('routes')
      if path == '/*':
        # Removing root route
        if len(routes) > 1:
          # If the root route is not the only route, it can't be removed.
          raise exceptions.ArgumentError(
              ('Can not remove root route of domain "{}" '+
               'because there are other routes configured.').format(domain))
        else:
          # If it's the only route, delete the whole domain.
          domains.remove(domain_config)
      else:
        # Removing non-root route
        self._RemovePath(routes, path)
    elif 'remove-domain' in parameters:
      domain = parameters['remove-domain'].lower()
      domain_config = self._FindDomainConfig(domains, domain)
      if domain_config is None:
        raise exceptions.ArgumentError(
            'Domain "{}" does not exist'.format(domain))
      domains.remove(domain_config)

    if not domains:
      raise exceptions.ArgumentError(
          ('Can not remove the last domain. '+
           'Use "gcloud run integrations delete custom-domains" instead.'))

    return services

  def BindServiceToIntegration(self, integration_name, resource_config,
                               service_name, service_config, parameters):
    """Binds a service to the integration.

    Args:
      integration_name: str, name of the integration
      resource_config: dict, the resource config object of the integration
      service_name: str, name of the service
      service_config: dict, the resouce config object of the service
      parameters: dict, parameters from the command

    Raises:
      exceptions.ArgumentError: always raise this exception because binding
      service is not supported in DomainRouting integration.
    """
    raise exceptions.ArgumentError(
        '--add-service is not supported in custom-domains integration')

  def UnbindServiceFromIntegration(self, integration_name, resource_config,
                                   service_name, service_config, parameters):
    """Unbinds a service from the integration.

    Args:
      integration_name: str, name of the integration
      resource_config: dict, the resource config object of the integration
      service_name: str, name of the service
      service_config: dict, the resouce config object of the service
      parameters: dict, parameters from the command

    Raises:
      exceptions.ArgumentError: always raise this exception because unbinding
      service is not supported in DomainRouting integration.
    """
    raise exceptions.ArgumentError(
        '--remove-service is not supported in custom-domains integration')

  def NewIntegrationName(self, service, parameters, app_dict):
    """Returns a name for a new integration."""
    return self.singleton_name

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
    for domain_config in resource_config.get('domains', []):
      for route in domain_config.get('routes', []):
        ref = route.get('ref')
        if ref:
          services.append(ref.replace('service/', ''))

    return services

  def _FindDomainConfig(self, domains, domain):
    for domain_config in domains:
      if domain_config['domain'] == domain:
        return domain_config

  def _RemovePath(self, routes, path):
    for route in routes:
      paths = route.setdefault('paths', [])
      for route_path in paths:
        if route_path == path:
          paths.remove(route_path)
          break
      if not paths:
        routes.remove(route)

  def _ParseMappingNotation(self, mapping):
    mapping_parts = mapping.split(':')
    if len(mapping_parts) != 2:
      raise exceptions.ArgumentError(
          'Mapping "{}" is not valid. Missing service notation.'.format(
              mapping))
    url = mapping_parts[0]
    service = mapping_parts[1]
    return url, service

  def _ParseDomainPath(self, url):
    url_parts = url.split('/', 1)
    domain = url_parts[0]
    path = '/*'
    if len(url_parts) == 2:
      path = '/' + url_parts[1]
    return domain.lower(), path
