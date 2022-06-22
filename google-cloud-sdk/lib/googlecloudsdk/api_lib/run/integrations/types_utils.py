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

# TODO(b/233097220) Update this tuple to be only runapps once prod is setup
BASELINE_APIS = (
    'cloudbuild.googleapis.com',
    'iam.googleapis.com',
    'run.googleapis.com',
    'runapps.googleapis.com',
    'storage.googleapis.com',
)

_INTEGRATION_TYPES = frozenset([
    frozendict({
        'name':
            'custom-domain',
        'resource_name':
            'router',
        'description':
            'Configure a custom domain for Cloud Run services with Google Cloud '
            'Load Balancer.',
        'example_command':
            '$ gcloud run integrations create --service=[SERVICE] '
            '--type=custom-domain --parameters=domain=example.com',
        'parameters':
            frozendict({
                'domain': frozendict({
                    'description':
                        'The domain to configure for your Cloud Run service. This '
                        'must be a domain you can configure DNS for.',
                    'type': 'domain',
                    'required': True,
                    'update_allowed': False,
                }),
                'paths': frozendict({
                    'description':
                        'The paths at the domain for your Cloud Run service. '
                        'Defaults to "/" if not specified. (e.g. "/foo/*" for '
                        '"example.com/foo/*")',
                    'type': 'path_matcher',
                }),
                'dns-zone': frozendict({
                    'description':
                        'The ID of the Cloud DNS Zone already configured for this '
                        'domain. If not specified, manual DNS configuration is '
                        'expected.',
                    'type': 'string',
                    'hidden': True,
                }),
            }),
        'required_apis': frozenset({
            'compute.googleapis.com'
        }),
    }),
    frozendict({
        'name':
            'redis',
        'description':
            'Configure a Redis instance (Cloud Memorystore) and connect it '
            'to a Cloud Run Service.',
        'example_command':
            '$ gcloud run integrations create --service=[SERVICE] '
            '--type=redis --parameters=memory-size-gb=2',
        'parameters':
            frozendict({
                'memory-size-gb': frozendict({
                    'description': 'Memory capacity of the Redis instance.',
                    'type': 'int',
                    'default': 1,
                }),
                'tier': frozendict({
                    'description':
                        'The service tier of the instance. '
                        'Supported options include BASIC for standalone '
                        'instance and STANDARD_HA for highly available '
                        'primary/replica instances.',
                    'type': 'string',
                    'hidden': True,
                }),
                'version': frozendict({
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
        'required_apis': frozenset({
            'redis.googleapis.com',
            'vpcaccess.googleapis.com'
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
  return _INTEGRATION_TYPES


def GetIntegration(integration_type):
  """Returns values associated to an integration type.

  Args:
    integration_type: str

  Returns:
    frozendict() of values associated to the integration type.
    If the integration does not exist, then None is returned.
  """
  for integration in _INTEGRATION_TYPES:
    if integration['name'] == integration_type:
      return integration
  return None


def GetIntegrationType(resource_type):
  """Returns the integration type associated to the given resource type.

  Args:
    resource_type: string, the resource type.

  Returns:
    The integration type.
  """
  for t in _INTEGRATION_TYPES:
    if t.get('resource_name', None) == resource_type:
      return t['name']
  return resource_type


def CheckValidIntegrationType(integration_type):
  """Checks if IntegrationType is supported.

  Args:
    integration_type: str, integration type to validate.
  Rasies: ArgumentError
  """
  if integration_type not in [
      integration['name'] for integration in _INTEGRATION_TYPES
  ]:
    raise exceptions.ArgumentError(
        'Integration of type {} is not supported'.format(integration_type))
