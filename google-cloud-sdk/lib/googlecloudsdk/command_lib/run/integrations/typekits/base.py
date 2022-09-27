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

import abc
import re


class TypeKit(object):
  """An abstract class that represents a typekit."""

  def __init__(self, type_metadata):
    self._type_metadata = type_metadata

  @property
  def integration_type(self):
    return self._type_metadata.get('integration_type')

  @property
  def resource_type(self):
    return self._type_metadata.get('resource_type')

  @property
  def is_singleton(self):
    return self._type_metadata.get('singleton', False)

  @property
  def singleton_name(self):
    return self._type_metadata.get('singleton_name')

  @property
  def is_backing_service(self):
    return self._type_metadata.get('backing_service', False)

  @property
  def is_ingress_service(self):
    return not self._type_metadata.get('backing_service', False)

  @abc.abstractmethod
  def GetAllReferences(self, resource_config):
    return []

  @abc.abstractmethod
  def UpdateResourceConfig(self, parameters, resource_config):
    """Updates config according to the parameters.

    Each TypeKit should override this method to update the resource config
    specific to the need of the typekit.

    Args:
      parameters: dict, parameters from the command
      resource_config: dict, the resource config object of the integration
    """

  def BindServiceToIntegration(self, integration_name, resource_config,
                               service_name, service_config, parameters):
    """Binds a service to the integration.

    Args:
      integration_name: str, name of the integration
      resource_config: dict, the resource config object of the integration
      service_name: str, name of the service
      service_config: dict, the resouce config object of the service
      parameters: dict, parameters from the command
    """
    del resource_config, service_name, parameters  # Not used here.
    ref_to_add = '{}/{}'.format(self.resource_type, integration_name)
    # Check if ref already exists.
    refs = set(ref['ref'] for ref in service_config.get('resources', []))
    if ref_to_add not in refs:
      service_config.setdefault('resources', []).append(
          {'ref': ref_to_add})

  def UnbindServiceFromIntegration(self, integration_name, resource_config,
                                   service_name, service_config, parameters):
    """Unbinds a service from the integration.

    Args:
      integration_name: str, name of the integration
      resource_config: dict, the resource config object of the integration
      service_name: str, name of the service
      service_config: dict, the resouce config object of the service
      parameters: dict, parameters from the command
    """
    del resource_config, service_name, parameters  # Not used here.
    ref_to_remove = '{}/{}'.format(self.resource_type, integration_name)
    service_config['resources'] = [
        x for x in service_config.get('resources', [])
        if x['ref'] != ref_to_remove
    ]

  def NewIntegrationName(self, service, parameters, resources_map):
    """Returns a name for a new integration.

    Args:
      service: str, name of the service
      parameters: dict, parameters from the command
      resources_map: the map of all resources in the application

    Returns:
      str, a new name for the integration.
    """
    del service, parameters  # Not used in here.
    name = '{}-{}'.format(self.integration_type, 1)
    while name in resources_map:
      # If name already taken, tries adding an integer suffix to it.
      # If suffixed name also exists, tries increasing the number until finding
      # an available one.
      count = 1
      match = re.search(r'(.+)-(\d+)$', name)
      if match:
        name = match.group(1)
        count = int(match.group(2)) + 1
      name = '{}-{}'.format(name, count)
    return name

  def GetCreateSelectors(self,
                         integration_name,
                         add_service_name,
                         remove_service_name=None):
    """Returns create selectors for given integration and service.

    Args:
      integration_name: str, name of integration.
      add_service_name: str, name of the service being added.
      remove_service_name: str, name of the service being removed.

    Returns:
      list of dict typed names.
    """
    service_name = add_service_name or remove_service_name
    selectors = [{'type': self.resource_type, 'name': integration_name}]

    if service_name:
      selectors.append({'type': 'service', 'name': service_name})

    return selectors

  def GetDeleteSelectors(self, integration_name):
    """Returns selectors for deleting the integration.

    Args:
      integration_name: str, name of integration.

    Returns:
      list of dict typed names.
    """
    return [{'type': self.resource_type, 'name': integration_name}]

  def GetRefServices(self, name, resource_config, all_resources):
    """Returns list of cloud run service that is binded to this resource.

    Args:
      name: str, name of the resource.
      resource_config: dict, the resource config object of the integration.
      all_resources: dict, all the resources in the application.

    Returns:
      list cloud run service names
    """
    del resource_config  # Not used here.
    services = []
    if self.is_backing_service:
      for resource_name, resource in all_resources.items():
        ref_name = '{}/{}'.format(self.resource_type, name)
        if resource.get('service', {}).get('resources'):
          if any([
              ref['ref'] == ref_name
              for ref in resource['service']['resources']
          ]):
            services.append(resource_name)
    return services

  def GetCreateComponentTypes(self, selectors, app_dict):
    """Returns a list of component types included in a create/update deployment.

    Args:
      selectors: list of dict of type names (string) that will be deployed.
      app_dict: The application resource as dictionary.

    Returns:
      set of component types as strings. The component types can also include
      hidden resource types that should be called out as part of the deployment
      progress output.
    """
    del app_dict  # Unused.
    if not selectors:
      return {}
    rtypes = set()
    for type_name in selectors:
      rtypes.add(type_name['type'])
    return rtypes

  def GetDeleteComponentTypes(self, selectors, app_dict):
    """Returns a list of component types included in a delete deployment.

    Args:
      selectors: list of dict of type names (string) that will be deployed.
      app_dict: The application resource as dictionary.

    Returns:
      set of component types as strings. The component types can also include
      hidden resource types that should be called out as part of the deployment
      progress output.
    """
    del app_dict  # Unused.
    if not selectors:
      return {}
    rtypes = set()
    for type_name in selectors:
      rtypes.add(type_name['type'])
    return rtypes
