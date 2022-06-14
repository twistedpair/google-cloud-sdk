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
import json
import re

from apitools.base.py import encoding
from apitools.base.py import exceptions as api_exceptions
from googlecloudsdk.api_lib.run.integrations import api_utils
from googlecloudsdk.api_lib.run.integrations import types_utils
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.run import connection_context
from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.command_lib.run import flags as run_flags
from googlecloudsdk.command_lib.run import serverless_operations
from googlecloudsdk.command_lib.run.integrations import flags
from googlecloudsdk.command_lib.run.integrations import messages_util
from googlecloudsdk.command_lib.run.integrations import stages
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

# Max wait time before timing out
_POLLING_TIMEOUT_MS = 180000
# Max wait time between poll retries before timing out
_RETRY_TIMEOUT_MS = 1000

_CONFIG_KEY = 'config'
_RESOURCES_KEY = 'resources'

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


def _HandleQueueingException(err):
  """Reraises the error if with better message if it's a queueing error.

  Args:
    err: the exception to be handled.

  Raises:
    exceptions.IntegrationsOperationError: this is a queueing error.
  """
  content = json.loads(err.content)
  msg = content['error']['message']
  code = content['error']['code']
  if msg == 'unable to queue the operation' and code == 409:
    raise exceptions.IntegrationsOperationError(
        'An integration is currently being configured.  Please wait ' +
        'until the current process is complete and try again')
  raise err


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
                     tracker,
                     appname,
                     appconfig,
                     integration_name=None,
                     deploy_message=None,
                     match_type_names=None,
                     intermediate_step=False,
                     etag=None):
    """Applies the application config.

    Args:
      tracker: StagedProgressTracker, to report on the progress.
      appname:  name of the application.
      appconfig: config of the application.
      integration_name: name of the integration that's being updated.
      deploy_message: message to display when deployment in progress.
      match_type_names: array of type/name pairs used for create selector.
      intermediate_step: bool of whether this is an intermediate step.
      etag: the etag of the application if it's an incremental patch.
    """
    tracker.StartStage(stages.UPDATE_APPLICATION)
    if integration_name:
      tracker.UpdateStage(
          stages.UPDATE_APPLICATION,
          'You can check the status at any time by running '
          '`gcloud alpha run integrations describe {}`'.format(
              integration_name))
    try:
      self._UpdateApplication(appname, appconfig, etag)
    except api_exceptions.HttpConflictError as err:
      _HandleQueueingException(err)
    except exceptions.IntegrationsOperationError as err:
      tracker.FailStage(stages.UPDATE_APPLICATION, err)
    else:
      tracker.CompleteStage(stages.UPDATE_APPLICATION)

    if match_type_names is None:
      match_type_names = [{'type': '*', 'name': '*'}]
    create_selector = {'matchTypeNames': match_type_names}

    if not intermediate_step:
      tracker.UpdateHeaderMessage(
          'Deployment started. This process will continue even if '
          'your terminal session is interrupted.')
    tracker.StartStage(stages.CREATE_DEPLOYMENT)
    if deploy_message:
      tracker.UpdateStage(stages.CREATE_DEPLOYMENT, deploy_message)
    try:
      self._CreateDeployment(appname, create_selector=create_selector)
    except api_exceptions.HttpConflictError as err:
      _HandleQueueingException(err)
    except exceptions.IntegrationsOperationError as err:
      tracker.FailStage(stages.CREATE_DEPLOYMENT, err)
    else:
      tracker.UpdateStage(stages.CREATE_DEPLOYMENT, '')
      tracker.CompleteStage(stages.CREATE_DEPLOYMENT)

    tracker.UpdateHeaderMessage('Done.')

  def _UpdateApplication(self, appname, appconfig, etag):
    """Update Application config, waits for operation to finish.

    Args:
      appname:  name of the application.
      appconfig: config of the application.
      etag: the etag of the application if it's an incremental patch.
    """
    app_ref = self.GetAppRef(appname)
    application = self.messages.Application(
        name=appname, config=appconfig, etag=etag)
    is_patch = etag or api_utils.GetApplication(self._client, app_ref)
    if is_patch:
      operation = api_utils.PatchApplication(self._client, app_ref, application)
    else:
      operation = api_utils.CreateApplication(self._client, app_ref,
                                              application)
    api_utils.WaitForApplicationOperation(self._client, operation)

  def _CreateDeployment(self,
                        appname,
                        create_selector=None,
                        delete_selector=None):
    """Create a deployment, waits for operation to finish.

    Args:
      appname:  name of the application.
      create_selector: create selector for the deployment.
      delete_selector: delete selector for the deployment.
    """
    app_ref = self.GetAppRef(appname)
    deployment_name = self._GetDeploymentName(app_ref.Name())
    # TODO(b/217573594): remove this when oneof constraint is removed.
    if create_selector and delete_selector:
      raise exceptions.ArgumentError('create_selector and delete_selector '
                                     'cannot be specified at the same time.')
    deployment = self.messages.Deployment(
        name=deployment_name,
        createSelector=create_selector,
        deleteSelector=delete_selector)
    deployment_ops = api_utils.CreateDeployment(self._client, app_ref,
                                                deployment)

    dep_response = api_utils.WaitForDeploymentOperation(
        self._client, deployment_ops)
    self.CheckDeploymentState(dep_response)

  def _GetDeploymentName(self, appname):
    return '{}-{}'.format(
        appname,
        datetime.datetime.now().strftime('%Y%m%d%H%M%S'))

  def GetResourceTypeFromConfig(self, resource_config):
    """Gets the resource type.

    The input is converted from proto with "oneof" property. Thus the dictionary
    is expected to have only one key, matching the type of the matching oneof.

    Args:
      resource_config: dict, the resource configuration.

    Returns:
      str, the integration type.
    """
    keys = list(resource_config.keys())
    if len(keys) != 1:
      raise exceptions.ConfigurationError(
          'resource config is invalid: {}.'.format(resource_config))
    return keys[0]

  def GetIntegration(self, name):
    """Get an integration.

    Args:
      name: str, the name of the resource.

    Raises:
      IntegrationNotFoundError: If the integration is not found.

    Returns:
      The integration config.
    """
    try:
      return self._GetDefaultAppDict()[_CONFIG_KEY][_RESOURCES_KEY][name]
    except KeyError:
      raise exceptions.IntegrationNotFoundError(
          'Integration [{}] cannot be found'.format(name))

  def GetIntegrationStatus(self, name):
    """Get status of an integration.

    Args:
      name: str, the name of the resource.

    Returns:
      The ResourceStatus of the integration, or None if not found
    """
    try:
      application_status = api_utils.GetApplicationStatus(
          self._client, self.GetAppRef(_DEFAULT_APP_NAME), name)
      app_status_dict = encoding.MessageToDict(application_status)
      integration_status = app_status_dict.get('resources', {}).get(name)
      if integration_status:
        return integration_status
      return None
    except KeyError:
      return None
    except api_exceptions.HttpError:
      return None

  def CreateIntegration(self,
                        tracker,
                        integration_type,
                        parameters,
                        service,
                        name=None):
    """Create an integration.

    Args:
      tracker: StagedProgressTracker, to report on the progress of releasing.
      integration_type:  type of the integration.
      parameters: parameter dictionary from args.
      service: the service to attach to the new integration.
      name: name of the integration, if empty, a defalt one will be generated.

    Returns:
      The name of the integration.
    """
    app_dict = self._GetDefaultAppDict()
    resources_map = app_dict[_CONFIG_KEY][_RESOURCES_KEY]
    if not name:
      name = self._NewIntegrationName(integration_type, service, parameters,
                                      app_dict)

    resource_type = self._GetResourceType(integration_type)

    if name in resources_map:
      raise exceptions.ArgumentError(
          'Integration with name [{}] already exists.'.format(name))

    resource_config = self._GetResourceConfig(resource_type, parameters,
                                              service, None, {})
    resources_map[name] = resource_config
    match_type_names = self._GetCreateSelectors(name, resource_type, service)
    if service:
      self._EnsureServiceConfig(resources_map, service)
      self._AddServiceToIntegrationRef(name, resource_type,
                                       resources_map[service])

    self.CheckCloudRunServices([service])

    deploy_message = messages_util.GetDeployMessage(resource_type, create=True)
    application = encoding.DictToMessage(app_dict, self.messages.Application)
    try:
      self.ApplyAppConfig(
          tracker=tracker,
          appname=_DEFAULT_APP_NAME,
          appconfig=application.config,
          integration_name=name,
          deploy_message=deploy_message,
          match_type_names=match_type_names,
          etag=application.etag)
    except exceptions.IntegrationsOperationError as err:
      tracker.AddWarning('To retry the deployment, use update command ' +
                         '`gcloud alpha run integrations update {}`'
                         .format(name))
      raise err

    return name

  def UpdateIntegration(self,
                        tracker,
                        name,
                        parameters,
                        add_service=None,
                        remove_service=None):
    """Update an integration.

    Args:
      tracker: StagedProgressTracker, to report on the progress of releasing.
      name:  str, the name of the resource to update.
      parameters: dict, the parameters from args.
      add_service: the service to attach to the integration.
      remove_service: the service to remove from the integration.

    Raises:
      IntegrationNotFoundError: If the integration is not found.

    Returns:
      The name of the integration.
    """
    app_dict = self._GetDefaultAppDict()
    resources_map = app_dict[_CONFIG_KEY][_RESOURCES_KEY]
    existing_resource = resources_map.get(name)
    if existing_resource is None:
      raise exceptions.IntegrationNotFoundError(
          'Integration [{}] cannot be found'.format(name))

    resource_type = self.GetResourceTypeFromConfig(existing_resource)
    integration_type = types_utils.GetIntegrationType(resource_type)
    flags.ValidateUpdateParameters(integration_type, parameters)
    resource_config = self._GetResourceConfig(resource_type, parameters,
                                              add_service, remove_service,
                                              existing_resource)
    resources_map[name] = resource_config
    match_type_names = self._GetCreateSelectors(name, resource_type,
                                                add_service, remove_service)

    if add_service:
      self._EnsureServiceConfig(resources_map, add_service)
      self._AddServiceToIntegrationRef(name, resource_type,
                                       resources_map[add_service])
    if remove_service and remove_service in resources_map:
      self._RemoveServiceToIntegrationRef(name, resource_type,
                                          resources_map[remove_service])

    services = []
    if self._IsIngressResource(resource_type):
      # For ingress resource, expand the check list and selector to include all
      # binded services.
      services = self._GetRefServices(name, resource_type, resource_config,
                                      resources_map)
      for service in services:
        if service != add_service:
          match_type_names.append({'type': 'service', 'name': service})
    elif add_service:
      services.append(add_service)
    elif self._IsBackingResource(resource_type) and remove_service is None:
      services.extend(
          self._GetRefServices(name, resource_type, resource_config,
                               resources_map))
      for service in services:
        match_type_names.append({'type': 'service', 'name': service})

    if services:
      self.CheckCloudRunServices(services)

    deploy_message = messages_util.GetDeployMessage(resource_type)
    application = encoding.DictToMessage(app_dict, self.messages.Application)
    return self.ApplyAppConfig(
        tracker=tracker,
        appname=_DEFAULT_APP_NAME,
        appconfig=application.config,
        integration_name=name,
        deploy_message=deploy_message,
        match_type_names=match_type_names,
        etag=application.etag)

  def DeleteIntegration(self, name, tracker):
    """Delete an integration.

    Args:
      name:  str, the name of the resource to update.
      tracker: StagedProgressTracker, to report on the progress.

    Raises:
      IntegrationNotFoundError: If the integration is not found.

    Returns:
      str, the type of the integration that is deleted.
    """
    app_dict = self._GetDefaultAppDict()
    resources_map = app_dict[_CONFIG_KEY][_RESOURCES_KEY]
    resource = resources_map.get(name)
    if resource is None:
      raise exceptions.IntegrationNotFoundError(
          'Integration [{}] cannot be found'.format(name))
    resource_type = self.GetResourceTypeFromConfig(resource)

    # TODO(b/222748706): revisit whether this apply to future ingress services.
    services = []
    if not self._IsIngressResource(resource_type):
      # Unbind services
      services = self._GetRefServices(name, resource_type, resource,
                                      resources_map)
    if services:
      match_type_names = []
      for service in services:
        self._RemoveServiceToIntegrationRef(name, resource_type,
                                            resources_map[service])
        match_type_names.append({'type': 'service', 'name': service})
      application = encoding.DictToMessage(app_dict,
                                           self.messages.Application)
      # TODO(b/222748706): refine message on failure.
      self.ApplyAppConfig(
          tracker=tracker,
          appname=_DEFAULT_APP_NAME,
          appconfig=application.config,
          match_type_names=match_type_names,
          intermediate_step=True,
          etag=application.etag)
    else:
      tracker.CompleteStage(stages.UPDATE_APPLICATION)
      tracker.CompleteStage(stages.CREATE_DEPLOYMENT)

    # TODO(b/222748706): refine message on failure.
    # Undeploy integration resource
    self._UndeployResource(resource_type, name, tracker)

    integration_type = types_utils.GetIntegrationType(resource_type)
    return integration_type

  def _UndeployResource(self, resource_type, name, tracker):
    """Undeploy a resource.

    Args:
      resource_type: type of the resource
      name: name of the resource
      tracker: StagedProgressTracker, to report on the progress.
    """
    delete_selector = self._GetDeleteSelectors(name, resource_type)

    tracker.StartStage(stages.UNDEPLOY_RESOURCE)
    self._CreateDeployment(
        appname=_DEFAULT_APP_NAME,
        delete_selector=delete_selector,)
    tracker.CompleteStage(stages.UNDEPLOY_RESOURCE)

    # Get application again to refresh etag before update
    app_dict = self._GetDefaultAppDict()
    del app_dict[_CONFIG_KEY][_RESOURCES_KEY][name]
    application = encoding.DictToMessage(app_dict, self.messages.Application)
    tracker.StartStage(stages.CLEANUP_CONFIGURATION)
    self._UpdateApplication(
        appname=_DEFAULT_APP_NAME,
        appconfig=application.config,
        etag=application.etag)
    tracker.CompleteStage(stages.CLEANUP_CONFIGURATION)

  def _IsIngressResource(self, resource_type):
    return resource_type == 'router'

  def _IsBackingResource(self, resource_type):
    return resource_type == 'redis'

  def ListIntegrationTypes(self):
    """Returns the list of integration type definitions.

    Returns:
      An array of integration type definitions.
    """
    return types_utils.IntegrationTypes(self._client)

  def GetIntegrationTypeDefinition(self, type_name):
    """Returns the integration type definition of the given name.

    Args:
      type_name: name of the integration type

    Returns:
      An integration type definition. None if no matching type.
    """
    int_types = types_utils.IntegrationTypes(self._client)
    for t in int_types:
      if t['name'] == type_name:
        return t
    return None

  def ListIntegrations(self, integration_type_filter, service_name_filter):
    """Returns the list of integrations.

    Args:
      integration_type_filter: str, if populated integration type to filter by.
      service_name_filter: str, if populated service name to filter by.

    Returns:
      List of Dicts containing name, type, and services.

    """
    app = api_utils.GetApplication(self._client,
                                   self.GetAppRef(_DEFAULT_APP_NAME))
    if not app:
      return []

    app_dict = encoding.MessageToDict(app)
    app_resources = app_dict.get('config', {}).get('resources')
    if not app_resources:
      return []

    # Filter by type and/or service.
    output = []
    for name, resource in app_resources.items():
      resource_type = self.GetResourceTypeFromConfig(resource)
      integration_type = types_utils.GetIntegrationType(resource_type)

      # Remove invalid integrations.
      if integration_type is None:
        continue

      # Always remove services.
      if integration_type == 'service':
        continue

      # TODO(b/217744072): Support Cloud SDK topic filtering.
      # Optionally filter by type.
      if (integration_type_filter and
          integration_type != integration_type_filter):
        continue

      # Optionally filter by service.
      services = self._GetRefServices(name, resource_type, resource,
                                      app_resources)
      if service_name_filter and service_name_filter not in services:
        continue

      # Assemble for Cloud SDK table formater.
      resource = {
          'name': name,
          'type': integration_type,
          'services': ','.join(services)
      }
      output.append(resource)

    return output

  def _GetCreateSelectors(self,
                          integration_name,
                          resource_type,
                          add_service_name,
                          remove_service_name=None):
    """Returns create selectors for given integration and service.

    Args:
      integration_name: str, name of integration.
      resource_type: str, type of integration.
      add_service_name: str, name of the service being added.
      remove_service_name: str, name of the service being removed.

    Returns:
      list of dict typed names.
    """
    service_name = add_service_name if add_service_name else remove_service_name
    selectors = [{'type': resource_type, 'name': integration_name}]

    # Handle router edgecase. Selector should not be added for remove service.
    if resource_type == 'router' and add_service_name:
      selectors.append({'type': 'service', 'name': add_service_name})
    elif resource_type != 'router' and service_name:
      selectors.append({'type': 'service', 'name': service_name})

    # TODO(b/222753640): Remove redis specific logic after default VPC logic
    # is handled in CP.
    if resource_type == 'redis':
      # For now redis integration has a shadow VPC resource. This will hopefully
      # change in the near future, but for now it needs to be actuated
      selectors.append({'type': 'vpc', 'name': '*'})

    return selectors

  def _GetDeleteSelectors(self, name, resource_type):
    """Returns delete selectors for undeploying an integration.

    Args:
      name: str, name of integration.
      resource_type: str, type of resource.

    Returns:
      the selector object
    """
    selectors = [{'type': resource_type, 'name': name}]

    if resource_type == 'redis':
      # TODO(b/222753640): remove this all destroying vpc selector
      selectors.append({'type': 'vpc', 'name': '*'})

    return {'matchTypeNames': selectors}

  def _AddServiceToIntegrationRef(self, name, resource_type, service):
    """Add service to integration ref.

    Args:
      name: str, name of integration.
      resource_type: str, type of integration.
      service: dict of proto, service to add ref too.
    """
    if resource_type == 'router':
      return

    # Check if ref already exists
    refs = [ref['ref'] for ref in service['service'].get('resources', [])]
    if '{}/{}'.format(resource_type, name) not in refs:
      service['service'].setdefault('resources', []).append(
          {'ref': '{}/{}'.format(resource_type, name)})

  def _RemoveServiceToIntegrationRef(self, name, resource_type, service):
    """Remove service to integration ref.

    Args:
      name: str, name of integration.
      resource_type: str, type of integration.
      service: dict of proto, service from which to remove ref.
    """
    if resource_type == 'router':
      return

    for ref in service.get('service', {}).get('resources', []):
      if ref['ref'] == '{}/{}'.format(resource_type, name):
        service['service']['resources'].remove(ref)

  def _GetRefServices(self, name, resource_type, resource, all_resources):
    """Returns list of services referenced by integration.

    Args:
      name: str, name of integration.
      resource_type: str, type of resource.
      resource: dict, internal representation of resource.
      all_resources: dict, of all resource with in appconfig default.

    Returns:
      list(str), of all service names referenced.
    """
    output = []

    # TODO(b/219606516) Ideally add bidirectional references to API. If not
    # feasible optimize code block create reverse reference table once and reuse
    # it.
    # For redis look for service to integration refs.
    if resource_type == 'redis':
      for resource_name, resource in all_resources.items():
        ref_name = '{}/{}'.format(resource_type, name)
        if resource.get('service', {}).get('resources'):
          if any([
              ref['ref'] == ref_name for ref in resource['service']['resources']
          ]):
            output.append(resource_name)

    # For custom-domain/router look for integration to service refs.
    elif resource_type == 'router':
      if resource.get('router', {}).get('default-route', {}).get('ref'):
        output.append(resource['router']['default-route']['ref'].replace(
            'service/', ''))

      if resource.get('router', {}).get('routes'):
        for route in resource['router']['routes']:
          if route.get('ref'):
            output.append(route['ref'].replace('service/', ''))

    return output

  def _GetDefaultAppDict(self):
    """Returns the default application as a dict.

    Returns:
      dict representing the application.
    """
    application = api_utils.GetApplication(self._client,
                                           self.GetAppRef(_DEFAULT_APP_NAME))
    if not application:
      application = self.messages.Application(
          name=_DEFAULT_APP_NAME, config={_RESOURCES_KEY: {}})
    app_dict = encoding.MessageToDict(application)
    app_dict.setdefault(_CONFIG_KEY, {})
    app_dict[_CONFIG_KEY].setdefault(_RESOURCES_KEY, {})
    return app_dict

  def _GetResourceConfig(self, res_type, parameters, add_service,
                         remove_service, res_config):
    """Returns a new resource config according to the parameters.

    Args:
      res_type: type of the resource.
      parameters: parameter dictionary from args.
      add_service: the service to attach to the integration.
      remove_service: the service to remove from the integration.
      res_config: previous resource config. If given, changes will be made based
        on it.

    Returns:
      A new resource config
    """
    if res_config is not None and res_type in res_config:
      config = dict(res_config[res_type])
    else:
      config = {}

    if res_type == 'router':
      if 'dns-zone' in parameters:
        config['dns-zone'] = parameters['dns-zone']
      if 'domain' in parameters:
        config['domain'] = parameters['domain']
      if remove_service:
        ref = 'service/{}'.format(remove_service)
        if 'default-route' in config and ref in config['default-route']['ref']:
          raise exceptions.ArgumentError(
              'Cannot remove service associated with the default path (/*)')

        config['routes'] = [
            x for x in config.get('routes', []) if x['ref'] != ref
        ]
      if add_service:
        route = {'ref': 'service/{}'.format(add_service)}
        if 'paths' in parameters:
          route['paths'] = parameters['paths']
          if 'routes' not in config:
            config['routes'] = []
          config['routes'].append(route)
        else:
          config['default-route'] = route
    elif res_type == 'redis':
      instance = config.setdefault('instance', {})
      if 'memory-size-gb' in parameters:
        instance['memory-size-gb'] = parameters['memory-size-gb']
      if 'tier' in parameters:
        instance['tier'] = parameters['tier']
      if 'version' in parameters:
        instance['version'] = parameters['version']

    else:
      raise exceptions.ArgumentError(
          'Unsupported integration type [{}]'.format(res_type))

    return {res_type: config}

  def _EnsureServiceConfig(self, resources_map, service_name):
    if service_name not in resources_map:
      resources_map[service_name] = {'service': {}}

  def _GetResourceType(self, integration_type):
    type_def = self.GetIntegrationTypeDefinition(integration_type)
    if type_def is not None:
      res_name = type_def.get('resource_name', None)
      if res_name is not None:
        return res_name
    return integration_type

  def _NewIntegrationName(self, integration_type, service, parameters,
                          app_dict):
    """Returns a new name for an integration.

    It makes sure the new name does not exist in the given app_dict.

    Args:
      integration_type:  str, name of the integration type.
      service: str, name of the service.
      parameters: parameter dictionary from args.
      app_dict: dict, the dictionary that represents the application.

    Returns:
      str, the new name.

    """
    if integration_type == 'custom-domain':
      domain = parameters['domain']
      if not domain:
        raise exceptions.ArgumentError('domain is required in "PARAMETERS" '
                                       'for integration type "custom-domain"')
      return 'domain-{}'.format(domain.replace('.', '-'))

    name = '{}-{}'.format(integration_type, service)
    while name in app_dict[_CONFIG_KEY][_RESOURCES_KEY]:
      count = 1
      match = re.search(r'(.+)-(\d+)$', name)
      if match:
        name = match.group(1)
        count = int(match.group(2)) + 1
      name = '{}-{}'.format(name, count)
    return name

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
        collection='runapps.projects.locations.applications')
    return app_ref

  def GetServiceRef(self, name):
    """Returns the Cloud Run service reference.

    Args:
      name:  name of the Cloud Run service.

    Returns:
      Cloud Run service reference
    """
    project = properties.VALUES.core.project.Get(required=True)
    service_ref = resources.REGISTRY.Parse(
        name,
        params={
            'namespacesId': project,
            'servicesId': name,
        },
        collection='run.namespaces.services')
    return service_ref

  def CheckCloudRunServices(self, service_names):
    """Check for existence of Cloud Run services.

    Args:
      service_names: array, list of service to check.

    Raises:
      exceptions.ServiceNotFoundError: when a Cloud Run service doesn't exist.
    """
    conn_context = connection_context.GetConnectionContext(
        {'region', self._region}, run_flags.Product.RUN)
    with serverless_operations.Connect(conn_context) as client:
      for name in service_names:
        service_ref = self.GetServiceRef(name)
        service = client.GetService(service_ref)
        if not service:
          raise exceptions.ServiceNotFoundError(
              'Service [{}] could not be found.'.format(name))

  def CheckDeploymentState(self, response):
    """Throws any unexpected states contained within deployment reponse.

    Args:
      response: run_apps.v1alpha1.deployment, response to check
    """
    # Short hand refference of deployment/job state
    dep_state = self.messages.DeploymentStatus.StateValueValuesEnum
    job_state = self.messages.JobDetails.StateValueValuesEnum

    if response.status.state == dep_state.SUCCEEDED:
      return

    if response.status.state == dep_state.FAILED:
      if not response.status.errorMessage:
        raise exceptions.IntegrationsOperationError('Configuration failed.')

      # Look for job that failed. It should always be last job, but this is not
      # guaranteed behavior.
      url = ''
      for job in response.status.jobDetails[::-1]:
        if job.state == job_state.FAILED:
          url = job.jobUri
          break

      error_msg = 'Configuration failed with error:\n  {}'.format(
          '\n  '.join(response.status.errorMessage.split('; ')))
      if url:
        error_msg += '\nLogs are available at {}'.format(url)

      raise exceptions.IntegrationsOperationError(error_msg)

    else:
      raise exceptions.IntegrationsOperationError(
          'Configuration returned in unexpected state "{}".'.format(
              response.status.state.name))
