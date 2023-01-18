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
"""Helper functions for typekits."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.api_lib.run.integrations import types_utils
from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.command_lib.run.integrations.typekits import cloudsql_typekit
from googlecloudsdk.command_lib.run.integrations.typekits import domain_routing_typekit
from googlecloudsdk.command_lib.run.integrations.typekits import redis_typekit


def GetTypeKit(integration_type):
  """Returns a typekit for the given integration type.

  Args:
    integration_type: str, type of integration.

  Raises:
    ArgumentError: If the integration type is not supported.

  Returns:
    typekit.TypeKit, a typekit instance.
  """
  if integration_type == 'custom-domains':
    return domain_routing_typekit.DomainRoutingTypeKit(
        types_utils.GetTypeMetadata('custom-domains'))
  if integration_type == 'redis':
    return redis_typekit.RedisTypeKit(types_utils.GetTypeMetadata('redis'))
  if integration_type == 'cloudsql':
    return cloudsql_typekit.CloudSqlTypeKit(
        types_utils.GetTypeMetadata('cloudsql'))
  raise exceptions.ArgumentError(
      'Integration of type {} is not supported'.format(integration_type))


def GetTypeKitByResource(resource):
  """Returns a typekit for the given resource.

  Args:
    resource: dict, the resource object.

  Raises:
    ArgumentError: If the resource's type is not recognized.

  Returns:
    typekit.TypeKit, a typekit instance.
  """
  type_metadata = types_utils.GetIntegrationFromResource(resource)
  if type_metadata is None:
    raise exceptions.ArgumentError(
        'Integration of resource {} is not recognized'.format(resource))
  integration_type = type_metadata.integration_type
  return GetTypeKit(integration_type)
