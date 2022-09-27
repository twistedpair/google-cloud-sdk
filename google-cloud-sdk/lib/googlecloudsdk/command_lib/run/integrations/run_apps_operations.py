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

from apitools.base.py import encoding
from apitools.base.py import exceptions as api_exceptions
from googlecloudsdk.api_lib.run import global_methods
from googlecloudsdk.api_lib.run.integrations import api_utils
from googlecloudsdk.api_lib.run.integrations import types_utils
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.run import connection_context
from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.command_lib.run import serverless_operations
from googlecloudsdk.command_lib.run.integrations import flags
from googlecloudsdk.command_lib.run.integrations import integration_list_printer
from googlecloudsdk.command_lib.run.integrations import messages_util
from googlecloudsdk.command_lib.run.integrations import stages
from googlecloudsdk.command_lib.run.integrations import typekits_util
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import progress_tracker

# Max wait time before timing out
_POLLING_TIMEOUT_MS = 180000
# Max wait time between poll retries before timing out
_RETRY_TIMEOUT_MS = 1000

_SERVICE_TYPE = 'service'

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
                     etag=None,
                     tracker_update_func=None):
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
      tracker_update_func: optional custom fn to update the tracker.
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
      self._CreateDeployment(
          appname,
          tracker,
          tracker_update_func=tracker_update_func,
          create_selector=create_selector)
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
                        tracker,
                        tracker_update_func=None,
                        create_selector=None,
                        delete_selector=None):
    """Create a deployment, waits for operation to finish.

    Args:
      appname:  name of the application.
      tracker: The ProgressTracker to track the deployment operation.
      tracker_update_func: optional custom fn to update the tracker.
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
        self._client,
        deployment_ops,
        tracker,
        tracker_update_func=tracker_update_func)
    self.CheckDeploymentState(dep_response)

  def _GetDeploymentName(self, appname):
    return '{}-{}'.format(appname,
                          datetime.datetime.now().strftime('%Y%m%d%H%M%S'))

  @staticmethod
  def _UpdateDeploymentTracker(tracker, operation, tracker_stages):
    """Updates deployment tracker with the current status of operation.

    Args:
      tracker: The ProgressTracker to track the deployment operation.
      operation: run_apps.v1alpha1.operation object for the deployment.
      tracker_stages: map of stages with key as stage key (string) and value is
        the progress_tracker.Stage.
    """

    messages = api_utils.GetMessages()
    metadata = api_utils.GetDeploymentOperationMetadata(messages, operation)
    resources_in_progress = []
    resources_completed = []
    resource_state = messages.ResourceDeploymentStatus.StateValueValuesEnum

    if metadata.resourceStatus is not None:
      for resource in metadata.resourceStatus:
        stage_name = stages.StageKeyForResourceDeployment(resource.name.type)
        if resource.state == resource_state.RUNNING:
          resources_in_progress.append(stage_name)
        if resource.state == resource_state.FINISHED:
          resources_completed.append(stage_name)

    for resource in resources_in_progress:
      if resource in tracker_stages and tracker.IsWaiting(resource):
        tracker.StartStage(resource)

    for resource in resources_completed:
      if resource in tracker_stages and tracker.IsRunning(resource):
        tracker.CompleteStage(resource)
    tracker.Tick()

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
      return self._GetDefaultAppDict()[api_utils.APP_DICT_CONFIG_KEY][
          api_utils.APP_CONFIG_DICT_RESOURCES_KEY][name]
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

  def GetLatestDeployment(self, resource_config):
    """Fetches the deployment object given a resource config.

    Args:
      resource_config: dict, may contain a key called 'latestDeployment'

    Returns:
      run_apps.v1alpha1.Deployment, the Deployment object.  This is None if
        the latest deployment name does not exist.  If the deployment itself
        cannot be found via the name or any http errors occur, then None will
        be returned.
    """
    latest_deployment_name = resource_config.get(
        types_utils.LATEST_DEPLOYMENT_FIELD)

    if not latest_deployment_name:
      return None

    try:
      return api_utils.GetDeployment(self._client, latest_deployment_name)
    except api_exceptions.HttpError:
      return None

  def CreateIntegration(self, integration_type, parameters, service, name=None):
    """Create an integration.

    Args:
      integration_type:  type of the integration.
      parameters: parameter dictionary from args.
      service: the service to attach to the new integration.
      name: name of the integration, if empty, a defalt one will be generated.

    Returns:
      The name of the integration.
    """
    app_dict = self._GetDefaultAppDict()
    resources_map = app_dict[api_utils.APP_DICT_CONFIG_KEY][
        api_utils.APP_CONFIG_DICT_RESOURCES_KEY]
    typekit = typekits_util.GetTypeKit(integration_type)
    if name and typekit.is_singleton:
      raise exceptions.ArgumentError(
          '--name is not allowed for integration type [{}].'.format(
              integration_type))
    if not name:
      name = typekit.NewIntegrationName(service, parameters, resources_map)

    resource_type = typekit.resource_type

    if name in resources_map:
      raise exceptions.ArgumentError(
          messages_util.IntegrationAlreadyExists(name))

    resource_config = {}
    typekit.UpdateResourceConfig(parameters, resource_config)

    resources_map[name] = {resource_type: resource_config}

    match_type_names = typekit.GetCreateSelectors(name, service)
    if typekit.is_ingress_service:
      # For ingress resource, expand the check list and selector to include all
      # binded services.
      services = typekit.GetRefServices(name, resource_config, resources_map)
      for ref_service in services:
        if ref_service != service:
          match_type_names.append({'type': _SERVICE_TYPE, 'name': ref_service})

    if service:
      typekit.BindServiceToIntegration(
          name, resource_config, service,
          resources_map.setdefault(service, {}).setdefault(_SERVICE_TYPE, {}),
          parameters)
      services = [service]
    else:
      services = typekit.GetRefServices(name, resource_config, resources_map)

    self.EnsureCloudRunServices(services, resources_map)
    self.CheckCloudRunServices(services)

    resource_stages = typekit.GetCreateComponentTypes(
        selectors=match_type_names,
        app_dict=app_dict)

    deploy_message = messages_util.GetDeployMessage(resource_type, create=True)
    application = encoding.DictToMessage(app_dict, self.messages.Application)
    stages_map = stages.IntegrationStages(
        create=True, resource_types=resource_stages)

    def StatusUpdate(tracker, operation, unused_status):
      self._UpdateDeploymentTracker(tracker, operation, stages_map)
      return

    with progress_tracker.StagedProgressTracker(
        'Creating new Integration...',
        stages_map.values(),
        failure_message='Failed to create new integration.') as tracker:
      try:
        self.ApplyAppConfig(
            tracker=tracker,
            tracker_update_func=StatusUpdate,
            appname=_DEFAULT_APP_NAME,
            appconfig=application.config,
            integration_name=name,
            deploy_message=deploy_message,
            match_type_names=match_type_names,
            etag=application.etag)
      except exceptions.IntegrationsOperationError as err:
        tracker.AddWarning(
            'To retry the deployment, use update command ' +
            'gcloud alpha run integrations update {}'.format(name))
        raise err

    return name

  def UpdateIntegration(self,
                        name,
                        parameters,
                        add_service=None,
                        remove_service=None):
    """Update an integration.

    Args:
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
    resources_map = app_dict[api_utils.APP_DICT_CONFIG_KEY][
        api_utils.APP_CONFIG_DICT_RESOURCES_KEY]
    existing_resource = resources_map.get(name)
    if existing_resource is None:
      raise exceptions.IntegrationNotFoundError(
          messages_util.IntegrationNotFound(name))

    typekit = typekits_util.GetTypeKitByResource(existing_resource)
    resource_type = typekit.resource_type

    flags.ValidateUpdateParameters(typekit.integration_type, parameters)

    resource_config = existing_resource[typekit.resource_type]
    typekit.UpdateResourceConfig(parameters, resource_config)

    match_type_names = typekit.GetCreateSelectors(name, add_service,
                                                  remove_service)

    if add_service:
      typekit.BindServiceToIntegration(
          name, resource_config, add_service,
          resources_map.setdefault(add_service,
                                   {}).setdefault(_SERVICE_TYPE, {}),
          parameters)

    if remove_service:
      if remove_service in resources_map:
        typekit.UnbindServiceFromIntegration(
            name, resource_config, remove_service,
            resources_map[remove_service].setdefault(_SERVICE_TYPE,
                                                     {}), parameters)
      else:
        raise exceptions.ServiceNotFoundError(
            'Service [{}] is not found among integrations'.format(
                remove_service))

    services = []
    if typekit.is_ingress_service:
      # For ingress resource, expand the check list and selector to include all
      # binded services.
      services = typekit.GetRefServices(name, resource_config, resources_map)
      for service in services:
        if service != add_service:
          match_type_names.append({'type': _SERVICE_TYPE, 'name': service})
    elif add_service:
      services.append(add_service)
    elif self._IsBackingResource(resource_type) and remove_service is None:
      services.extend(
          typekit.GetRefServices(name, resource_config, resources_map))
      for service in services:
        match_type_names.append({'type': _SERVICE_TYPE, 'name': service})

    if services:
      self.EnsureCloudRunServices(services, resources_map)
      self.CheckCloudRunServices(services)

    deploy_message = messages_util.GetDeployMessage(resource_type)
    application = encoding.DictToMessage(app_dict, self.messages.Application)

    resource_stages = typekit.GetCreateComponentTypes(
        selectors=match_type_names,
        app_dict=app_dict)
    stages_map = stages.IntegrationStages(
        create=False, resource_types=resource_stages)

    def StatusUpdate(tracker, operation, unused_status):
      self._UpdateDeploymentTracker(tracker, operation, stages_map)
      return

    with progress_tracker.StagedProgressTracker(
        'Updating Integration...',
        stages_map.values(),
        failure_message='Failed to update integration.') as tracker:
      return self.ApplyAppConfig(
          tracker=tracker,
          tracker_update_func=StatusUpdate,
          appname=_DEFAULT_APP_NAME,
          appconfig=application.config,
          integration_name=name,
          deploy_message=deploy_message,
          match_type_names=match_type_names,
          etag=application.etag)

  def DeleteIntegration(self, name):
    """Delete an integration.

    Args:
      name:  str, the name of the resource to update.

    Raises:
      IntegrationNotFoundError: If the integration is not found.

    Returns:
      str, the type of the integration that is deleted.
    """
    app_dict = self._GetDefaultAppDict()
    resources_map = app_dict[api_utils.APP_DICT_CONFIG_KEY][
        api_utils.APP_CONFIG_DICT_RESOURCES_KEY]
    resource = resources_map.get(name)
    if resource is None:
      raise exceptions.IntegrationNotFoundError(
          'Integration [{}] cannot be found'.format(name))
    typekit = typekits_util.GetTypeKitByResource(resource)
    resource_type = typekit.resource_type

    # TODO(b/222748706): revisit whether this apply to future ingress services.
    services = []
    if typekit.is_backing_service:
      # Unbind services
      services = typekit.GetRefServices(name, resource.get(resource_type),
                                        resources_map)
    service_match_type_names = []
    if services:
      for service in services:
        service_match_type_names.append({
            'type': _SERVICE_TYPE,
            'name': service
        })
    delete_match_type_names = typekit.GetDeleteSelectors(name)
    should_configure_service = bool(services)
    resource_stages = typekit.GetDeleteComponentTypes(
        selectors=delete_match_type_names, app_dict=app_dict)
    stages_map = stages.IntegrationDeleteStages(
        destroy_resource_types=resource_stages,
        should_configure_service=should_configure_service)

    def StatusUpdate(tracker, operation, unused_status):
      self._UpdateDeploymentTracker(tracker, operation, stages_map)
      return
    with progress_tracker.StagedProgressTracker(
        'Deleting Integration...',
        stages_map.values(),
        failure_message='Failed to delete integration.') as tracker:
      if services:
        for service in services:
          typekit.UnbindServiceFromIntegration(
              name, resource[resource_type], service,
              resources_map[service][_SERVICE_TYPE], {})
        application = encoding.DictToMessage(app_dict,
                                             self.messages.Application)
        # TODO(b/222748706): refine message on failure.
        self.ApplyAppConfig(
            tracker=tracker,
            tracker_update_func=StatusUpdate,
            appname=_DEFAULT_APP_NAME,
            appconfig=application.config,
            match_type_names=service_match_type_names,
            intermediate_step=True,
            etag=application.etag)
      # Undeploy integration resource
      delete_selector = {'matchTypeNames': delete_match_type_names}
      self._UndeployResource(name, delete_selector, tracker, StatusUpdate)

    type_def = types_utils.GetIntegrationFromResource(resource)
    integration_type = type_def[types_utils.INTEGRATION_TYPE]
    return integration_type

  def _UndeployResource(self,
                        name,
                        delete_selector,
                        tracker,
                        tracker_update_func=None):
    """Undeploy a resource.

    Args:
      name: name of the resource
      delete_selector: The selector for the undeploy operation.
      tracker: StagedProgressTracker, to report on the progress.
      tracker_update_func: optional custom fn to update the tracker.
    """
    tracker.StartStage(stages.UNDEPLOY_RESOURCE)
    self._CreateDeployment(
        appname=_DEFAULT_APP_NAME,
        tracker=tracker,
        tracker_update_func=tracker_update_func,
        delete_selector=delete_selector,
    )
    tracker.CompleteStage(stages.UNDEPLOY_RESOURCE)

    # Get application again to refresh etag before update
    app_dict = self._GetDefaultAppDict()
    del app_dict[api_utils.APP_DICT_CONFIG_KEY][
        api_utils.APP_CONFIG_DICT_RESOURCES_KEY][name]
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
    return types_utils.GetIntegration(type_name)

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
    # the dict is sorted by the resource name to guarantee the output
    # is the same every time.  This is useful for scenario tests.
    for name, resource in sorted(app_resources.items()):
      try:
        typekit = typekits_util.GetTypeKitByResource(resource)
      except exceptions.ArgumentError:
        # If no matching typekit, like service, skip over.
        continue

      resource_type = typekit.resource_type
      integration_type = typekit.integration_type

      # TODO(b/217744072): Support Cloud SDK topic filtering.
      # Optionally filter by type.
      if (integration_type_filter and
          integration_type != integration_type_filter):
        continue

      # Optionally filter by service.
      services = typekit.GetRefServices(name, resource.get(resource_type),
                                        app_resources)
      if service_name_filter and service_name_filter not in services:
        continue

      status = (
          self.messages.DeploymentStatus.StateValueValuesEnum.STATE_UNSPECIFIED
          )
      latest_deployment = resource.get(types_utils.LATEST_DEPLOYMENT_FIELD)
      if latest_deployment:
        dep = api_utils.GetDeployment(self._client, latest_deployment)
        if dep:
          status = dep.status.state

      output.append(
          integration_list_printer.Row(
              integration_name=name,
              integration_type=integration_type,
              services=','.join(services),
              latest_deployment_status=str(status),
          ))
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
          name=_DEFAULT_APP_NAME,
          config={api_utils.APP_CONFIG_DICT_RESOURCES_KEY: {}})
    return api_utils.ApplicationToDict(application)

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

  def EnsureCloudRunServices(self, service_names, resources_map):
    """Make sure resources block for the Cloud Run services exists.

    Args:
      service_names: array, list of service to check.
      resources_map: the resources map of the application
    """
    for service in service_names:
      resources_map.setdefault(service, {}).setdefault(_SERVICE_TYPE, {})

  def CheckCloudRunServices(self, service_names):
    """Check for existence of Cloud Run services.

    Args:
      service_names: array, list of service to check.

    Raises:
      exceptions.ServiceNotFoundError: when a Cloud Run service doesn't exist.
    """
    conn_context = connection_context.RegionalConnectionContext(
        self._region, global_methods.SERVERLESS_API_NAME,
        global_methods.SERVERLESS_API_VERSION)
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
