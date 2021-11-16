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
import datetime

from apitools.base.py import encoding
from googlecloudsdk.api_lib.run.integrations import api_utils
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

_API_NAME = 'run_apps'

# Max wait time before timing out
_POLLING_TIMEOUT_MS = 180000
# Max wait time between poll retries before timing out
_RETRY_TIMEOUT_MS = 1000

_DEFAULT_APP_NAME = 'default'


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

  def ApplyAppConfig(self,
                     appname,
                     appconfig,
                     message=None,
                     match_type_names=None):
    """Apply the application config.

    Args:
      appname:  name of the application.
      appconfig: config of the application.
      message: the message to display when waiting for API call to finish.
        If not given, default messages will be used.
      match_type_names: array of type/name pairs used for create selector.

    Returns:
      The updated application.
    """
    app_ref = self.GetAppRef(appname)
    application = self.messages.Application(name=appname, config=appconfig)
    existing_app = api_utils.GetApplication(self._client, app_ref)
    if existing_app:
      operation = api_utils.PatchApplication(self._client, app_ref, application)
      if message is None:
        message = 'Updating Application [{}]'.format(appname)
    else:
      operation = api_utils.CreateApplication(self._client, app_ref,
                                              application)
      if message is None:
        message = 'Creating Application [{}]'.format(appname)
    api_utils.WaitForOperation(self._client, operation, message)
    deployment_name = self._GetDeploymentName(appname)
    if match_type_names is None:
      match_type_names = [{'type': '*', 'name': '*'}]
    deployment = self.messages.Deployment(
        name=deployment_name,
        createSelector={'matchTypeNames': match_type_names})
    deployment_ops = api_utils.CreateDeployment(self._client, app_ref,
                                                deployment)
    return api_utils.WaitForOperation(self._client, deployment_ops,
                                      'Deploying Changes')

  def _GetDeploymentName(self, appname):
    return '{}-{}'.format(
        appname,
        datetime.datetime.now().strftime('%Y%m%d%H%M'))

  def CreateIntegration(self, integration_type, parameters, service, name=None):
    """Create an integration.

    Args:
      integration_type:  type of the integration.
      parameters: parameter dictionary from args.
      service: the service to attach to the new integration.
      name: name of the integration, if empty, a defalt one will be generated.

    Returns:
      The updated application.
    """
    app_ref = self.GetAppRef(_DEFAULT_APP_NAME)
    application = api_utils.GetApplication(self._client, app_ref)
    if not application:
      application = self.messages.Application(
          name=_DEFAULT_APP_NAME, config={'resources': {}})

    app_dict = encoding.MessageToDict(application)
    app_dict.setdefault('config', {})
    app_dict['config'].setdefault('resources', {})
    if not name:
      name = self._GetIntegrationName(integration_type, service)

    if name in app_dict['config']['resources']:
      raise exceptions.ArgumentError(
          'Integration with name [{}] already exists.'.format(name))

    resource_config = self.GetResourceConfig(integration_type, parameters,
                                             service, {})
    app_dict['config']['resources'][name] = resource_config
    application = encoding.DictToMessage(app_dict, self.messages.Application)
    # TODO(b/201452306): pass in etag.
    match_type_names = [{'type': integration_type, 'name': name}]
    return self.ApplyAppConfig(
        appname=_DEFAULT_APP_NAME,
        appconfig=application.config,
        message='Creating Integration [{}]'.format(name),
        match_type_names=match_type_names)

  def GetResourceConfig(self, int_type, parameters, service, res_config):
    """Returns a new resource config according to the parameters.

    Args:
      int_type: type of the resource.
      parameters: parameter dictionary from args.
      service: the service to attach to the new integration.
      res_config: previous resource config. If given, changes will be made based
        on it.

    Returns:
      A new resource config
    """
    if res_config is not None and int_type in res_config:
      config = dict(res_config[int_type])
    else:
      config = {}

    if int_type == 'router':
      if 'dns-zone' in parameters:
        config['dns-zone'] = parameters['dns-zone']
      if 'domain' in parameters:
        config['domain'] = parameters['domain']
      if service:
        route = {'ref': 'service/{}'.format(service)}
        if 'paths' in parameters:
          route['paths'] = parameters['paths']
          if 'routes' not in config:
            config['routes'] = []
          config['routes'].append(route)
        else:
          config['default-route'] = route
      return {int_type: config}

    raise exceptions.ArgumentError(
        'Unsupported integration type [{}]'.format(int_type))

  def _GetIntegrationName(self, integration_type, service):
    # TODO(b/201452306):check for duplicate.
    return '{}-{}'.format(integration_type, service)

  def GetAppRef(self, name):
    """Returns the application resource object.

    Args:
      name:  name of the application.

    Returns:
      The application resource object
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
    return app_ref
