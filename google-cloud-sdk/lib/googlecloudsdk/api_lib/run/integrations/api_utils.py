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

import re

from apitools.base.py import encoding as apitools_encoding
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import exceptions as api_lib_exceptions
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import encoding
from googlecloudsdk.core.util import retry


API_NAME = 'runapps'
API_VERSION = 'v1alpha1'

# Key for the config field of application dictionary.
APP_DICT_CONFIG_KEY = 'config'
# Key for the resource field within config field of application dictionary.
APP_CONFIG_DICT_RESOURCES_KEY = 'resources'

# Max wait time before timing out, match timeout of CP
_POLLING_TIMEOUT_MS = 30 * 60 * 1000
# Max wait time between poll retries before timing out
_RETRY_TIMEOUT_MS = 1000

_LOCATION_ERROR_REGEX = re.compile(r'Location [\w-]+ is not found')


def GetMessages():
  """Returns the messages module for the Runapps API.

  Returns:
    Module containing the definitions of messages for the Runapps API.
  """
  return apis.GetMessagesModule(API_NAME, API_VERSION)


def GetApplication(client, app_ref):
  """Calls ApplicationGet API of Runapps of the specified reference.

  Args:
    client: GAPIC API client, the api client to use.
    app_ref: googlecloudsdk.core.resources.Resource, the resource reference of
      the application.

  Returns:
    The Application object. Or None if not found.
  """
  request = client.MESSAGES_MODULE.RunappsProjectsLocationsApplicationsGetRequest(
      name=app_ref.RelativeName())
  try:
    return client.projects_locations_applications.Get(request)
  except apitools_exceptions.HttpForbiddenError as e:
    _HandleLocationError(e)
  except apitools_exceptions.HttpNotFoundError:
    return None


def ApplicationToDict(application):
  """Converts application resource to a dictionary.

  Args:
    application: The application object.

  Returns:
    The application data in a dictionary format.
  """
  app_dict = apitools_encoding.MessageToDict(application)
  app_dict.setdefault(APP_DICT_CONFIG_KEY,
                      {}).setdefault(APP_CONFIG_DICT_RESOURCES_KEY, {})
  return app_dict


def GetApplicationStatus(client, app_ref, resource_name=None):
  """Calls ApplicationGetStatus API of Runapps of the specified reference.

  Args:
    client: GAPIC API client, the api client to use.
    app_ref: googlecloudsdk.core.resources.Resource, the resource reference of
      the application.
    resource_name: name of the resource to get status for. If not given, all
      resources in the application will be queried.

  Returns:
    The ApplicationStatus object. Or None if not found.
  """
  read_mask = 'resources.{}'.format(resource_name) if resource_name else None
  module = client.MESSAGES_MODULE
  request = module.RunappsProjectsLocationsApplicationsGetStatusRequest(
      name=app_ref.RelativeName(), readMask=read_mask)
  try:
    return client.projects_locations_applications.GetStatus(request)
  except apitools_exceptions.HttpForbiddenError as e:
    _HandleLocationError(e)
  except apitools_exceptions.HttpNotFoundError:
    return None


def CreateApplication(client, app_ref, application):
  """Calls ApplicationCreate API of Runapps of the specified reference.

  Args:
    client: GAPIC API client, the api client to use.
    app_ref: googlecloudsdk.core.resources.Resource, the resource reference of
      the application.
    application: run_apps.v1alpha1.Application, the application to create

  Returns:
    run_apps.v1alpha1.Operation, the LRO of this request.
  """
  return client.projects_locations_applications.Create(
      client.MESSAGES_MODULE.RunappsProjectsLocationsApplicationsCreateRequest(
          application=application,
          applicationId=application.name,
          parent=app_ref.Parent().RelativeName()))


def PatchApplication(client, app_ref, application, update_mask=None):
  """Calls ApplicationPatch API of Runapps of the specified reference.

  Args:
    client: GAPIC API client, the api client to use.
    app_ref: googlecloudsdk.core.resources.Resource, the resource reference of
      the application.
    application: run_apps.v1alpha1.Application, the application to patch
    update_mask: str, comma separated string listing the fields to be updated.

  Returns:
    run_apps.v1alpha1.Operation, the LRO of this request.
  """
  return client.projects_locations_applications.Patch(
      client.MESSAGES_MODULE.RunappsProjectsLocationsApplicationsPatchRequest(
          application=application,
          updateMask=update_mask,
          name=app_ref.RelativeName()))


def CreateDeployment(client, app_ref, deployment, validate_only=False):
  """Calls ApplicationDeploymentCreate API of Runapps.

  Args:
    client: GAPIC API client, the api client to use.
    app_ref: googlecloudsdk.core.resources.Resource, the resource reference of
      the application the deployment belongs to
    deployment: run_apps.v1alpha1.Deployment, the deployment object
    validate_only: bool, whether to only validate the deployment

  Returns:
    run_apps.v1alpha1.Operation, the LRO of this request.
  """
  return client.projects_locations_applications_deployments.Create(
      client.MESSAGES_MODULE
      .RunappsProjectsLocationsApplicationsDeploymentsCreateRequest(
          parent=app_ref.RelativeName(),
          deployment=deployment,
          deploymentId=deployment.name,
          validateOnly=validate_only)
      )


def GetDeployment(client, deployment_name):
  """Calls GetDeployment API of Runapps.

  Args:
    client: GAPIC API client, the api client to use.
    deployment_name: str, the canonical name of the deployment.  For example:
      projects/<project>/locations/<location>/applications/<app>/deployment/<id>

  Returns:
    run_apps.v1alpha1.Deployment, the Deployment object.  None is returned if
      the deployment cannot be found.
  """
  try:
    return client.projects_locations_applications_deployments.Get(
        client.MESSAGES_MODULE
        .RunappsProjectsLocationsApplicationsDeploymentsGetRequest(
            name=deployment_name)
        )
  except apitools_exceptions.HttpNotFoundError:
    return None


def WaitForApplicationOperation(client, operation):
  """Waits for an operation to complete.

  Args:
    client:  GAPIC API client, client used to make requests.
    operation: run_apps.v1alpha1.operation object to wait for.

  Returns:
    run_apps.v1alpha1.application, from operation.
  """

  return _WaitForOperation(client, operation,
                           client.projects_locations_applications)


def WaitForDeploymentOperation(client, operation, tracker, tracker_update_func):
  """Waits for an operation to complete.

  Args:
    client:  GAPIC API client, client used to make requests.
    operation: run_apps.v1alpha1.operation, object to wait for.
    tracker: The ProgressTracker that tracks the operation progress.
    tracker_update_func: function to update the tracker on polling.

  Returns:
    run_apps.v1alpha1.Deployment, from operation.
  """

  return _WaitForOperation(client, operation,
                           client.projects_locations_applications_deployments,
                           tracker, tracker_update_func)


def _WaitForOperation(client,
                      operation,
                      resource_type,
                      tracker=None,
                      tracker_update_func=None):
  """Waits for an operation to complete.

  Args:
    client:  GAPIC API client, client used to make requests.
    operation: run_apps.v1alpha1.operation, object to wait for.
    resource_type: type, the expected type of resource response
    tracker: The ProgressTracker that tracks the operation progress.
    tracker_update_func: function to update the tracker on polling.

  Returns:
    The resulting resource of input paramater resource_type.
  """
  poller = waiter.CloudOperationPoller(resource_type,
                                       client.projects_locations_operations)
  operation_ref = resources.REGISTRY.ParseRelativeName(
      operation.name,
      collection='{}.projects.locations.operations'.format(API_NAME))

  def _StatusUpdate(result, status):
    if tracker is None:
      return
    if tracker_update_func:
      tracker_update_func(tracker, result, status)
    else:
      tracker.Tick()

  try:
    return poller.GetResult(
        waiter.PollUntilDone(
            poller,
            operation_ref,
            max_wait_ms=_POLLING_TIMEOUT_MS,
            wait_ceiling_ms=_RETRY_TIMEOUT_MS,
            status_update=_StatusUpdate))
  except waiter.OperationError:
    operation = poller.Poll(operation_ref)
    raise exceptions.IntegrationsOperationError(
        'OperationError: code={0}, message={1}'.format(
            operation.error.code, encoding.Decode(operation.error.message)))
  except retry.WaitException:
    # Operation timed out.
    raise waiter.TimeoutError(
        'Operation timed out after {0} seconds. The operations may still '
        'be underway remotely and may still succeed.'
        .format(_POLLING_TIMEOUT_MS / 1000))


def GetDeploymentOperationMetadata(messages, operation):
  """Get the metadata message for the deployment operation.

  Args:
    messages: Module containing the definitions of messages for the Runapps
      API.
    operation: runapps.v1alpha1.operation.

  Returns:
    The DeploymentOperationMetadata object.
  """

  return apitools_encoding.PyValueToMessage(
      messages.DeploymentOperationMetadata,
      apitools_encoding.MessageToPyValue(operation.metadata))


def _HandleLocationError(error):
  """Get the metadata message for the deployment operation.

  Args:
    error: The original HttpError.

  Raises:
    UnsupportedIntegrationsLocationError if it's location error. Otherwise
    raise the original error.
  """
  parsed_err = api_lib_exceptions.HttpException(error)
  if _LOCATION_ERROR_REGEX.match(parsed_err.payload.status_message):
    raise exceptions.UnsupportedIntegrationsLocationError(
        'Currently, this feature is only available in region us-central1.')
  raise error
