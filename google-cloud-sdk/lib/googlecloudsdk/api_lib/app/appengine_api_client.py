# Copyright 2015 Google Inc. All Rights Reserved.
"""Functions for creating a client to talk to the App Engine Admin API."""

import json

from googlecloudsdk.api_lib.app.api import operations
from googlecloudsdk.api_lib.app.api import requests
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apis.appengine.v1beta4 import appengine_v1beta4_client as v1beta4_client
from googlecloudsdk.third_party.apitools.base.py import encoding
from googlecloudsdk.third_party.appengine.admin.tools.conversion import yaml_schema

import yaml

KNOWN_APIS = {'v1beta4': v1beta4_client.AppengineV1beta4}


class AppengineApiClient(object):
  """Client used by gcloud to communicate with the App Engine API."""

  def __init__(self, client, api_version):
    self.client = client
    self.api_version = api_version
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

  def DeployModule(
      self, module_name, version_id, module_config, manifest, image):
    """Updates and deploys new app versions based on given config.

    Args:
      module_name: str, The module to deploy.
      version_id: str, The version of the module to deploy.
      module_config: AppInfoExternal, Module info parsed from a module yaml
        file.
      manifest: Dictionary mapping source files to Google Cloud Storage
        locations.
      image: The name of the container image.
    Returns:
      A Version resource representing the deployed version.
    """
    version_resource = self._CreateVersionResource(module_config, manifest,
                                                   version_id, image)
    create_request = self.messages.AppengineAppsModulesVersionsCreateRequest(
        name=self._FormatModule(app_id=self.project, module_name=module_name),
        version=version_resource)

    operation = requests.MakeRequest(
        self.client.apps_modules_versions.Create, create_request)

    log.debug('Received operation: [{operation}]'.format(
        operation=operation.name))

    return operations.WaitForOperation(self.client.apps_operations, operation)

  def SetDefaultVersion(self, module_name, version_id):
    """Sets the default serving version of the given modules.

    Args:
      module_name: str, The module name
      version_id: str, The version to set as default.
    """
    # Create a traffic split where 100% of traffic goes to the specified
    # version.
    allocations = {version_id: 1.0}
    traffic_split = encoding.PyValueToMessage(self.messages.TrafficSplit,
                                              {'allocations': allocations})

    update_module_request = self.messages.AppengineAppsModulesPatchRequest(
        name=self._FormatModule(app_id=self.project, module_name=module_name),
        module=self.messages.Module(split=traffic_split),
        mask='split')

    # TODO(clouser) Convert this to poll a long running operation.
    requests.MakeRequest(self.client.apps_modules.Patch, update_module_request)

  def DeleteVersion(self, module_name, version_id):
    """Deletes the specified version of the given module.

    Args:
      module_name: str, The module name
      version_id: str, The version to set as default.

    Returns:
      A Version resource representing the deleted version.
    """
    delete_request = self.messages.AppengineAppsModulesVersionsDeleteRequest(
        name=self._FormatVersion(app_id=self.project,
                                 module_name=module_name,
                                 version_id=version_id))
    operation = requests.MakeRequest(
        self.client.apps_modules_versions.Delete,
        delete_request)
    return operations.WaitForOperation(self.client.apps_operations, operation)

  def _CreateVersionResource(self, module_config, manifest, version_id, image):
    """Constructs a Version resource for deployment."""
    appinfo = module_config.parsed
    # TODO(bryanmau): Two Steps
    # 1. Once Zeus supports service, flip this to write module into service
    #    and warn the user that module is deprecated
    # 2. Once we want to stop supporting module, take this code out
    if appinfo.service:
      appinfo.module = appinfo.service
      appinfo.service = None

    parsed_yaml = module_config.parsed.ToYAML()
    config_dict = yaml.safe_load(parsed_yaml)
    try:
      json_version_resource = yaml_schema.SCHEMA.ConvertValue(config_dict)
    except ValueError, e:
      raise exceptions.ToolException.FromCurrent(
          ('[{f}] could not be converted to the App Engine configuration '
           'format for the following reason: {msg}').format(
               f=module_config.file, msg=e.message))
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

  def _FormatApp(self, app_id):
    return 'apps/{app_id}'.format(app_id=app_id)

  def _FormatModule(self, app_id, module_name):
    return 'apps/{app_id}/modules/{module_name}'.format(app_id=app_id,
                                                        module_name=module_name)

  def _FormatVersion(self, app_id, module_name, version_id):
    return 'apps/{app_id}/modules/{module_name}/versions/{version_id}'.format(
        app_id=app_id, module_name=module_name, version_id=version_id)


def GetApiClient(http, default_version='v1beta4'):
  """Initializes an AppengineApiClient using the specified API version.

  Uses the api_client_overrides/appengine property to determine which client
  version to use. Additionally uses the api_endpoint_overrides/appengine
  property to determine the server endpoint for the App Engine API.

  Args:
    http: The http transport to use.
    default_version: Default client version to use if the
      api_client_overrides/appengine property was not set.

  Returns:
    An AppengineApiClient used by gcloud to communicate with the App Engine API.

  Raises:
    ValueError: If default_version does not correspond to a supported version of
      the API.
  """
  api_version = properties.VALUES.api_client_overrides.appengine.Get()
  if not api_version:
    api_version = default_version

  client = KNOWN_APIS.get(api_version)
  if not client:
    raise ValueError('Invalid API version: [{0}]'.format(api_version))

  endpoint_override = properties.VALUES.api_endpoint_overrides.appengine.Get()
  appengine_client = client(url=endpoint_override, get_credentials=False,
                            http=http)

  return AppengineApiClient(appengine_client, api_version)
