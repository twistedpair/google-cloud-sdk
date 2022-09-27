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

from frozendict import frozendict
from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.core import properties

BASELINE_APIS = (
    'runapps.googleapis.com',
)

RESOURCE_TYPE = 'resource_type'
INTEGRATION_TYPE = 'integration_type'
REQUIRED_FIELD = 'required_field'
LATEST_DEPLOYMENT_FIELD = 'latestDeployment'

# TODO(b/237328242) Convert this to class
_INTEGRATION_TYPES = frozenset([
    frozendict({
        INTEGRATION_TYPE:
            'custom-domains',
        RESOURCE_TYPE:
            'router',
        'singleton':
            True,
        'singleton_name':
            'custom-domains',
        REQUIRED_FIELD:
            'domains',
        'visible': True,
        'description':
            'Configure custom domains for Cloud Run services with Google Cloud '
            'Load Balancer.',
        'example_command':
            """Create the integration to add the first domain mapping:
    $ gcloud {track} run integrations create --type=custom-domains --parameters='set-mapping=example.com/*:[SERVICE]'
  Update the integration to add subsequent mappings:
    $ gcloud {track} run integrations update custom-domains --parameters='set-mapping=anotherexample.com/*:[SERVICE]'
        """,
        'parameters':
            frozendict({
                'set-mapping':
                    frozendict({
                        'description':
                            'Set a route mapping from a path to a service. ' +
                            'Format: set-mapping=[DOMAIN]/[PATH]:[SERVICE]',
                        'required': True,
                        'type':
                            'domain-path-service',
                    }),
                'remove-mapping':
                    frozendict({
                        'description':
                            'Remove a route mapping. ' +
                            'Format: remove-mapping=[DOMAIN]/[PATH]',
                        'type':
                            'domain-path',
                        'create_allowed': False,
                    }),
                'remove-domain':
                    frozendict({
                        'description':
                            'To remove a domain an all of its route mappings.',
                        'type': 'domain',
                        'create_allowed': False,
                    }),
            }),
        'update_exclusive_groups':
            frozenset({
                frozendict({
                    'params':
                        frozenset(
                            {'set-mapping', 'remove-mapping', 'remove-domain'}),
                })
            }),
        'disable_service_flags': True,
        'required_apis':
            frozenset({'compute.googleapis.com'}),
    }),
    frozendict({
        INTEGRATION_TYPE:
            'redis',
        RESOURCE_TYPE:
            'redis',
        'description':
            'Configure a Redis instance (Cloud Memorystore) and connect it '
            'to a Cloud Run Service.',
        'example_command':
            '$ gcloud {track} run integrations create --service=[SERVICE] '
            '--type=redis --parameters=memory-size-gb=2',
        'backing_service': True,
        'visible': True,
        'parameters':
            frozendict({
                'memory-size-gb':
                    frozendict({
                        'description': 'Memory capacity of the Redis instance.',
                        'type': 'int',
                        'default': 1,
                    }),
                'tier':
                    frozendict({
                        'description':
                            'The service tier of the instance. '
                            'Supported options include BASIC for standalone '
                            'instance and STANDARD_HA for highly available '
                            'primary/replica instances.',
                        'type': 'string',
                        'hidden': True,
                    }),
                'version':
                    frozendict({
                        'description':
                            'The version of Redis software. If not '
                            'provided, latest supported version will be used. '
                            'Supported values include: REDIS_6_X, REDIS_5_0, '
                            'REDIS_4_0 and REDIS_3_2.',
                        'type': 'string',
                        'update_allowed': False,
                        'hidden': True,
                    }),
            }),
        'required_apis':
            frozenset({'redis.googleapis.com', 'vpcaccess.googleapis.com'}),
    }),
    frozendict({
        INTEGRATION_TYPE:
            'cloudsql',
        RESOURCE_TYPE:
            'cloudsql',
        'description':
            'Configure a CloudSQL database instance and connect it '
            'to a Cloud Run Service.',
        'visible': False,
        'example_command':
            '$ gcloud {track} run integrations create --service=[SERVICE] '
            '--type=cloudsql --parameters=version=MYSQL_8_0,tier=db-f1-micro',
        'backing_service': True,
        'parameters':
            frozendict({
                'tier':
                    frozendict({
                        'description':
                            'The service tier of the instance. '
                            'For example: db-f1-micro or db-g1-small.',
                        'type': 'string',
                        'update_allowed': False,
                        'required': True,
                    }),
                'version':
                    frozendict({
                        'description':
                            'The version of CloudSQL software. '
                            'For example: MYSQL_8_0, POSTGRES_14, '
                            'or SQLSERVER_2019_STANDARD. '
                            'See https://cloud.google.com/sql/docs/mysql/admin-api/rest/v1beta4/SqlDatabaseVersion for more details.',
                        'type': 'string',
                        'update_allowed': False,
                        'required': True,
                    }),
            }),
        'required_apis':
            frozenset({
                'sqladmin.googleapis.com',
                'cloudresourcemanager.googleapis.com',
                'secretmanager.googleapis.com'
            }),
    }),
])


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
      integration for integration in _INTEGRATION_TYPES
      if _IntegrationVisible(integration)
  ]


def GetIntegration(integration_type):
  """Returns values associated to an integration type.

  Args:
    integration_type: str

  Returns:
    frozendict() of values associated to the integration type.
      If the integration does not exist or is not visible to the user,
      then None is returned.
  """
  for integration in _INTEGRATION_TYPES:
    if (
        integration[INTEGRATION_TYPE] == integration_type
        and _IntegrationVisible(integration)
    ):
      return integration
  return None


def _IntegrationVisible(integration):
  """Returns whether or not the integration is visible.

  Args:
    integration: frozen_dict, each entry is defined in _INTEGRATION_TYPES

  Returns:
    True if the integration is set to visible, or if the property
      is set to true.  Otherwise it is False.
  """
  show_experimental_integrations = (
      properties.VALUES.runapps.experimental_integrations.GetBool()
  )
  return integration.get('visible', False) or show_experimental_integrations


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
  for integration_type in _INTEGRATION_TYPES:
    if not _IntegrationVisible(integration_type):
      continue
    if integration_type.get(RESOURCE_TYPE, None) == resource_type:
      must_have_field = integration_type.get(REQUIRED_FIELD, None)
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
  return type_def[INTEGRATION_TYPE]


def CheckValidIntegrationType(integration_type):
  """Checks if IntegrationType is supported.

  Args:
    integration_type: str, integration type to validate.
  Rasies: ArgumentError
  """
  if GetIntegration(integration_type) is None:
    raise exceptions.ArgumentError(
        'Integration of type {} is not supported'.format(integration_type))
