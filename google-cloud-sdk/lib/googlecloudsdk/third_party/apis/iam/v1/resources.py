# -*- coding: utf-8 -*- #
# Copyright 2015 Google LLC. All Rights Reserved.
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
"""Resource definitions for cloud platform apis."""

import enum


BASE_URL = 'https://iam.googleapis.com/v1/'
DOCS_URL = 'https://cloud.google.com/iam/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  IAMPOLICIES = (
      'iamPolicies',
      'iamPolicies',
      {},
      [],
      True
  )
  LOCATIONS = (
      'locations',
      'locations/{locationsId}',
      {},
      ['locationsId'],
      True
  )
  LOCATIONS_WORKFORCEPOOLS = (
      'locations.workforcePools',
      '{+name}',
      {
          '':
              'locations/{locationsId}/workforcePools/{workforcePoolsId}',
      },
      ['name'],
      True
  )
  LOCATIONS_WORKFORCEPOOLS_OPERATIONS = (
      'locations.workforcePools.operations',
      '{+name}',
      {
          '':
              'locations/{locationsId}/workforcePools/{workforcePoolsId}/'
              'operations/{operationsId}',
      },
      ['name'],
      True
  )
  LOCATIONS_WORKFORCEPOOLS_PROVIDERS = (
      'locations.workforcePools.providers',
      '{+name}',
      {
          '':
              'locations/{locationsId}/workforcePools/{workforcePoolsId}/'
              'providers/{providersId}',
      },
      ['name'],
      True
  )
  LOCATIONS_WORKFORCEPOOLS_PROVIDERS_KEYS = (
      'locations.workforcePools.providers.keys',
      '{+name}',
      {
          '':
              'locations/{locationsId}/workforcePools/{workforcePoolsId}/'
              'providers/{providersId}/keys/{keysId}',
      },
      ['name'],
      True
  )
  LOCATIONS_WORKFORCEPOOLS_PROVIDERS_KEYS_OPERATIONS = (
      'locations.workforcePools.providers.keys.operations',
      '{+name}',
      {
          '':
              'locations/{locationsId}/workforcePools/{workforcePoolsId}/'
              'providers/{providersId}/keys/{keysId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  LOCATIONS_WORKFORCEPOOLS_PROVIDERS_OPERATIONS = (
      'locations.workforcePools.providers.operations',
      '{+name}',
      {
          '':
              'locations/{locationsId}/workforcePools/{workforcePoolsId}/'
              'providers/{providersId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  LOCATIONS_WORKFORCEPOOLS_SUBJECTS = (
      'locations.workforcePools.subjects',
      'locations/{locationsId}/workforcePools/{workforcePoolsId}/subjects/'
      '{subjectsId}',
      {},
      ['locationsId', 'workforcePoolsId', 'subjectsId'],
      True
  )
  LOCATIONS_WORKFORCEPOOLS_SUBJECTS_OPERATIONS = (
      'locations.workforcePools.subjects.operations',
      '{+name}',
      {
          '':
              'locations/{locationsId}/workforcePools/{workforcePoolsId}/'
              'subjects/{subjectsId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  ORGANIZATIONS = (
      'organizations',
      'organizations/{organizationsId}',
      {},
      ['organizationsId'],
      True
  )
  ORGANIZATIONS_ROLES = (
      'organizations.roles',
      '{+name}',
      {
          '':
              'organizations/{organizationsId}/roles/{rolesId}',
      },
      ['name'],
      True
  )
  PROJECTS = (
      'projects',
      'projects/{projectsId}',
      {},
      ['projectsId'],
      True
  )
  PROJECTS_LOCATIONS = (
      'projects.locations',
      'projects/{projectsId}/locations/{locationsId}',
      {},
      ['projectsId', 'locationsId'],
      True
  )
  PROJECTS_LOCATIONS_WORKLOADIDENTITYPOOLS = (
      'projects.locations.workloadIdentityPools',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'workloadIdentityPools/{workloadIdentityPoolsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_WORKLOADIDENTITYPOOLS_OPERATIONS = (
      'projects.locations.workloadIdentityPools.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'workloadIdentityPools/{workloadIdentityPoolsId}/operations/'
              '{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_WORKLOADIDENTITYPOOLS_PROVIDERS = (
      'projects.locations.workloadIdentityPools.providers',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'workloadIdentityPools/{workloadIdentityPoolsId}/providers/'
              '{providersId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_WORKLOADIDENTITYPOOLS_PROVIDERS_KEYS = (
      'projects.locations.workloadIdentityPools.providers.keys',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'workloadIdentityPools/{workloadIdentityPoolsId}/providers/'
              '{providersId}/keys/{keysId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_WORKLOADIDENTITYPOOLS_PROVIDERS_KEYS_OPERATIONS = (
      'projects.locations.workloadIdentityPools.providers.keys.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'workloadIdentityPools/{workloadIdentityPoolsId}/providers/'
              '{providersId}/keys/{keysId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_LOCATIONS_WORKLOADIDENTITYPOOLS_PROVIDERS_OPERATIONS = (
      'projects.locations.workloadIdentityPools.providers.operations',
      '{+name}',
      {
          '':
              'projects/{projectsId}/locations/{locationsId}/'
              'workloadIdentityPools/{workloadIdentityPoolsId}/providers/'
              '{providersId}/operations/{operationsId}',
      },
      ['name'],
      True
  )
  PROJECTS_ROLES = (
      'projects.roles',
      '{+name}',
      {
          '':
              'projects/{projectsId}/roles/{rolesId}',
      },
      ['name'],
      True
  )
  PROJECTS_SERVICEACCOUNTS = (
      'projects.serviceAccounts',
      '{+name}',
      {
          '':
              'projects/{projectsId}/serviceAccounts/{serviceAccountsId}',
      },
      ['name'],
      True
  )
  PROJECTS_SERVICEACCOUNTS_IDENTITYBINDINGS = (
      'projects.serviceAccounts.identityBindings',
      '{+name}',
      {
          '':
              'projects/{projectsId}/serviceAccounts/{serviceAccountsId}/'
              'identityBindings/{identityBindingsId}',
      },
      ['name'],
      True
  )
  PROJECTS_SERVICEACCOUNTS_KEYS = (
      'projects.serviceAccounts.keys',
      '{+name}',
      {
          '':
              'projects/{projectsId}/serviceAccounts/{serviceAccountsId}/'
              'keys/{keysId}',
      },
      ['name'],
      True
  )
  ROLES = (
      'roles',
      '{+name}',
      {
          '':
              'roles/{rolesId}',
      },
      ['name'],
      True
  )

  def __init__(self, collection_name, path, flat_paths, params,
               enable_uri_parsing):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
    self.enable_uri_parsing = enable_uri_parsing
