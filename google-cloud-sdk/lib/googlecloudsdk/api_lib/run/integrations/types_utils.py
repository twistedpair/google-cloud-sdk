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

_INTEGRATION_TYPES = frozenset([frozendict({
    'name':
        'custom-domain',
    'resource_name':
        'router',
    'description':
        'Configure a custom domain for Cloud Run services with Google Cloud '
        'Load Balancer',
    'parameters': frozenset([
        frozendict({
            'name': 'domain',
            'description':
                'The domain to configure for your Cloud Run service. This '
                'must be a domain you can configure DNS for.',
            'type': 'domain',
            'required': True,
        }),
        frozendict({
            'name': 'paths',
            'description':
                'The paths at the domain for your Cloud Run service. '
                'Defaults to "/" if not specified. (e.g. "/foo/*" for '
                '"example.com/foo/*")',
            'type': 'path_matcher',
        }),
        frozendict({
            'name': 'dns-zone',
            'description':
                'The ID of the Cloud DNS Zone already configured for this '
                'domain. If not specified, manual DNS configuration is '
                'expected.',
            'type': 'string',
        }),
    ]),
})])


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

