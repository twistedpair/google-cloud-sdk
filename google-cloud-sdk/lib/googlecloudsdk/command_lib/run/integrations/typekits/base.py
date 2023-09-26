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
from typing import List, Optional

from googlecloudsdk.api_lib.run.integrations import types_utils
from googlecloudsdk.generated_clients.apis.runapps.v1alpha1 import runapps_v1alpha1_messages


class TypeKit(object):
  """An abstract class that represents a typekit."""

  def __init__(self, type_metadata: types_utils.TypeMetadata):
    self._type_metadata = type_metadata

  @property
  def integration_type(self):
    return self._type_metadata.integration_type

  @property
  def resource_type(self):
    return self._type_metadata.resource_type

  @property
  def is_singleton(self):
    return self._type_metadata.singleton_name is not None

  @property
  def singleton_name(self):
    return self._type_metadata.singleton_name

  @property
  def is_backing_service(self):
    return self._type_metadata.service_type == types_utils.ServiceType.BACKING

  @property
  def is_ingress_service(self):
    return self._type_metadata.service_type == types_utils.ServiceType.INGRESS

  @abc.abstractmethod
  def GetAllReferences(self, resource_config):
    return []

  @abc.abstractmethod
  def GetDeployMessage(self, create: bool = False) -> str:
    """Message that is shown to the user upon starting the deployment.

    Each TypeKit should override this method to at least tell the user how
    long the deployment is expected to take.

    Args:
      create: denotes if the command was a create deployment.

    Returns:
      The message displayed to the user.
    """

  @abc.abstractmethod
  def UpdateResourceConfig(self, parameters, resource_config):
    """Updates config according to the parameters.

    Each TypeKit should override this method to update the resource config
    specific to the need of the typekit.

    Args:
      parameters: dict, parameters from the command
      resource_config: dict, the resource config object of the integration
    """

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
      service_config: dict, the resouce config object of the service
      parameters: dict, parameters from the command
    """
    del resource_config, service_name, parameters  # Not used here.
    ref_to_add = '{}/{}'.format(self.resource_type, integration_name)
    # Check if ref already exists.
    refs = set(ref['ref'] for ref in service_config.get('resources', []))
    if ref_to_add not in refs:
      service_config.setdefault('resources', []).append({'ref': ref_to_add})

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
      service_config: dict, the resouce config object of the service
      parameters: dict, parameters from the command
    """
    del resource_config, service_name, parameters  # Not used here.
    ref_to_remove = '{}/{}'.format(self.resource_type, integration_name)
    service_config['resources'] = [
        x
        for x in service_config.get('resources', [])
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

  def GetCreateSelectors(self, integration_name):
    """Returns create selectors for given integration and service.

    Args:
      integration_name: str, name of integration.

    Returns:
      list of dict typed names.
    """

    return [{'type': self.resource_type, 'name': integration_name}]

  def GetDeleteSelectors(self, integration_name):
    """Returns selectors for deleting the integration.

    Args:
      integration_name: str, name of integration.

    Returns:
      list of dict typed names.
    """
    return [{'type': self.resource_type, 'name': integration_name}]

  # TODO(b/298063267): clean up after replacing all with GetBindedWorkload
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
          if any(
              [
                  ref['ref'] == ref_name
                  for ref in resource['service']['resources']
              ]
          ):
            services.append(resource_name)
    return services

  def GetBindedWorkloads(
      self,
      resource: runapps_v1alpha1_messages.Resource,
      all_resources: List[runapps_v1alpha1_messages.Resource],
      workload_type: str = 'service',
  ) -> List[runapps_v1alpha1_messages.ResourceID]:
    """Returns list of workloads that are associated to this resource.

    If the resource is a backing service, then it returns a list of workloads
    binding to the resource. If the resource is an ingress service, then all
    of the workloads it is binding to.

    Args:
      resource: the resource object of the integration.
      all_resources: all the resources in the application.
      workload_type: type of the workload to search for.

    Returns:
      list ResourceID of the binded workloads.
    """
    if self.is_backing_service:
      filtered_workloads = [
          res for res in all_resources if res.id.type == workload_type
      ]
      return [
          workload.id.name
          for workload in filtered_workloads
          if self._FindBinding(workload, resource.id.type, resource.id.name)
      ]
    return [
        res_id.name
        for res_id in self._FindBindingRecursive(resource, workload_type)
    ]

  def _FindBindingRecursive(
      self,
      resource: runapps_v1alpha1_messages.Resource,
      target_type: Optional[str] = None,
      target_name: Optional[str] = None,
  ) -> List[runapps_v1alpha1_messages.ResourceID]:
    """Find bindings from the given resource and its subresource.

    Args:
      resource: the resource to look for bindings from.
      target_type: the type of bindings to match. If empty, will match all
        types.
      target_name: the name of the bindings to match. If empty, will match all
        names.

    Returns:
      list of ResourceID of the bindings.
    """
    svcs = self._FindBinding(resource, target_type, target_name)
    if resource.subresources:
      for subresource in resource.subresources:
        svcs.extend(
            self._FindBindingRecursive(subresource, target_type, target_name)
        )
    return svcs

  def _FindBinding(
      self,
      resource: runapps_v1alpha1_messages.Resource,
      target_type: Optional[str],
      target_name: Optional[str],
  ) -> List[runapps_v1alpha1_messages.ResourceID]:
    """Returns list of bindings that match the target_type and target_name.

    Args:
      resource: the resource to look for bindings from.
      target_type: the type of bindings to match. If empty, will match all
        types.
      target_name: the name of the bindings to match. If empty, will match all
        names.

    Returns:
      list of ResourceID of the bindings.
    """
    result = []
    for binding in resource.bindings:
      if (not target_name or binding.targetRef.id.name == target_name) and (
          not target_type or binding.targetRef.id.type == target_type
      ):
        result.append(binding.targetRef.id)
    return result

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
