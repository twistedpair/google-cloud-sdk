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
from googlecloudsdk.core import apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log


class EndpointsServiceInfo(object):
  """Container class for holding Endpoints service information."""

  def __init__(self, service_name, service_version):
    self.service_name = service_name
    self.service_version = service_version


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


def ProcessEndpointsService(service, project, client=None, messages=None):
  """Pushes service configs to the Endpoints handler.

  First, this method checks each service in the list of services to see
  whether it's to be handled by Cloud Endpoints. If so, it pushes the config.

  Args:
    service: ServiceYamlInfo, The service being deployed.
    project: The name of the GCP project.
    client: The Service Management API client to use.
    messages: The Service Management API messages module to use.

  Returns:
    EndpointsServiceInfo: an instance of EndpointsServiceInfo that contains the
      Endpoints service name and service version that is processed.
  """
  # lazy load the API library and client to make unit testing feasible.
  if not client:
    client = apis.GetClientInstance('servicemanagement', 'v1')
  if not messages:
    messages = apis.GetMessagesModule('servicemanagement', 'v1')

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
      return PushServiceConfig(swagger_abs_path, project, client, messages)

  return None


def WriteServiceConfigToFile(file_path, contents):
  """Writes Service Config contents to a file on disk.

  Args:
    file_path: path to the file that is to be written to.
    contents: the contents to write to the file.

  Raises:
    SwaggerUploadException: if errors occur in creating the destination
        directory or writing to the file.
  """
  dir_path = os.path.dirname(file_path)
  if not os.path.isdir(dir_path):
    try:
      os.makedirs(dir_path)
    except (IOError, OSError) as e:
      raise SwaggerUploadException(
          'Failed to create directory {0} {1}'.format(dir_path, str(e)))
  try:
    with open(file_path, 'w') as out:
      out.write(contents)
  except (IOError, OSError) as e:
    raise SwaggerUploadException(
        'Failed to write Google Service Configuration '
        'file {0} to disk {1}'.format(file_path, str(e)))


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
    EndpointsServiceInfo: an instance of EndpointsServiceInfo that contains the
      Endpoints service name and service version that is pushed.
  """
  if not swagger_file:
    raise ValueError(
        'Open API (Swagger) specification file path must be provided.')
  if not project:
    raise ValueError('Project Id must be provided.')
  if not client:
    raise ValueError('Service Management client must be provided.')
  if not messages:
    raise ValueError('Service Management client messages must be provided.')

  swagger_file_contents = None
  try:
    with open(swagger_file) as f:
      swagger_file_contents = f.read()
  except IOError:
    raise SwaggerOpenException(
        'Unable to read swagger spec file "{0}"'.format(swagger_file))

  # Try to load the file as JSON or YAML.
  service_config_dict = services_util.LoadJsonOrYaml(swagger_file_contents)
  if not service_config_dict:
    raise SwaggerOpenException(
        'Could not read JSON or YAML from Open API (Swagger) file {}.'.format(
            swagger_file))

  # Check to see if the Endpoints meta service needs to be enabled.
  enable_api.EnableServiceIfDisabled(
      project, services_util.GetEndpointsServiceName(), async=False)

  # First, get the Open API specification contents, and convert it to
  # Google Service Config. This is only needed at the moment for the
  # Diagnostics information the ConvertConfig generates.
  # TODO(b/30276465): When the Diagnostics information is available via the
  # SubmitSourceConfig API, remove the usage of ConvertConfig API.
  swagger_file_obj = messages.File(
      contents=swagger_file_contents, path=swagger_file)
  swagger_spec = messages.SwaggerSpec(swaggerFiles=[swagger_file_obj])
  request = messages.ConvertConfigRequest(swaggerSpec=swagger_spec)
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
  # TODO(b/28090287): Remove this when ESP is able to pull this configuration
  # directly from Service Management API.
  swagger_path = os.path.dirname(swagger_file)
  service_json_file = os.path.join(swagger_path, 'endpoints', 'service.json')
  WriteServiceConfigToFile(
      service_json_file,
      apitools_base.encoding.MessageToJson(response.serviceConfig))

  service_name = service_config_dict.get('host', None)
  # Create the Service resource if it does not already exist.
  services_util.CreateServiceIfNew(service_name, project)

  # Push the service configuration.
  config_id = services_util.PushOpenApiServiceConfig(
      service_name,
      swagger_file_contents,
      os.path.basename(swagger_file),
      async=False)

  if config_id and service_name:
    # Print this to screen and to the log because the output is needed by the
    # human user.
    log.status.Print(
        ('\nService Configuration with version [{0}] uploaded '
         'for service [{1}]\n').format(config_id, service_name))
  else:
    raise SwaggerUploadException(
        'Failed to retrieve Service Configuration Version')

  # Create a Rollout for the new service configuration
  percentages = messages.TrafficPercentStrategy.PercentagesValue()
  percentages.additionalProperties.append(
      messages.TrafficPercentStrategy.PercentagesValue.AdditionalProperty(
          key=config_id, value=100.0))
  traffic_percent_strategy = messages.TrafficPercentStrategy(
      percentages=percentages)
  rollout = messages.Rollout(
      serviceName=service_name,
      trafficPercentStrategy=traffic_percent_strategy,
  )
  rollout_operation = client.services_rollouts.Create(rollout)
  services_util.ProcessOperationResult(rollout_operation, async=False)

  # Enable the service for the producer project if it is not already enabled
  enable_api.EnableServiceIfDisabled(project, service_name, async=False)

  return EndpointsServiceInfo(
      service_name=service_name, service_version=config_id)
