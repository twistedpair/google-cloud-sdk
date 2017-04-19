# Copyright 2016 Google Inc. All Rights Reserved.
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

"""service-management enable helper functions."""

import json

from apitools.base.py import exceptions
from apitools.base.py import list_pager

from googlecloudsdk.api_lib.service_management import services_util
from googlecloudsdk.api_lib.util import exceptions as api_lib_exceptions
from googlecloudsdk.core import log


def EnableServiceApiCall(project_id, service_name):
  """Make API call to enable a specific API.

  Args:
    project_id: The ID of the project for which to enable the service.
    service_name: The name of the service to enable on the project.

  Raises:
    services_util.EnableServicePermissionDeniedException: when enabling the API
        fails.
    api_lib_exceptions.HttpException: Another miscellaneous error with the
        enabling service.

  Returns:
    The result of the Enable operation
  """

  client = services_util.GetClientInstance()
  messages = services_util.GetMessagesModule()

  request = messages.ServicemanagementServicesEnableRequest(
      serviceName=service_name,
      enableServiceRequest=messages.EnableServiceRequest(
          consumerId='project:' + project_id
      )
  )

  try:
    return client.services.Enable(request)
  except exceptions.HttpError as e:
    if e.status_code in [403, 404]:
      # TODO(b/36865980): When backend supports it, differentiate errors.
      msg = json.loads(e.content).get('error', {}).get('message', '')
      raise services_util.EnableServicePermissionDeniedException(msg)
    else:
      raise api_lib_exceptions.HttpException(e)


def IsServiceEnabled(project_id, service_name):
  """Return true if the service is enabled.

  Args:
    project_id: The ID of the project we want to query.
    service_name: The name of the service.

  Raises:
    services_util.ListServicesPermissionDeniedException: if a 403 or 404
        error is returned by the List request.
    api_lib_exceptions.HttpException: Another miscellaneous error with the
        listing service.

  Returns:
    True if the service is enabled, false otherwise.
  """

  client = services_util.GetClientInstance()

  # Get the list of enabled services.
  request = services_util.GetEnabledListRequest(project_id)
  try:
    for service in list_pager.YieldFromList(
        client.services,
        request,
        batch_size_attribute='pageSize',
        field='services'):
      # If the service is present in the list of enabled services, return
      # True, otherwise return False
      if service.serviceName.lower() == service_name.lower():
        return True
  except exceptions.HttpError as e:
    if e.status_code in [403, 404]:
      msg = json.loads(e.content).get('error', {}).get('message', '')
      raise services_util.ListServicesPermissionDeniedException(msg)
    raise api_lib_exceptions.HttpException(e)
  return False


def EnableServiceIfDisabled(project_id, service_name, async=False):
  """Check to see if the service is enabled, and if it is not, do so.

  Args:
    project_id: The ID of the project for which to enable the service.
    service_name: The name of the service to enable on the project.
    async: bool, if True, print the operation ID and return immediately,
           without waiting for the op to complete.

  Raises:
    services_util.ListServicesPermissionDeniedException: if a 403 or 404 error
        is returned by the listing service.
    services_util.EnableServicePermissionDeniedException: when enabling the API
        fails with a 403 or 404 error code.
    api_lib_exceptions.HttpException: Another miscellaneous error with the
        servicemanagement service.
  """

  # If the service is enabled, we can return
  if IsServiceEnabled(project_id, service_name):
    log.debug('Service [{0}] is already enabled for project [{1}]'.format(
        service_name, project_id))
    return

  # If the service is not yet enabled, enable it
  log.status.Print('Enabling service {0} on project {1}...'.format(
      service_name, project_id))

  # Enable the service
  operation = EnableServiceApiCall(project_id, service_name)

  # Process the enable operation
  services_util.ProcessOperationResult(operation, async)
