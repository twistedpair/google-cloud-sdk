# Copyright 2017 Google Inc. All Rights Reserved.
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

import itertools
import json
import operator

from apitools.base.py import encoding
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.app import exceptions
from googlecloudsdk.api_lib.app import instances_util
from googlecloudsdk.api_lib.app import operations_util
from googlecloudsdk.api_lib.app import region_util
from googlecloudsdk.api_lib.app import service_util
from googlecloudsdk.api_lib.app import version_util
from googlecloudsdk.api_lib.app.api import appengine_api_client_base
from googlecloudsdk.api_lib.app.api import requests
from googlecloudsdk.core import log
from googlecloudsdk.third_party.appengine.admin.tools.conversion import convert_yaml

import yaml


class AppengineApiClient(appengine_api_client_base.AppengineApiClientBase):
  """Client used by gcloud to communicate with the App Engine API."""

  def GetApplication(self):
    """Retrieves the application resource.

    Returns:
      An app resource representing the project's app.

    Raises:
      googlecloudsdk.api_lib.app.exceptions.NotFoundError if app doesn't exist
    """
    request = self.messages.AppengineAppsGetRequest(
        name=self._FormatApp())
    return requests.MakeRequest(self.client.apps.Get, request)

  def IsStopped(self, app):
    """Checks application resource to get serving status.

    Args:
      app: appengine_v1_messages.Application, the application to check.

    Returns:
      bool, whether the application is currently disabled. If serving or not
        set, returns False.
    """
    stopped = app.servingStatus in [
        self.messages.Application.ServingStatusValueValuesEnum.USER_DISABLED,
        self.messages.Application.ServingStatusValueValuesEnum.SYSTEM_DISABLED]
    return stopped

  def RepairApplication(self, progress_message=None):
    """Creates missing app resources.

    In particular, the Application.code_bucket GCS reference.

    Args:
      progress_message: str, the message to use while the operation is polled,
        if not the default.

    Returns:
      A long running operation.
    """
    request = self.messages.AppengineAppsRepairRequest(
        name=self._FormatApp(),
        repairApplicationRequest=self.messages.RepairApplicationRequest())

    operation = requests.MakeRequest(self.client.apps.Repair, request)

    log.debug('Received operation: [{operation}]'.format(
        operation=operation.name))

    return operations_util.WaitForOperation(
        self.client.apps_operations, operation, message=progress_message)

  def CreateApp(self, location):
    """Creates an App Engine app within the current cloud project.

    Creates a new singleton app within the currently selected Cloud Project.
    The action is one-time and irreversible.

    Args:
      location: str, The location (region) of the app, i.e. "us-central"

    Raises:
      googlecloudsdk.api_lib.app.exceptions.ConflictError if app already exists

    Returns:
      A long running operation.
    """
    create_request = self.messages.Application(id=self.project,
                                               locationId=location)

    operation = requests.MakeRequest(
        self.client.apps.Create, create_request)

    log.debug('Received operation: [{operation}]'.format(
        operation=operation.name))

    message = ('Creating App Engine application in project [{project}] and '
               'region [{region}].'.format(project=self.project,
                                           region=location))
    return operations_util.WaitForOperation(self.client.apps_operations,
                                            operation, message=message)

  def DeployService(
      self, service_name, version_id, service_config, manifest, image,
      endpoints_info=None):
    """Updates and deploys new app versions based on given config.

    Args:
      service_name: str, The service to deploy.
      version_id: str, The version of the service to deploy.
      service_config: AppInfoExternal, Service info parsed from a service yaml
        file.
      manifest: Dictionary mapping source files to Google Cloud Storage
        locations.
      image: The name of the container image.
      endpoints_info: EndpointsServiceInfo, Endpoints service info to be added
        to the AppInfoExternal configuration. Only provided when Endpoints API
        Management feature is enabled.
    Returns:
      A Version resource representing the deployed version.
    """
    version_resource = self._CreateVersionResource(
        service_config, manifest, version_id, image, endpoints_info)
    create_request = self.messages.AppengineAppsServicesVersionsCreateRequest(
        parent=self._GetServiceRelativeName(service_name=service_name),
        version=version_resource)

    operation = requests.MakeRequest(
        self.client.apps_services_versions.Create, create_request)

    log.debug('Received operation: [{operation}]'.format(
        operation=operation.name))

    message = 'Updating service [{service}]'.format(service=service_name)

    return operations_util.WaitForOperation(self.client.apps_operations,
                                            operation,
                                            message=message)

  def GetServiceResource(self, service):
    """Describe the given service.

    Args:
      service: str, the ID of the service

    Returns:
      Service resource object from the API
    """
    request = self.messages.AppengineAppsServicesGetRequest(
        name=self._GetServiceRelativeName(service))
    return requests.MakeRequest(
        self.client.apps_services.Get, request)

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
        name=self._GetServiceRelativeName(service_name=service_name),
        service=self.messages.Service(split=traffic_split),
        migrateTraffic=migrate,
        updateMask='split')

    operation = requests.MakeRequest(
        self.client.apps_services.Patch,
        update_service_request)
    return operations_util.WaitForOperation(self.client.apps_operations,
                                            operation)

  def DeleteVersion(self, service_name, version_id):
    """Deletes the specified version of the given service.

    Args:
      service_name: str, The service name
      version_id: str, The version to delete.

    Returns:
      The completed Operation.
    """
    delete_request = self.messages.AppengineAppsServicesVersionsDeleteRequest(
        name=self._FormatVersion(service_name=service_name,
                                 version_id=version_id))
    operation = requests.MakeRequest(
        self.client.apps_services_versions.Delete,
        delete_request)
    message = 'Deleting [{0}/{1}]'.format(service_name, version_id)
    return operations_util.WaitForOperation(
        self.client.apps_operations, operation, message=message)

  def SetServingStatus(self, service_name, version_id, serving_status,
                       block=True):
    """Sets the serving status of the specified version.

    Args:
      service_name: str, The service name
      version_id: str, The version to delete.
      serving_status: The serving status to set.
      block: bool, whether to block on the completion of the operation

    Returns:
      The completed Operation if block is True, or the Operation to wait on
      otherwise.
    """
    patch_request = self.messages.AppengineAppsServicesVersionsPatchRequest(
        name=self._FormatVersion(service_name=service_name,
                                 version_id=version_id),
        version=self.messages.Version(servingStatus=serving_status),
        updateMask='servingStatus')
    operation = requests.MakeRequest(
        self.client.apps_services_versions.Patch,
        patch_request)
    if block:
      return operations_util.WaitForOperation(self.client.apps_operations,
                                              operation)
    else:
      return operation

  def ListInstances(self, versions):
    """Produces a generator of all instances for the given versions.

    Args:
      versions: list of version_util.Version

    Returns:
      A generator of each instances_util.Instance for the given versions
    """
    iters = []
    for version in versions:
      request = self.messages.AppengineAppsServicesVersionsInstancesListRequest(
          parent=self._FormatVersion(version.service, version.id))
      iters.append(list_pager.YieldFromList(
          self.client.apps_services_versions_instances,
          request,
          field='instances',
          batch_size=100,  # Set batch size so tests can expect it.
          batch_size_attribute='pageSize'))
    return (instances_util.Instance.FromInstanceResource(i)
            for i in itertools.chain.from_iterable(iters))

  def GetAllInstances(self, service=None, version=None, version_filter=None):
    """Generator of all instances, optionally filtering by service or version.

    Args:
      service: str, the ID of the service to filter by.
      version: str, the ID of the version to filter by.
      version_filter: filter function accepting version_util.Version

    Returns:
      generator of instance_util.Instance
    """
    services = self.ListServices()
    log.debug('All services: {0}'.format(services))
    services = service_util.GetMatchingServices(
        services, [service] if service else None)

    versions = self.ListVersions(services)
    log.debug('Versions: {0}'.format(map(str, versions)))
    versions = version_util.GetMatchingVersions(
        versions, [version] if version else None, service)
    versions = filter(version_filter, versions)

    return self.ListInstances(versions)

  def DebugInstance(self, res, ssh_key=None):
    """Enable debugging of a Flexible instance.

    Args:
      res: A googleclousdk.core.Resource object.
      ssh_key: str, Public SSH key to add to the instance. Examples:
        `[USERNAME]:ssh-rsa [KEY_VALUE] [USERNAME]` ,
        `[USERNAME]:ssh-rsa [KEY_VALUE] google-ssh {"userName":"[USERNAME]",`
        `"expireOn":"[EXPIRE_TIME]"}`
        For more information, see Adding and Removing SSH Keys
        (https://cloud.google.com/compute/docs/instances/adding-removing-ssh-
        keys).

    Returns:
      The completed Operation.
    """
    request = self.messages.AppengineAppsServicesVersionsInstancesDebugRequest(
        name=res.RelativeName(),
        debugInstanceRequest=self.messages.DebugInstanceRequest(sshKey=ssh_key))
    operation = requests.MakeRequest(
        self.client.apps_services_versions_instances.Debug, request)
    return operations_util.WaitForOperation(self.client.apps_operations,
                                            operation)

  def DeleteInstance(self, res):
    """Delete a Flexible instance.

    Args:
      res: A googlecloudsdk.core.Resource object.

    Returns:
      The completed Operation.
    """
    request = self.messages.AppengineAppsServicesVersionsInstancesDeleteRequest(
        name=res.RelativeName())
    operation = requests.MakeRequest(
        self.client.apps_services_versions_instances.Delete, request)
    return operations_util.WaitForOperation(self.client.apps_operations,
                                            operation)

  def GetInstanceResource(self, res):
    """Describe the given instance of the given version of the given service.

    Args:
      res: A googlecloudsdk.core.Resource object.

    Raises:
      googlecloudsdk.api_lib.app.exceptions.NotFoundError: If instance does not
        exist.

    Returns:
      Version resource object from the API
    """
    request = self.messages.AppengineAppsServicesVersionsInstancesGetRequest(
        name=res.RelativeName())
    return requests.MakeRequest(
        self.client.apps_services_versions_instances.Get, request)

  def StopVersion(self, service_name, version_id, block=True):
    """Stops the specified version.

    Args:
      service_name: str, The service name
      version_id: str, The version to stop.
      block: bool, whether to block on the completion of the operation


    Returns:
      The completed Operation if block is True, or the Operation to wait on
      otherwise.
    """
    return self.SetServingStatus(
        service_name,
        version_id,
        self.messages.Version.ServingStatusValueValuesEnum.STOPPED,
        block)

  def StartVersion(self, service_name, version_id, block=True):
    """Starts the specified version.

    Args:
      service_name: str, The service name
      version_id: str, The version to start.
      block: bool, whether to block on the completion of the operation

    Returns:
      The completed Operation if block is True, or the Operation to wait on
      otherwise.
    """
    return self.SetServingStatus(
        service_name,
        version_id,
        self.messages.Version.ServingStatusValueValuesEnum.SERVING,
        block)

  def ListServices(self):
    """Lists all services for the given application.

    Returns:
      A list of service_util.Service objects.
    """
    request = self.messages.AppengineAppsServicesListRequest(
        parent=self._FormatApp())
    services = []
    for service in list_pager.YieldFromList(
        self.client.apps_services, request, field='services',
        batch_size=100, batch_size_attribute='pageSize'):
      traffic_split = {}
      if service.split:
        for split in service.split.allocations.additionalProperties:
          traffic_split[split.key] = split.value
      services.append(
          service_util.Service(self.project, service.id, traffic_split))
    return services

  def GetVersionResource(self, service, version):
    """Describe the given version of the given service.

    Args:
      service: str, the ID of the service for the version to describe.
      version: str, the ID of the version to describe.

    Returns:
      Version resource object from the API.
    """
    request = self.messages.AppengineAppsServicesVersionsGetRequest(
        name=self._FormatVersion(service, version),
        view=(self.messages.
              AppengineAppsServicesVersionsGetRequest.ViewValueValuesEnum.FULL))
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
          parent=self._GetServiceRelativeName(service.id))
      for version in list_pager.YieldFromList(
          self.client.apps_services_versions, request, field='versions',
          batch_size=100, batch_size_attribute='pageSize'):
        versions.append(
            version_util.Version.FromVersionResource(version, service))

    return versions

  def ListRegions(self):
    """List all regions and support for standard and flexible.

    Returns:
      List of region_util.Region instances.
    """
    request = self.messages.AppengineAppsLocationsListRequest(
        name='apps/-')
    regions = list_pager.YieldFromList(
        self.client.apps_locations, request, field='locations',
        batch_size=100, batch_size_attribute='pageSize')
    return [region_util.Region.FromRegionResource(loc) for loc in regions]

  def DeleteService(self, service_name):
    """Deletes the specified service.

    Args:
      service_name: str, Name of the service to delete.

    Returns:
      The completed Operation.
    """
    delete_request = self.messages.AppengineAppsServicesDeleteRequest(
        name=self._GetServiceRelativeName(service_name=service_name))
    operation = requests.MakeRequest(
        self.client.apps_services.Delete,
        delete_request)
    message = 'Deleting [{}]'.format(service_name)
    return operations_util.WaitForOperation(self.client.apps_operations,
                                            operation,
                                            message=message)

  def GetOperation(self, op_id):
    """Grabs details about a particular gcloud operation.

    Args:
      op_id: str, ID of operation.

    Returns:
      Operation resource object from API call.
    """
    request = self.messages.AppengineAppsOperationsGetRequest(
        name=self._FormatOperation(op_id))

    return requests.MakeRequest(self.client.apps_operations.Get, request)

  def ListOperations(self, op_filter=None):
    """Lists all operations for the given application.

    Args:
      op_filter: String to filter which operations to grab.

    Returns:
      A list of opeartion_util.Operation objects.
    """
    request = self.messages.AppengineAppsOperationsListRequest(
        name=self._FormatApp(),
        filter=op_filter)

    operations = list_pager.YieldFromList(
        self.client.apps_operations, request, field='operations',
        batch_size=100, batch_size_attribute='pageSize')
    return [operations_util.Operation(op) for op in operations]

  def _CreateVersionResource(
      self, service_config, manifest, version_id, image, endpoints_info):
    """Constructs a Version resource for deployment."""
    appinfo = service_config.parsed

    # TODO(b/29453752): Remove when we want to stop supporting module
    if appinfo.module:
      appinfo.service = appinfo.module
      appinfo.module = None

    parsed_yaml = service_config.parsed.ToYAML()
    config_dict = yaml.safe_load(parsed_yaml)
    try:
      # pylint: disable=protected-access
      schema_parser = convert_yaml.GetSchemaParser(self.client._VERSION)
      json_version_resource = schema_parser.ConvertValue(config_dict)
    except ValueError, e:
      raise exceptions.ConfigError(
          '[{f}] could not be converted to the App Engine configuration '
          'format for the following reason: {msg}'.format(
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

    # In the JSON representation, BetaSettings are a dict of key-value pairs.
    # In the Message representation, BetaSettings are an ordered array of
    # key-value pairs. Sort the key-value pairs here, so that unit testing is
    # possible.
    if 'betaSettings' in json_version_resource:
      json_dict = json_version_resource.get('betaSettings')
      # TODO(b/29993301): Move Endpoints settings up from beta_settings into a
      # top level configuration section of messages.Version
      if json_dict and endpoints_info:
        json_dict['endpoints_service_name'] = endpoints_info.service_name
        json_dict['endpoints_service_version'] = endpoints_info.service_version
      attributes = []
      for key, value in sorted(json_dict.iteritems()):
        attributes.append(
            self.messages.Version.BetaSettingsValue.AdditionalProperty(
                key=key, value=value))
      version_resource.betaSettings = self.messages.Version.BetaSettingsValue(
          additionalProperties=attributes)

    # The files in the deployment manifest also need to be sorted for unit
    # testing purposes.
    try:
      version_resource.deployment.files.additionalProperties.sort(
          key=operator.attrgetter('key'))
    except AttributeError:  # manifest not present, or no files in manifest
      pass

    # Add an ID for the version which is to be created.
    version_resource.id = version_id
    return version_resource


def GetApiClient():
  return AppengineApiClient.GetApiClient()
