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

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.apitools.base import py as apitools_base


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

  # Create a local ./endpoints directory which will contain the service.json
  # file needed by ESP. This file+directory will be carried to the Managed VM
  # via the app container.
  # TODO(user): Remove this when ESP is able to pull this configuration
  # directly from Inception.
  endpoints_dir = 'endpoints'
  if not os.path.exists(endpoints_dir):
    os.makedirs(endpoints_dir)
  with open(endpoints_dir + '/service.json', 'w') as out:
    out.write(apitools_base.encoding.MessageToJson(response.serviceConfig))

  # Second, upload Google Service Configuration to Service Management API
  managed_service = messages.ManagedService(
      serviceConfig=response.serviceConfig,
      serviceName=response.serviceConfig.name)
  # Set the serviceConfig producerProjectId
  managed_service.serviceConfig.producerProjectId = project

  request = messages.ServicemanagementServicesUpdateRequest(
      serviceName=managed_service.serviceName,
      managedService=managed_service,
  )
  try:
    client.services.Update(request)
    # TODO(b/27295262): wait here until the asynchronous operation in the
    # response has finished.
  except apitools_base.exceptions.HttpError as error:
    raise SwaggerUploadException(_GetErrorMessage(error))

  # Next, enable the service for the producer project
  usage_settings = messages.UsageSettings(
      consumerEnableStatus=
      messages.UsageSettings.ConsumerEnableStatusValueValuesEnum.ENABLED
  )
  project_settings = messages.ProjectSettings(usageSettings=usage_settings)
  request = messages.ServicemanagementServicesProjectSettingsPatchRequest(
      serviceName=managed_service.serviceName,
      consumerProjectId=project,
      projectSettings=project_settings,
      updateMask='usage_settings.consumer_enable_status'
  )
  try:
    client.services_projectSettings.Patch(request)
    # TODO(b/27295262): wait here until the asynchronous operation in the
    # response has finished.
  except apitools_base.exceptions.HttpError as error:
    raise SwaggerUploadException(_GetErrorMessage(error))
