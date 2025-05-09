"""Generated client library for appconfigmanager version v1alpha."""
# NOTE: This file is autogenerated and should not be edited by hand.

from __future__ import absolute_import

from apitools.base.py import base_api
from googlecloudsdk.generated_clients.apis.appconfigmanager.v1alpha import appconfigmanager_v1alpha_messages as messages


class AppconfigmanagerV1alpha(base_api.BaseApiClient):
  """Generated client library for service appconfigmanager version v1alpha."""

  MESSAGES_MODULE = messages
  BASE_URL = 'https://appconfigmanager.googleapis.com/'
  MTLS_BASE_URL = 'https://appconfigmanager.mtls.googleapis.com/'

  _PACKAGE = 'appconfigmanager'
  _SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
  _VERSION = 'v1alpha'
  _CLIENT_ID = 'CLIENT_ID'
  _CLIENT_SECRET = 'CLIENT_SECRET'
  _USER_AGENT = 'google-cloud-sdk'
  _CLIENT_CLASS_NAME = 'AppconfigmanagerV1alpha'
  _URL_VERSION = 'v1alpha'
  _API_KEY = None

  def __init__(self, url='', credentials=None,
               get_credentials=True, http=None, model=None,
               log_request=False, log_response=False,
               credentials_args=None, default_global_params=None,
               additional_http_headers=None, response_encoding=None):
    """Create a new appconfigmanager handle."""
    url = url or self.BASE_URL
    super(AppconfigmanagerV1alpha, self).__init__(
        url, credentials=credentials,
        get_credentials=get_credentials, http=http, model=model,
        log_request=log_request, log_response=log_response,
        credentials_args=credentials_args,
        default_global_params=default_global_params,
        additional_http_headers=additional_http_headers,
        response_encoding=response_encoding)
    self.projects_locations_configs_versionRenders = self.ProjectsLocationsConfigsVersionRendersService(self)
    self.projects_locations_configs_versions = self.ProjectsLocationsConfigsVersionsService(self)
    self.projects_locations_configs = self.ProjectsLocationsConfigsService(self)
    self.projects_locations = self.ProjectsLocationsService(self)
    self.projects = self.ProjectsService(self)

  class ProjectsLocationsConfigsVersionRendersService(base_api.BaseApiService):
    """Service class for the projects_locations_configs_versionRenders resource."""

    _NAME = 'projects_locations_configs_versionRenders'

    def __init__(self, client):
      super(AppconfigmanagerV1alpha.ProjectsLocationsConfigsVersionRendersService, self).__init__(client)
      self._upload_configs = {
          }

    def Get(self, request, global_params=None):
      r"""Gets details of a single ConfigVersionRender.

      Args:
        request: (AppconfigmanagerProjectsLocationsConfigsVersionRendersGetRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (ConfigVersionRender) The response message.
      """
      config = self.GetMethodConfig('Get')
      return self._RunMethod(
          config, request, global_params=global_params)

    Get.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}/configs/{configsId}/versionRenders/{versionRendersId}',
        http_method='GET',
        method_id='appconfigmanager.projects.locations.configs.versionRenders.get',
        ordered_params=['name'],
        path_params=['name'],
        query_params=['view'],
        relative_path='v1alpha/{+name}',
        request_field='',
        request_type_name='AppconfigmanagerProjectsLocationsConfigsVersionRendersGetRequest',
        response_type_name='ConfigVersionRender',
        supports_download=False,
    )

    def List(self, request, global_params=None):
      r"""Lists ConfigVersionRenders in a given project, location, and Config.

      Args:
        request: (AppconfigmanagerProjectsLocationsConfigsVersionRendersListRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (ListConfigVersionRendersResponse) The response message.
      """
      config = self.GetMethodConfig('List')
      return self._RunMethod(
          config, request, global_params=global_params)

    List.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}/configs/{configsId}/versionRenders',
        http_method='GET',
        method_id='appconfigmanager.projects.locations.configs.versionRenders.list',
        ordered_params=['parent'],
        path_params=['parent'],
        query_params=['filter', 'orderBy', 'pageSize', 'pageToken', 'view'],
        relative_path='v1alpha/{+parent}/versionRenders',
        request_field='',
        request_type_name='AppconfigmanagerProjectsLocationsConfigsVersionRendersListRequest',
        response_type_name='ListConfigVersionRendersResponse',
        supports_download=False,
    )

  class ProjectsLocationsConfigsVersionsService(base_api.BaseApiService):
    """Service class for the projects_locations_configs_versions resource."""

    _NAME = 'projects_locations_configs_versions'

    def __init__(self, client):
      super(AppconfigmanagerV1alpha.ProjectsLocationsConfigsVersionsService, self).__init__(client)
      self._upload_configs = {
          }

    def Create(self, request, global_params=None):
      r"""Creates a new ConfigVersion in a given project, location, and Config.

      Args:
        request: (AppconfigmanagerProjectsLocationsConfigsVersionsCreateRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (ConfigVersion) The response message.
      """
      config = self.GetMethodConfig('Create')
      return self._RunMethod(
          config, request, global_params=global_params)

    Create.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}/configs/{configsId}/versions',
        http_method='POST',
        method_id='appconfigmanager.projects.locations.configs.versions.create',
        ordered_params=['parent'],
        path_params=['parent'],
        query_params=['configVersionId', 'requestId'],
        relative_path='v1alpha/{+parent}/versions',
        request_field='configVersion',
        request_type_name='AppconfigmanagerProjectsLocationsConfigsVersionsCreateRequest',
        response_type_name='ConfigVersion',
        supports_download=False,
    )

    def Delete(self, request, global_params=None):
      r"""Deletes a single ConfigVersion.

      Args:
        request: (AppconfigmanagerProjectsLocationsConfigsVersionsDeleteRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (Empty) The response message.
      """
      config = self.GetMethodConfig('Delete')
      return self._RunMethod(
          config, request, global_params=global_params)

    Delete.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}/configs/{configsId}/versions/{versionsId}',
        http_method='DELETE',
        method_id='appconfigmanager.projects.locations.configs.versions.delete',
        ordered_params=['name'],
        path_params=['name'],
        query_params=['requestId'],
        relative_path='v1alpha/{+name}',
        request_field='',
        request_type_name='AppconfigmanagerProjectsLocationsConfigsVersionsDeleteRequest',
        response_type_name='Empty',
        supports_download=False,
    )

    def Get(self, request, global_params=None):
      r"""Gets details of a single ConfigVersion.

      Args:
        request: (AppconfigmanagerProjectsLocationsConfigsVersionsGetRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (ConfigVersion) The response message.
      """
      config = self.GetMethodConfig('Get')
      return self._RunMethod(
          config, request, global_params=global_params)

    Get.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}/configs/{configsId}/versions/{versionsId}',
        http_method='GET',
        method_id='appconfigmanager.projects.locations.configs.versions.get',
        ordered_params=['name'],
        path_params=['name'],
        query_params=['view'],
        relative_path='v1alpha/{+name}',
        request_field='',
        request_type_name='AppconfigmanagerProjectsLocationsConfigsVersionsGetRequest',
        response_type_name='ConfigVersion',
        supports_download=False,
    )

    def List(self, request, global_params=None):
      r"""Lists ConfigVersions in a given project, location, and Config.

      Args:
        request: (AppconfigmanagerProjectsLocationsConfigsVersionsListRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (ListConfigVersionsResponse) The response message.
      """
      config = self.GetMethodConfig('List')
      return self._RunMethod(
          config, request, global_params=global_params)

    List.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}/configs/{configsId}/versions',
        http_method='GET',
        method_id='appconfigmanager.projects.locations.configs.versions.list',
        ordered_params=['parent'],
        path_params=['parent'],
        query_params=['filter', 'orderBy', 'pageSize', 'pageToken', 'view'],
        relative_path='v1alpha/{+parent}/versions',
        request_field='',
        request_type_name='AppconfigmanagerProjectsLocationsConfigsVersionsListRequest',
        response_type_name='ListConfigVersionsResponse',
        supports_download=False,
    )

    def Patch(self, request, global_params=None):
      r"""Updates the parameters of a single ConfigVersion.

      Args:
        request: (AppconfigmanagerProjectsLocationsConfigsVersionsPatchRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (ConfigVersion) The response message.
      """
      config = self.GetMethodConfig('Patch')
      return self._RunMethod(
          config, request, global_params=global_params)

    Patch.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}/configs/{configsId}/versions/{versionsId}',
        http_method='PATCH',
        method_id='appconfigmanager.projects.locations.configs.versions.patch',
        ordered_params=['name'],
        path_params=['name'],
        query_params=['requestId', 'updateMask'],
        relative_path='v1alpha/{+name}',
        request_field='configVersion',
        request_type_name='AppconfigmanagerProjectsLocationsConfigsVersionsPatchRequest',
        response_type_name='ConfigVersion',
        supports_download=False,
    )

    def Render(self, request, global_params=None):
      r"""Gets rendered version of a Config Version.

      Args:
        request: (AppconfigmanagerProjectsLocationsConfigsVersionsRenderRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (RenderConfigVersionResponse) The response message.
      """
      config = self.GetMethodConfig('Render')
      return self._RunMethod(
          config, request, global_params=global_params)

    Render.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}/configs/{configsId}/versions/{versionsId}:render',
        http_method='GET',
        method_id='appconfigmanager.projects.locations.configs.versions.render',
        ordered_params=['name'],
        path_params=['name'],
        query_params=[],
        relative_path='v1alpha/{+name}:render',
        request_field='',
        request_type_name='AppconfigmanagerProjectsLocationsConfigsVersionsRenderRequest',
        response_type_name='RenderConfigVersionResponse',
        supports_download=False,
    )

  class ProjectsLocationsConfigsService(base_api.BaseApiService):
    """Service class for the projects_locations_configs resource."""

    _NAME = 'projects_locations_configs'

    def __init__(self, client):
      super(AppconfigmanagerV1alpha.ProjectsLocationsConfigsService, self).__init__(client)
      self._upload_configs = {
          }

    def Create(self, request, global_params=None):
      r"""Creates a new Config in a given project and location.

      Args:
        request: (AppconfigmanagerProjectsLocationsConfigsCreateRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (Config) The response message.
      """
      config = self.GetMethodConfig('Create')
      return self._RunMethod(
          config, request, global_params=global_params)

    Create.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}/configs',
        http_method='POST',
        method_id='appconfigmanager.projects.locations.configs.create',
        ordered_params=['parent'],
        path_params=['parent'],
        query_params=['configId', 'requestId'],
        relative_path='v1alpha/{+parent}/configs',
        request_field='config',
        request_type_name='AppconfigmanagerProjectsLocationsConfigsCreateRequest',
        response_type_name='Config',
        supports_download=False,
    )

    def Delete(self, request, global_params=None):
      r"""Deletes a single Config.

      Args:
        request: (AppconfigmanagerProjectsLocationsConfigsDeleteRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (Empty) The response message.
      """
      config = self.GetMethodConfig('Delete')
      return self._RunMethod(
          config, request, global_params=global_params)

    Delete.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}/configs/{configsId}',
        http_method='DELETE',
        method_id='appconfigmanager.projects.locations.configs.delete',
        ordered_params=['name'],
        path_params=['name'],
        query_params=['requestId'],
        relative_path='v1alpha/{+name}',
        request_field='',
        request_type_name='AppconfigmanagerProjectsLocationsConfigsDeleteRequest',
        response_type_name='Empty',
        supports_download=False,
    )

    def Get(self, request, global_params=None):
      r"""Gets details of a single Config.

      Args:
        request: (AppconfigmanagerProjectsLocationsConfigsGetRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (Config) The response message.
      """
      config = self.GetMethodConfig('Get')
      return self._RunMethod(
          config, request, global_params=global_params)

    Get.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}/configs/{configsId}',
        http_method='GET',
        method_id='appconfigmanager.projects.locations.configs.get',
        ordered_params=['name'],
        path_params=['name'],
        query_params=[],
        relative_path='v1alpha/{+name}',
        request_field='',
        request_type_name='AppconfigmanagerProjectsLocationsConfigsGetRequest',
        response_type_name='Config',
        supports_download=False,
    )

    def List(self, request, global_params=None):
      r"""Lists Configs in a given project and location.

      Args:
        request: (AppconfigmanagerProjectsLocationsConfigsListRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (ListConfigsResponse) The response message.
      """
      config = self.GetMethodConfig('List')
      return self._RunMethod(
          config, request, global_params=global_params)

    List.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}/configs',
        http_method='GET',
        method_id='appconfigmanager.projects.locations.configs.list',
        ordered_params=['parent'],
        path_params=['parent'],
        query_params=['filter', 'orderBy', 'pageSize', 'pageToken'],
        relative_path='v1alpha/{+parent}/configs',
        request_field='',
        request_type_name='AppconfigmanagerProjectsLocationsConfigsListRequest',
        response_type_name='ListConfigsResponse',
        supports_download=False,
    )

    def Patch(self, request, global_params=None):
      r"""Updates the parameters of a single Config.

      Args:
        request: (AppconfigmanagerProjectsLocationsConfigsPatchRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (Config) The response message.
      """
      config = self.GetMethodConfig('Patch')
      return self._RunMethod(
          config, request, global_params=global_params)

    Patch.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}/configs/{configsId}',
        http_method='PATCH',
        method_id='appconfigmanager.projects.locations.configs.patch',
        ordered_params=['name'],
        path_params=['name'],
        query_params=['requestId', 'updateMask'],
        relative_path='v1alpha/{+name}',
        request_field='config',
        request_type_name='AppconfigmanagerProjectsLocationsConfigsPatchRequest',
        response_type_name='Config',
        supports_download=False,
    )

  class ProjectsLocationsService(base_api.BaseApiService):
    """Service class for the projects_locations resource."""

    _NAME = 'projects_locations'

    def __init__(self, client):
      super(AppconfigmanagerV1alpha.ProjectsLocationsService, self).__init__(client)
      self._upload_configs = {
          }

    def Get(self, request, global_params=None):
      r"""Gets information about a location.

      Args:
        request: (AppconfigmanagerProjectsLocationsGetRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (Location) The response message.
      """
      config = self.GetMethodConfig('Get')
      return self._RunMethod(
          config, request, global_params=global_params)

    Get.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations/{locationsId}',
        http_method='GET',
        method_id='appconfigmanager.projects.locations.get',
        ordered_params=['name'],
        path_params=['name'],
        query_params=[],
        relative_path='v1alpha/{+name}',
        request_field='',
        request_type_name='AppconfigmanagerProjectsLocationsGetRequest',
        response_type_name='Location',
        supports_download=False,
    )

    def List(self, request, global_params=None):
      r"""Lists information about the supported locations for this service.

      Args:
        request: (AppconfigmanagerProjectsLocationsListRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (ListLocationsResponse) The response message.
      """
      config = self.GetMethodConfig('List')
      return self._RunMethod(
          config, request, global_params=global_params)

    List.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1alpha/projects/{projectsId}/locations',
        http_method='GET',
        method_id='appconfigmanager.projects.locations.list',
        ordered_params=['name'],
        path_params=['name'],
        query_params=['extraLocationTypes', 'filter', 'pageSize', 'pageToken'],
        relative_path='v1alpha/{+name}/locations',
        request_field='',
        request_type_name='AppconfigmanagerProjectsLocationsListRequest',
        response_type_name='ListLocationsResponse',
        supports_download=False,
    )

  class ProjectsService(base_api.BaseApiService):
    """Service class for the projects resource."""

    _NAME = 'projects'

    def __init__(self, client):
      super(AppconfigmanagerV1alpha.ProjectsService, self).__init__(client)
      self._upload_configs = {
          }
