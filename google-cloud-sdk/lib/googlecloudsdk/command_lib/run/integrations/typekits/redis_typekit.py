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

from googlecloudsdk.api_lib.run.integrations import api_utils
from googlecloudsdk.command_lib.run.integrations.typekits import base


class RedisTypeKit(base.TypeKit):
  """The redis integration typekit."""

  def GetDeployMessage(self, create=False):
    return 'This might take up to 10 minutes.'

  def UpdateResourceConfig(self, parameters, resource_config):
    """Updates the resource config according to the parameters.

    Args:
      parameters: dict, parameters from the command
      resource_config: dict, the resource config object of the integration
    """
    instance = resource_config.setdefault('instance', {})
    supported_parameters = ['memory-size-gb', 'tier', 'version']

    for param in supported_parameters:
      if param in parameters:
        instance[param] = parameters[param]

  def GetCreateSelectors(self, integration_name):
    """Returns create selectors for given integration and service.

    Args:
      integration_name: str, name of integration.

    Returns:
      list of dict typed names.
    """
    selectors = super(RedisTypeKit, self).GetCreateSelectors(integration_name)
    selectors.append({'type': 'vpc', 'name': '*'})
    return selectors

  def GetDeleteSelectors(self, integration_name):
    """Selectors for deleting the integration.

    Args:
      integration_name: str, name of integration.

    Returns:
      list of dict typed names.
    """
    selectors = super(RedisTypeKit, self).GetDeleteSelectors(integration_name)
    selectors.append({'type': 'vpc', 'name': '*'})
    return selectors

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
    rtypes = super(RedisTypeKit,
                   self).GetCreateComponentTypes(selectors,
                                                 app_dict)
    rtypes.add('vpc')
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
    rtypes = super(RedisTypeKit,
                   self).GetCreateComponentTypes(selectors,
                                                 app_dict)
    num_redis = self._NumberOfRedisInApp(app_dict)
    if num_redis == 1:
      rtypes.add('vpc')
    elif 'vpc' in rtypes:
      rtypes.remove('vpc')
    return rtypes

  def _NumberOfRedisInApp(self, app_dict):
    """Returns a cound of redis resources in the application.

    Args:
      app_dict: The application resource as dictionary.

    Returns:
      count of redis resources.
    """
    resources_map = app_dict[api_utils.APP_DICT_CONFIG_KEY][
        api_utils.APP_CONFIG_DICT_RESOURCES_KEY]
    count = 0
    for resource in resources_map.values():
      if 'redis' in resource:
        count += 1
    return count
