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
"""Functions for creating a client to talk to the App Engine Admin API."""

import json

from apitools.base.py import encoding
from googlecloudsdk.api_lib.app import instances_util
from googlecloudsdk.api_lib.app import service_util
from googlecloudsdk.api_lib.app import version_util
from googlecloudsdk.api_lib.app.api import operations
from googlecloudsdk.api_lib.app.api import requests
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import apis as core_apis
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.appengine.admin.tools.conversion import yaml_schema_v1beta

import yaml


class AppengineApiClient(object):
  """Client used by gcloud to communicate with the App Engine API."""

  def __init__(self, client):
    self.client = client
    self.project = properties.VALUES.core.project.Get(required=True)

  @property
  def messages(self):
    return self.client.MESSAGES_MODULE

  def GetApplicationCodeBucket(self):
    """Retrieves the default code bucket associated with the application."""
    request = self.messages.AppengineAppsGetRequest(
        name=self._FormatApp(app_id=self.project),
        ensureResourcesExist=True)

    try:
      application = requests.MakeRequest(self.client.apps.Get, request)
    except exceptions.HttpException, e:
      log.error(e)
      return ''

    if application.codeBucket:
      return 'gs://{0}/'.format(application.codeBucket)
    else:
      return ''

  def DeployService(
      self, service_name, version_id, service_config, manifest, image):
    """Updates and deploys new app versions based on given config.

    Args:
      service_name: str, The service to deploy.
      version_id: str, The version of the service to deploy.
      service_config: AppInfoExternal, Service info parsed from a service yaml
        file.
      manifest: Dictionary mapping source files to Google Cloud Storage
        locations.
      image: The name of the container image.
    Returns:
      A Version resource representing the deployed version.
    """
    version_resource = self._CreateVersionResource(service_config, manifest,
                                                   version_id, image)
    create_request = self.messages.AppengineAppsServicesVersionsCreateRequest(
        name=self._FormatService(app_id=self.project,
                                 service_name=service_name),
        version=version_resource)

    operation = requests.MakeRequest(
        self.client.apps_services_versions.Create, create_request)

    log.debug('Received operation: [{operation}]'.format(
        operation=operation.name))

    return operations.WaitForOperation(self.client.apps_operations, operation)

  def SetDefaultVersion(self, service_name, version_id):
    """Sets the default serving version of the given services.

    Args:
      service_name: str, The service name
      version_id: str, The version to set as default.
    Returns:
      Long running operation.
    """
    # Create a traffic split where 100% of traffic goes to the specified
    # version.
    allocations = {version_id: 1.0}
    return self.SetTrafficSplit(service_name, allocations)

  def SetTrafficSplit(self, service_name, allocations,
                      shard_by='UNSPECIFIED', migrate=False):
    """Sets the traffic split of the given services.

    Args:
      service_name: str, The service name
      allocations: A dict mapping version ID to traffic split.
      shard_by: A ShardByValuesEnum value specifying how to shard the traffic.
      migrate: Whether or not to migrate traffic.
    Returns:
      Long running operation.
    """
    # Create a traffic split where 100% of traffic goes to the specified
    # version.
    traffic_split = encoding.PyValueToMessage(self.messages.TrafficSplit,
                                              {'allocations': allocations,
                                               'shardBy': shard_by})
    update_service_request = self.messages.AppengineAppsServicesPatchRequest(
        name=self._FormatService(app_id=self.project,
                                 service_name=service_name),
        service=self.messages.Service(split=traffic_split),
        migrateTraffic=migrate,
        mask='split')

    operation = requests.MakeRequest(
        self.client.apps_services.Patch,
        update_service_request)
    return operations.WaitForOperation(self.client.apps_operations, operation)

  def DeleteVersion(self, service_name, version_id):
    """Deletes the specified version of the given service.

    Args:
      service_name: str, The service name
      version_id: str, The version to delete.

    Returns:
      The completed Operation.
    """
    delete_request = self.messages.AppengineAppsServicesVersionsDeleteRequest(
        name=self._FormatVersion(app_id=self.project,
                                 service_name=service_name,
                                 version_id=version_id))
    operation = requests.MakeRequest(
        self.client.apps_services_versions.Delete,
        delete_request)
    return operations.WaitForOperation(self.client.apps_operations, operation)

  def SetServingStatus(self, service_name, version_id, serving_status):
    """Sets the serving status of the specified version.

    Args:
      service_name: str, The service name
      version_id: str, The version to delete.
      serving_status: The serving status to set.

    Returns:
      The completed Operation.
    """
    patch_request = self.messages.AppengineAppsServicesVersionsPatchRequest(
        name=self._FormatVersion(app_id=self.project,
                                 service_name=service_name,
                                 version_id=version_id),
        version=self.messages.Version(servingStatus=serving_status),
        mask='servingStatus')
    operation = requests.MakeRequest(
        self.client.apps_services_versions.Patch,
        patch_request)
    return operations.WaitForOperation(self.client.apps_operations, operation)

  def ListInstances(self, versions):
    """Lists all instances for the given versions.

    Args:
      versions: list of version_util.Version

    Returns:
      list of instances_util.Instance for the given versions
    """
    instances = []
    for version in versions:
      list_req = (
          self.messages.AppengineAppsServicesVersionsInstancesListRequest(
              name=self._FormatVersion(self.project, version.service,
                                       version.id)))
      instances += map(instances_util.Instance.FromInstanceResource,
                       requests.MakeRequest(
                           self.client.apps_services_versions_instances.List,
                           list_req).instances)
    return instances

  def GetAllInstances(self, service=None, version=None):
    """List all instances, optionally filtering by service or version.

    Args:
      service: str, the ID of the service to filter by.
      version: str, the ID of the service to filter by.

    Returns:
      list of instance_util.Instance
    """
    services = self.ListServices()
    log.debug('All services: {0}'.format(services))
    services = service_util.GetMatchingServices(
        services, [service] if service else None)

    versions = self.ListVersions(services)
    log.debug('Versions: {0}'.format(map(str, versions)))
    versions = version_util.GetMatchingVersions(
        versions, [version] if version else None, service)

    return self.ListInstances(versions)

  def StopVersion(self, service_name, version_id):
    """Stops the specified version.

    Args:
      service_name: str, The service name
      version_id: str, The version to stop.

    Returns:
      The completed Operation.
    """
    return self.SetServingStatus(
        service_name,
        version_id,
        self.messages.Version.ServingStatusValueValuesEnum.STOPPED)

  def StartVersion(self, service_name, version_id):
    """Starts the specified version.

    Args:
      service_name: str, The service name
      version_id: str, The version to start.

    Returns:
      The completed Operation.
    """
    return self.SetServingStatus(
        service_name,
        version_id,
        self.messages.Version.ServingStatusValueValuesEnum.SERVING)

  def ListServices(self):
    """Lists all services for the given application.

    Returns:
      A list of service_util.Service objects.
    """
    request = self.messages.AppengineAppsServicesListRequest(
        name=self._FormatApp(self.project))
    response = requests.MakeRequest(self.client.apps_services.List, request)

    services = []
    for s in response.services:
      traffic_split = {}
      if s.split:
        for split in s.split.allocations.additionalProperties:
          traffic_split[split.key] = split.value
      service = service_util.Service(self.project, s.id, traffic_split)
      services.append(service)

    return services

  def GetVersionResource(self, service, version):
    """Describe the given version of the given service.

    Args:
      service: str, the ID of the service for the version to describe
      version: str, the ID of the version to describe

    Returns:
      Version resource object from the API
    """
    request = self.messages.AppengineAppsServicesVersionsGetRequest(
        name=self._FormatVersion(self.project, service, version))
    return requests.MakeRequest(self.client.apps_services_versions.Get, request)

  def ListVersions(self, services):
    """Lists all versions for the specified services.

    Args:
      services: A list of service_util.Service objects.
    Returns:
      A list of version_util.Version objects.
    """
    versions = []
    for service in services:
      # Get the versions.
      request = self.messages.AppengineAppsServicesVersionsListRequest(
          name=self._FormatService(self.project, service.id))
      response = requests.MakeRequest(
          self.client.apps_services_versions.List, request)

      for v in response.versions:
        versions.append(version_util.Version.FromVersionResource(v, service))

    return versions

  def DeleteService(self, service_name):
    """Deletes the specified service.

    Args:
      service_name: str, Name of the service to delete.

    Returns:
      The completed Operation.
    """
    delete_request = self.messages.AppengineAppsServicesDeleteRequest(
        name=self._FormatService(app_id=self.project,
                                 service_name=service_name))
    operation = requests.MakeRequest(
        self.client.apps_services.Delete,
        delete_request)
    return operations.WaitForOperation(self.client.apps_operations, operation)

  def _CreateVersionResource(self, service_config, manifest, version_id, image):
    """Constructs a Version resource for deployment."""
    appinfo = service_config.parsed
    # TODO(b/29453752): Remove when we want to stop supporting module
    if appinfo.module:
      appinfo.service = appinfo.module
      appinfo.module = None

    parsed_yaml = service_config.parsed.ToYAML()
    config_dict = yaml.safe_load(parsed_yaml)
    try:
      json_version_resource = yaml_schema_v1beta.SCHEMA.ConvertValue(
          config_dict)
    except ValueError, e:
      raise exceptions.ToolException.FromCurrent(
          ('[{f}] could not be converted to the App Engine configuration '
           'format for the following reason: {msg}').format(
               f=service_config.file, msg=e.message))
    log.debug('Converted YAML to JSON: "{0}"'.format(
        json.dumps(json_version_resource, indent=2, sort_keys=True)))

    json_version_resource['deployment'] = {}
    # Add the deployment manifest information.
    json_version_resource['deployment']['files'] = manifest
    if image:
      json_version_resource['deployment']['container'] = {'image': image}
    version_resource = encoding.PyValueToMessage(self.messages.Version,
                                                 json_version_resource)

    # Add an ID for the version which is to be created.
    version_resource.id = version_id
    return version_resource

  # TODO(b/24562881): Once the API is updated, convert to use resource parser.
  def _FormatApp(self, app_id):
    return 'apps/{app_id}'.format(app_id=app_id)

  def _FormatService(self, app_id, service_name):
    return 'apps/{app_id}/services/{service_name}'.format(
        app_id=app_id, service_name=service_name)

  def _FormatVersion(self, app_id, service_name, version_id):
    return 'apps/{app_id}/services/{service_name}/versions/{version_id}'.format(
        app_id=app_id, service_name=service_name, version_id=version_id)


def GetApiClient():
  """Initializes an AppengineApiClient using the specified API version.

  Uses the api_client_overrides/appengine property to determine which client
  version to use. Additionally uses the api_endpoint_overrides/appengine
  property to determine the server endpoint for the App Engine API.

  Returns:
    An AppengineApiClient used by gcloud to communicate with the App Engine API.

  Raises:
    ValueError: If default_version does not correspond to a supported version of
      the API.
  """
  return AppengineApiClient(core_apis.GetClientInstance('appengine', 'v1beta5'))
