# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Helpers for the operations API client."""

from apitools.base.py import exceptions
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.privateca import base
from googlecloudsdk.api_lib.util import exceptions as api_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


def ListOperations(location, list_filter, limit, page_size):
  """Lists operations in a given project.

  Args:
    location: The location to list operations in, or '-' for all locations.
    list_filter: A filter to apply to the list request.
    limit: The number of operations to retrieve.
    page_size: The number of operations to retrieve per page.

  Returns:
    A generator of matching operations.
  """
  client = base.GetClientInstance(api_version='v1')
  messages = base.GetMessagesModule(api_version='v1')

  project = properties.VALUES.core.project.GetOrFail()
  parent_resource = 'projects/{}/locations/{}'.format(project, location)

  request = messages.PrivatecaProjectsLocationsOperationsListRequest(
      name=parent_resource, filter=list_filter)

  return list_pager.YieldFromList(
      client.projects_locations_operations,
      request,
      field='operations',
      limit=limit,
      batch_size_attribute='pageSize',
      batch_size=page_size)


def GetOperation(operation_ref):
  """Gets an operation resource."""
  client = base.GetClientInstance(api_version='v1')
  messages = base.GetMessagesModule(api_version='v1')
  request = messages.PrivatecaProjectsLocationsOperationsGetRequest(
      name=operation_ref.RelativeName())
  try:
    return client.projects_locations_operations.Get(request)
  except exceptions.HttpError as e:
    log.debug('GetOperation failed: %r.', e)
    raise api_exceptions.HttpException(e)
