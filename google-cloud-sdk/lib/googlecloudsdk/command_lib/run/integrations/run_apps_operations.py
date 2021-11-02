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
"""Allows you to write surfaces in terms of logical RunApps operations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import contextlib

from googlecloudsdk.api_lib.run.integrations import api_utils
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

_API_NAME = 'run_apps'

# Max wait time before timing out
_POLLING_TIMEOUT_MS = 180000
# Max wait time between poll retries before timing out
_RETRY_TIMEOUT_MS = 1000


@contextlib.contextmanager
def Connect(conn_context):
  """Provide a RunAppsOperations instance to use.

  Arguments:
    conn_context: a context manager that yields a ConnectionInfo and manages a
      dynamic context.

  Yields:
    A RunAppsOperations instance.
  """
  # pylint: disable=protected-access
  client = apis.GetClientInstance(
      conn_context.api_name,
      conn_context.api_version)

  yield RunAppsOperations(client, conn_context.api_version, conn_context.region)


class RunAppsOperations(object):
  """Client used by Cloud Run Integrations to communicate with the API."""

  def __init__(self, client, api_version, region):
    """Inits RunAppsOperations with given API clients.

    Args:
      client: The API client for interacting with RunApps APIs.
      api_version: Version of resources & clients (v1alpha1, v1beta1)
      region: str, The region of the control plane.
    """

    self._client = client
    self._api_version = api_version
    self._region = region

  @property
  def client(self):
    return self._client

  @property
  def messages(self):
    return self._client.MESSAGES_MODULE

  def ApplyAppConfig(self, name, appconfig):
    """Apply the application config.

    Args:
      name:  name of the application.
      appconfig: config of the application.

    Returns:
      The updated application.
    """
    project = properties.VALUES.core.project.Get(required=True)
    location = self._region
    app_ref = resources.REGISTRY.Parse(
        name,
        params={
            'projectsId': project,
            'locationsId': location
        },
        collection='run_apps.projects.locations.applications')
    application = self.messages.Application(name=name, config=appconfig)
    existing_app = api_utils.GetApplication(self._client, app_ref)
    if existing_app:
      operation = api_utils.PatchApplication(self._client, app_ref, application)
      message = 'Updating Application [{}]'.format(name)
    else:
      operation = api_utils.CreateApplication(self._client, app_ref,
                                              application)
      message = 'Creating Application [{}]'.format(name)
    return api_utils.WaitForOperation(self._client, operation, message)
