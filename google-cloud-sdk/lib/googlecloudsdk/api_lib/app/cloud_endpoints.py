# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Utilities for interacting with Google Service Management."""

import json
import os.path

from apitools.base import py as apitools_base

from googlecloudsdk.api_lib.service_management import enable_api
from googlecloudsdk.api_lib.service_management import services_util
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log


class SwaggerOpenException(exceptions.Error):

  def __init__(self, message):
    super(SwaggerOpenException, self).__init__(message)


class SwaggerUploadException(exceptions.Error):

  def __init(self, message):
    super(SwaggerUploadException, self).__init__(message)


# TODO(b/26202997): Switch to using the GetHttpErrorMessage in core once
# b/26202997 is resolved.
def _GetErrorMessage(error):
  content_obj = json.loads(error.content)
  return content_obj.get('error', {}).get('message', '')


def ProcessEndpointsService(service, project):
  """Pushes service configs to the Endpoints handler.

  First, this method checks each service in the list of services to see
  whether it's to be handled by Cloud Endpoints. If so, it pushes the config.

  Args:
    service: ServiceYamlInfo, The service being deployed.
    project: The name of the GCP project.
  """
  if service and service.parsed and service.parsed.beta_settings:
    bs = service.parsed.beta_settings
    use_endpoints = bs.get('use_endpoints_api_management', '').lower()
    swagger_file = bs.get('endpoints_swagger_spec_file')
    if use_endpoints in ('true', '1', 'yes') and swagger_file:
      if os.path.isabs(swagger_file):
        swagger_abs_path = swagger_file
      else:
        swagger_abs_path = os.path.normpath(os.path.join(
            os.path.dirname(service.file), swagger_file))
      PushServiceConfig(
          swagger_abs_path,
          project,
          apis.GetClientInstance('servicemanagement', 'v1'),
          apis.GetMessagesModule('servicemanagement', 'v1'))


def PushServiceConfig(swagger_file, project, client, messages):
  """Pushes Service Configuration to Google Service Management.

  Args:
    swagger_file: full path to a JSON file containing the swagger spec.
    project: the Google cloud project Id
    client: the client to use for calls to Service Management API
    messages: the client library messages to use for Service Management API

  Raises:
    SwaggerOpenException: if input is malformed or file cannot be read
    SwaggerUploadException: if service fails to convert swagger, or
      upload of the service configuration conversion result fails
    ValueError: if the required inputs are not provided.

  Returns:
    Operation: a long running asynchronous Operation
  """
  if not swagger_file:
    raise ValueError('Swagger specification file path must be provided.')
  if not project:
    raise ValueError('Project Id must be provided.')
  if not client:
    raise ValueError('Service Management client must be provided.')
  if not messages:
    raise ValueError('Service Management client messages must be provided.')

  swagger_path = os.path.dirname(swagger_file)

  # First, convert the swagger specification to Google Service Configuration
  try:
    with open(swagger_file) as f:
      swagger_file = messages.File(
          contents=f.read(),
          path=swagger_file,
      )
  except IOError:
    raise SwaggerOpenException(
        'Unable to read swagger spec file "{0}"'.format(swagger_file))

  # Check to see if the Endpoints meta service needs to be enabled.
  enable_api.EnableServiceIfDisabled(
      project, services_util.GetEndpointsServiceName(), async=False)

  swagger_spec = messages.SwaggerSpec(swaggerFiles=[swagger_file])
  request = messages.ConvertConfigRequest(
      swaggerSpec=swagger_spec,
  )

  try:
    response = client.v1.ConvertConfig(request)
  except apitools_base.exceptions.HttpError as error:
    raise SwaggerUploadException(_GetErrorMessage(error))

  if response.diagnostics:
    kind = messages.Diagnostic.KindValueValuesEnum
    for diagnostic in response.diagnostics:
      logger = log.error if diagnostic.kind == kind.ERROR else log.warning
      logger('{l}: {m}'.format(l=diagnostic.location, m=diagnostic.message))

  if not response.serviceConfig:
    raise SwaggerUploadException('Failed to upload service configuration.')

  # Create an endpoints directory under the location of the swagger config
  # which will contain the service.json file needed by ESP.
  # This file+directory will be carried to the App Engine Flexible VM via the
  # app container.
  # TODO(user): Remove this when ESP is able to pull this configuration
  # directly from Inception.
  endpoints_dir = os.path.join(swagger_path, 'endpoints')
  if not os.path.exists(endpoints_dir):
    os.makedirs(endpoints_dir)
  with open(endpoints_dir + '/service.json', 'w') as out:
    out.write(apitools_base.encoding.MessageToJson(response.serviceConfig))

  # Second, upload Google Service Configuration to Service Management API
  service_name = response.serviceConfig.name
  managed_service = messages.ManagedService(
      serviceConfig=response.serviceConfig,
      serviceName=service_name)
  # Set the serviceConfig producerProjectId
  managed_service.serviceConfig.producerProjectId = project

  request = messages.ServicemanagementServicesUpdateRequest(
      serviceName=service_name,
      managedService=managed_service,
  )

  try:
    update_operation = client.services.Update(request)
  except apitools_base.exceptions.HttpError as error:
    raise SwaggerUploadException(_GetErrorMessage(error))

  # Wait on the operation to complete
  try:
    services_util.ProcessOperationResult(update_operation, async=False)
  except calliope_exceptions.ToolException:
    raise SwaggerUploadException('Failed to upload service configuration.')

  # Enable the service for the producer project if it is not already enabled
  enable_api.EnableServiceIfDisabled(project, service_name, async=False)
