"""Generated client library for assuredworkloads version v1beta1."""
# NOTE: This file is autogenerated and should not be edited by hand.

from __future__ import absolute_import

from apitools.base.py import base_api
from googlecloudsdk.third_party.apis.assuredworkloads.v1beta1 import assuredworkloads_v1beta1_messages as messages


class AssuredworkloadsV1beta1(base_api.BaseApiClient):
  """Generated client library for service assuredworkloads version v1beta1."""

  MESSAGES_MODULE = messages
  BASE_URL = 'https://assuredworkloads.googleapis.com/'
  MTLS_BASE_URL = 'https://assuredworkloads.mtls.googleapis.com/'

  _PACKAGE = 'assuredworkloads'
  _SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
  _VERSION = 'v1beta1'
  _CLIENT_ID = 'CLIENT_ID'
  _CLIENT_SECRET = 'CLIENT_SECRET'
  _USER_AGENT = 'google-cloud-sdk'
  _CLIENT_CLASS_NAME = 'AssuredworkloadsV1beta1'
  _URL_VERSION = 'v1beta1'
  _API_KEY = None

  def __init__(self, url='', credentials=None,
               get_credentials=True, http=None, model=None,
               log_request=False, log_response=False,
               credentials_args=None, default_global_params=None,
               additional_http_headers=None, response_encoding=None):
    """Create a new assuredworkloads handle."""
    url = url or self.BASE_URL
    super(AssuredworkloadsV1beta1, self).__init__(
        url, credentials=credentials,
        get_credentials=get_credentials, http=http, model=model,
        log_request=log_request, log_response=log_response,
        credentials_args=credentials_args,
        default_global_params=default_global_params,
        additional_http_headers=additional_http_headers,
        response_encoding=response_encoding)
    self.organizations_locations_operations = self.OrganizationsLocationsOperationsService(self)
    self.organizations_locations_workloads_organizations_locations_workloads = self.OrganizationsLocationsWorkloadsOrganizationsLocationsWorkloadsService(self)
    self.organizations_locations_workloads_organizations_locations = self.OrganizationsLocationsWorkloadsOrganizationsLocationsService(self)
    self.organizations_locations_workloads_organizations = self.OrganizationsLocationsWorkloadsOrganizationsService(self)
    self.organizations_locations_workloads_violations = self.OrganizationsLocationsWorkloadsViolationsService(self)
    self.organizations_locations_workloads = self.OrganizationsLocationsWorkloadsService(self)
    self.organizations_locations = self.OrganizationsLocationsService(self)
    self.organizations = self.OrganizationsService(self)
    self.projects_organizations_locations_workloads = self.ProjectsOrganizationsLocationsWorkloadsService(self)
    self.projects_organizations_locations = self.ProjectsOrganizationsLocationsService(self)
    self.projects_organizations = self.ProjectsOrganizationsService(self)
    self.projects = self.ProjectsService(self)

  class OrganizationsLocationsOperationsService(base_api.BaseApiService):
    """Service class for the organizations_locations_operations resource."""

    _NAME = 'organizations_locations_operations'

    def __init__(self, client):
      super(AssuredworkloadsV1beta1.OrganizationsLocationsOperationsService, self).__init__(client)
      self._upload_configs = {
          }

    def Get(self, request, global_params=None):
      r"""Gets the latest state of a long-running operation. Clients can use this method to poll the operation result at intervals as recommended by the API service.

      Args:
        request: (AssuredworkloadsOrganizationsLocationsOperationsGetRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (GoogleLongrunningOperation) The response message.
      """
      config = self.GetMethodConfig('Get')
      return self._RunMethod(
          config, request, global_params=global_params)

    Get.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1beta1/organizations/{organizationsId}/locations/{locationsId}/operations/{operationsId}',
        http_method='GET',
        method_id='assuredworkloads.organizations.locations.operations.get',
        ordered_params=['name'],
        path_params=['name'],
        query_params=[],
        relative_path='v1beta1/{+name}',
        request_field='',
        request_type_name='AssuredworkloadsOrganizationsLocationsOperationsGetRequest',
        response_type_name='GoogleLongrunningOperation',
        supports_download=False,
    )

    def List(self, request, global_params=None):
      r"""Lists operations that match the specified filter in the request. If the server doesn't support this method, it returns `UNIMPLEMENTED`. NOTE: the `name` binding allows API services to override the binding to use different resource name schemes, such as `users/*/operations`. To override the binding, API services can add a binding such as `"/v1/{name=users/*}/operations"` to their service configuration. For backwards compatibility, the default name includes the operations collection id, however overriding users must ensure the name binding is the parent resource, without the operations collection id.

      Args:
        request: (AssuredworkloadsOrganizationsLocationsOperationsListRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (GoogleLongrunningListOperationsResponse) The response message.
      """
      config = self.GetMethodConfig('List')
      return self._RunMethod(
          config, request, global_params=global_params)

    List.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1beta1/organizations/{organizationsId}/locations/{locationsId}/operations',
        http_method='GET',
        method_id='assuredworkloads.organizations.locations.operations.list',
        ordered_params=['name'],
        path_params=['name'],
        query_params=['filter', 'pageSize', 'pageToken'],
        relative_path='v1beta1/{+name}/operations',
        request_field='',
        request_type_name='AssuredworkloadsOrganizationsLocationsOperationsListRequest',
        response_type_name='GoogleLongrunningListOperationsResponse',
        supports_download=False,
    )

  class OrganizationsLocationsWorkloadsOrganizationsLocationsWorkloadsService(base_api.BaseApiService):
    """Service class for the organizations_locations_workloads_organizations_locations_workloads resource."""

    _NAME = 'organizations_locations_workloads_organizations_locations_workloads'

    def __init__(self, client):
      super(AssuredworkloadsV1beta1.OrganizationsLocationsWorkloadsOrganizationsLocationsWorkloadsService, self).__init__(client)
      self._upload_configs = {
          }

    def AnalyzeWorkloadMove(self, request, global_params=None):
      r"""Analyzes a hypothetical move of a source project or project-based workload to a target (destination) folder-based workload.

      Args:
        request: (AssuredworkloadsOrganizationsLocationsWorkloadsOrganizationsLocationsWorkloadsAnalyzeWorkloadMoveRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (GoogleCloudAssuredworkloadsV1beta1AnalyzeWorkloadMoveResponse) The response message.
      """
      config = self.GetMethodConfig('AnalyzeWorkloadMove')
      return self._RunMethod(
          config, request, global_params=global_params)

    AnalyzeWorkloadMove.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1beta1/organizations/{organizationsId}/locations/{locationsId}/workloads/{workloadsId}/organizations/{organizationsId1}/locations/{locationsId1}/workloads/{workloadsId1}:analyzeWorkloadMove',
        http_method='GET',
        method_id='assuredworkloads.organizations.locations.workloads.organizations.locations.workloads.analyzeWorkloadMove',
        ordered_params=['source', 'target'],
        path_params=['source', 'target'],
        query_params=['project'],
        relative_path='v1beta1/{+source}/{+target}:analyzeWorkloadMove',
        request_field='',
        request_type_name='AssuredworkloadsOrganizationsLocationsWorkloadsOrganizationsLocationsWorkloadsAnalyzeWorkloadMoveRequest',
        response_type_name='GoogleCloudAssuredworkloadsV1beta1AnalyzeWorkloadMoveResponse',
        supports_download=False,
    )

  class OrganizationsLocationsWorkloadsOrganizationsLocationsService(base_api.BaseApiService):
    """Service class for the organizations_locations_workloads_organizations_locations resource."""

    _NAME = 'organizations_locations_workloads_organizations_locations'

    def __init__(self, client):
      super(AssuredworkloadsV1beta1.OrganizationsLocationsWorkloadsOrganizationsLocationsService, self).__init__(client)
      self._upload_configs = {
          }

  class OrganizationsLocationsWorkloadsOrganizationsService(base_api.BaseApiService):
    """Service class for the organizations_locations_workloads_organizations resource."""

    _NAME = 'organizations_locations_workloads_organizations'

    def __init__(self, client):
      super(AssuredworkloadsV1beta1.OrganizationsLocationsWorkloadsOrganizationsService, self).__init__(client)
      self._upload_configs = {
          }

  class OrganizationsLocationsWorkloadsViolationsService(base_api.BaseApiService):
    """Service class for the organizations_locations_workloads_violations resource."""

    _NAME = 'organizations_locations_workloads_violations'

    def __init__(self, client):
      super(AssuredworkloadsV1beta1.OrganizationsLocationsWorkloadsViolationsService, self).__init__(client)
      self._upload_configs = {
          }

    def Acknowledge(self, request, global_params=None):
      r"""Acknowledges an existing violation. By acknowledging a violation, users acknowledge the existence of a compliance violation in their workload and decide to ignore it due to a valid business justification. Acknowledgement is a permanent operation and it cannot be reverted.

      Args:
        request: (AssuredworkloadsOrganizationsLocationsWorkloadsViolationsAcknowledgeRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (GoogleCloudAssuredworkloadsV1beta1AcknowledgeViolationResponse) The response message.
      """
      config = self.GetMethodConfig('Acknowledge')
      return self._RunMethod(
          config, request, global_params=global_params)

    Acknowledge.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1beta1/organizations/{organizationsId}/locations/{locationsId}/workloads/{workloadsId}/violations/{violationsId}:acknowledge',
        http_method='POST',
        method_id='assuredworkloads.organizations.locations.workloads.violations.acknowledge',
        ordered_params=['name'],
        path_params=['name'],
        query_params=[],
        relative_path='v1beta1/{+name}:acknowledge',
        request_field='googleCloudAssuredworkloadsV1beta1AcknowledgeViolationRequest',
        request_type_name='AssuredworkloadsOrganizationsLocationsWorkloadsViolationsAcknowledgeRequest',
        response_type_name='GoogleCloudAssuredworkloadsV1beta1AcknowledgeViolationResponse',
        supports_download=False,
    )

    def Get(self, request, global_params=None):
      r"""Retrieves Assured Workload Violation based on ID.

      Args:
        request: (AssuredworkloadsOrganizationsLocationsWorkloadsViolationsGetRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (GoogleCloudAssuredworkloadsV1beta1Violation) The response message.
      """
      config = self.GetMethodConfig('Get')
      return self._RunMethod(
          config, request, global_params=global_params)

    Get.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1beta1/organizations/{organizationsId}/locations/{locationsId}/workloads/{workloadsId}/violations/{violationsId}',
        http_method='GET',
        method_id='assuredworkloads.organizations.locations.workloads.violations.get',
        ordered_params=['name'],
        path_params=['name'],
        query_params=[],
        relative_path='v1beta1/{+name}',
        request_field='',
        request_type_name='AssuredworkloadsOrganizationsLocationsWorkloadsViolationsGetRequest',
        response_type_name='GoogleCloudAssuredworkloadsV1beta1Violation',
        supports_download=False,
    )

    def List(self, request, global_params=None):
      r"""Lists the Violations in the AssuredWorkload Environment. Callers may also choose to read across multiple Workloads as per [AIP-159](https://google.aip.dev/159) by using '-' (the hyphen or dash character) as a wildcard character instead of workload-id in the parent. Format `organizations/{org_id}/locations/{location}/workloads/-`.

      Args:
        request: (AssuredworkloadsOrganizationsLocationsWorkloadsViolationsListRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (GoogleCloudAssuredworkloadsV1beta1ListViolationsResponse) The response message.
      """
      config = self.GetMethodConfig('List')
      return self._RunMethod(
          config, request, global_params=global_params)

    List.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1beta1/organizations/{organizationsId}/locations/{locationsId}/workloads/{workloadsId}/violations',
        http_method='GET',
        method_id='assuredworkloads.organizations.locations.workloads.violations.list',
        ordered_params=['parent'],
        path_params=['parent'],
        query_params=['filter', 'interval_endTime', 'interval_startTime', 'pageSize', 'pageToken'],
        relative_path='v1beta1/{+parent}/violations',
        request_field='',
        request_type_name='AssuredworkloadsOrganizationsLocationsWorkloadsViolationsListRequest',
        response_type_name='GoogleCloudAssuredworkloadsV1beta1ListViolationsResponse',
        supports_download=False,
    )

  class OrganizationsLocationsWorkloadsService(base_api.BaseApiService):
    """Service class for the organizations_locations_workloads resource."""

    _NAME = 'organizations_locations_workloads'

    def __init__(self, client):
      super(AssuredworkloadsV1beta1.OrganizationsLocationsWorkloadsService, self).__init__(client)
      self._upload_configs = {
          }

    def Create(self, request, global_params=None):
      r"""Creates Assured Workload.

      Args:
        request: (AssuredworkloadsOrganizationsLocationsWorkloadsCreateRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (GoogleLongrunningOperation) The response message.
      """
      config = self.GetMethodConfig('Create')
      return self._RunMethod(
          config, request, global_params=global_params)

    Create.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1beta1/organizations/{organizationsId}/locations/{locationsId}/workloads',
        http_method='POST',
        method_id='assuredworkloads.organizations.locations.workloads.create',
        ordered_params=['parent'],
        path_params=['parent'],
        query_params=['externalId'],
        relative_path='v1beta1/{+parent}/workloads',
        request_field='googleCloudAssuredworkloadsV1beta1Workload',
        request_type_name='AssuredworkloadsOrganizationsLocationsWorkloadsCreateRequest',
        response_type_name='GoogleLongrunningOperation',
        supports_download=False,
    )

    def Delete(self, request, global_params=None):
      r"""Deletes the workload. Make sure that workload's direct children are already in a deleted state, otherwise the request will fail with a FAILED_PRECONDITION error. In addition to assuredworkloads.workload.delete permission, the user should also have orgpolicy.policy.set permission on the deleted folder to remove Assured Workloads OrgPolicies.

      Args:
        request: (AssuredworkloadsOrganizationsLocationsWorkloadsDeleteRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (GoogleProtobufEmpty) The response message.
      """
      config = self.GetMethodConfig('Delete')
      return self._RunMethod(
          config, request, global_params=global_params)

    Delete.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1beta1/organizations/{organizationsId}/locations/{locationsId}/workloads/{workloadsId}',
        http_method='DELETE',
        method_id='assuredworkloads.organizations.locations.workloads.delete',
        ordered_params=['name'],
        path_params=['name'],
        query_params=['etag'],
        relative_path='v1beta1/{+name}',
        request_field='',
        request_type_name='AssuredworkloadsOrganizationsLocationsWorkloadsDeleteRequest',
        response_type_name='GoogleProtobufEmpty',
        supports_download=False,
    )

    def Get(self, request, global_params=None):
      r"""Gets Assured Workload associated with a CRM Node.

      Args:
        request: (AssuredworkloadsOrganizationsLocationsWorkloadsGetRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (GoogleCloudAssuredworkloadsV1beta1Workload) The response message.
      """
      config = self.GetMethodConfig('Get')
      return self._RunMethod(
          config, request, global_params=global_params)

    Get.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1beta1/organizations/{organizationsId}/locations/{locationsId}/workloads/{workloadsId}',
        http_method='GET',
        method_id='assuredworkloads.organizations.locations.workloads.get',
        ordered_params=['name'],
        path_params=['name'],
        query_params=[],
        relative_path='v1beta1/{+name}',
        request_field='',
        request_type_name='AssuredworkloadsOrganizationsLocationsWorkloadsGetRequest',
        response_type_name='GoogleCloudAssuredworkloadsV1beta1Workload',
        supports_download=False,
    )

    def List(self, request, global_params=None):
      r"""Lists Assured Workloads under a CRM Node.

      Args:
        request: (AssuredworkloadsOrganizationsLocationsWorkloadsListRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (GoogleCloudAssuredworkloadsV1beta1ListWorkloadsResponse) The response message.
      """
      config = self.GetMethodConfig('List')
      return self._RunMethod(
          config, request, global_params=global_params)

    List.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1beta1/organizations/{organizationsId}/locations/{locationsId}/workloads',
        http_method='GET',
        method_id='assuredworkloads.organizations.locations.workloads.list',
        ordered_params=['parent'],
        path_params=['parent'],
        query_params=['filter', 'pageSize', 'pageToken'],
        relative_path='v1beta1/{+parent}/workloads',
        request_field='',
        request_type_name='AssuredworkloadsOrganizationsLocationsWorkloadsListRequest',
        response_type_name='GoogleCloudAssuredworkloadsV1beta1ListWorkloadsResponse',
        supports_download=False,
    )

    def Patch(self, request, global_params=None):
      r"""Updates an existing workload. Currently allows updating of workload display_name and labels. For force updates don't set etag field in the Workload. Only one update operation per workload can be in progress.

      Args:
        request: (AssuredworkloadsOrganizationsLocationsWorkloadsPatchRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (GoogleCloudAssuredworkloadsV1beta1Workload) The response message.
      """
      config = self.GetMethodConfig('Patch')
      return self._RunMethod(
          config, request, global_params=global_params)

    Patch.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1beta1/organizations/{organizationsId}/locations/{locationsId}/workloads/{workloadsId}',
        http_method='PATCH',
        method_id='assuredworkloads.organizations.locations.workloads.patch',
        ordered_params=['name'],
        path_params=['name'],
        query_params=['updateMask'],
        relative_path='v1beta1/{+name}',
        request_field='googleCloudAssuredworkloadsV1beta1Workload',
        request_type_name='AssuredworkloadsOrganizationsLocationsWorkloadsPatchRequest',
        response_type_name='GoogleCloudAssuredworkloadsV1beta1Workload',
        supports_download=False,
    )

    def RestrictAllowedResources(self, request, global_params=None):
      r"""Restrict the list of resources allowed in the Workload environment. The current list of allowed products can be found at https://cloud.google.com/assured-workloads/docs/supported-products In addition to assuredworkloads.workload.update permission, the user should also have orgpolicy.policy.set permission on the folder resource to use this functionality.

      Args:
        request: (AssuredworkloadsOrganizationsLocationsWorkloadsRestrictAllowedResourcesRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (GoogleCloudAssuredworkloadsV1beta1RestrictAllowedResourcesResponse) The response message.
      """
      config = self.GetMethodConfig('RestrictAllowedResources')
      return self._RunMethod(
          config, request, global_params=global_params)

    RestrictAllowedResources.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1beta1/organizations/{organizationsId}/locations/{locationsId}/workloads/{workloadsId}:restrictAllowedResources',
        http_method='POST',
        method_id='assuredworkloads.organizations.locations.workloads.restrictAllowedResources',
        ordered_params=['name'],
        path_params=['name'],
        query_params=[],
        relative_path='v1beta1/{+name}:restrictAllowedResources',
        request_field='googleCloudAssuredworkloadsV1beta1RestrictAllowedResourcesRequest',
        request_type_name='AssuredworkloadsOrganizationsLocationsWorkloadsRestrictAllowedResourcesRequest',
        response_type_name='GoogleCloudAssuredworkloadsV1beta1RestrictAllowedResourcesResponse',
        supports_download=False,
    )

  class OrganizationsLocationsService(base_api.BaseApiService):
    """Service class for the organizations_locations resource."""

    _NAME = 'organizations_locations'

    def __init__(self, client):
      super(AssuredworkloadsV1beta1.OrganizationsLocationsService, self).__init__(client)
      self._upload_configs = {
          }

  class OrganizationsService(base_api.BaseApiService):
    """Service class for the organizations resource."""

    _NAME = 'organizations'

    def __init__(self, client):
      super(AssuredworkloadsV1beta1.OrganizationsService, self).__init__(client)
      self._upload_configs = {
          }

  class ProjectsOrganizationsLocationsWorkloadsService(base_api.BaseApiService):
    """Service class for the projects_organizations_locations_workloads resource."""

    _NAME = 'projects_organizations_locations_workloads'

    def __init__(self, client):
      super(AssuredworkloadsV1beta1.ProjectsOrganizationsLocationsWorkloadsService, self).__init__(client)
      self._upload_configs = {
          }

    def AnalyzeWorkloadMove(self, request, global_params=None):
      r"""Analyzes a hypothetical move of a source project or project-based workload to a target (destination) folder-based workload.

      Args:
        request: (AssuredworkloadsProjectsOrganizationsLocationsWorkloadsAnalyzeWorkloadMoveRequest) input message
        global_params: (StandardQueryParameters, default: None) global arguments
      Returns:
        (GoogleCloudAssuredworkloadsV1beta1AnalyzeWorkloadMoveResponse) The response message.
      """
      config = self.GetMethodConfig('AnalyzeWorkloadMove')
      return self._RunMethod(
          config, request, global_params=global_params)

    AnalyzeWorkloadMove.method_config = lambda: base_api.ApiMethodInfo(
        flat_path='v1beta1/projects/{projectsId}/organizations/{organizationsId}/locations/{locationsId}/workloads/{workloadsId}:analyzeWorkloadMove',
        http_method='GET',
        method_id='assuredworkloads.projects.organizations.locations.workloads.analyzeWorkloadMove',
        ordered_params=['project', 'target'],
        path_params=['project', 'target'],
        query_params=['source'],
        relative_path='v1beta1/{+project}/{+target}:analyzeWorkloadMove',
        request_field='',
        request_type_name='AssuredworkloadsProjectsOrganizationsLocationsWorkloadsAnalyzeWorkloadMoveRequest',
        response_type_name='GoogleCloudAssuredworkloadsV1beta1AnalyzeWorkloadMoveResponse',
        supports_download=False,
    )

  class ProjectsOrganizationsLocationsService(base_api.BaseApiService):
    """Service class for the projects_organizations_locations resource."""

    _NAME = 'projects_organizations_locations'

    def __init__(self, client):
      super(AssuredworkloadsV1beta1.ProjectsOrganizationsLocationsService, self).__init__(client)
      self._upload_configs = {
          }

  class ProjectsOrganizationsService(base_api.BaseApiService):
    """Service class for the projects_organizations resource."""

    _NAME = 'projects_organizations'

    def __init__(self, client):
      super(AssuredworkloadsV1beta1.ProjectsOrganizationsService, self).__init__(client)
      self._upload_configs = {
          }

  class ProjectsService(base_api.BaseApiService):
    """Service class for the projects resource."""

    _NAME = 'projects'

    def __init__(self, client):
      super(AssuredworkloadsV1beta1.ProjectsService, self).__init__(client)
      self._upload_configs = {
          }
