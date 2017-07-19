# Copyright 2014 Google Inc. All Rights Reserved.
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
"""Facilities for getting a list of Cloud resources."""

import itertools

from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.core import remote_completion
from googlecloudsdk.core.resource import resource_projector


def _ConvertProtobufsToDicts(resources):
  for resource in resources:
    if resource is None:
      continue

    yield resource_projector.MakeSerializable(resource)


def ProcessResults(resources, field_selector, sort_key_fn=None,
                   reverse_sort=False, limit=None):
  """Process the results from the list query.

  Args:
    resources: The list of returned resources.
    field_selector: Select the primary key for sorting.
    sort_key_fn: Sort the key using this comparison function.
    reverse_sort: Sort the resources in reverse order.
    limit: Limit the number of resourses returned.
  Yields:
    The resource.
  """
  resources = _ConvertProtobufsToDicts(resources)
  if sort_key_fn:
    resources = sorted(resources, key=sort_key_fn, reverse=reverse_sort)

  if limit > 0:
    resources = itertools.islice(resources, limit)
  cache = remote_completion.RemoteCompletion()
  self_links = []
  for resource in resources:
    if 'selfLink' in resource:
      self_links.append(resource['selfLink'])
    if field_selector:
      yield field_selector.Apply(resource)
    else:
      yield resource
  if self_links:
    cache.StoreInCache(self_links)


def FormatListRequests(service, project, scopes, scope_name,
                       filter_expr):
  """Helper for generating list requests."""
  requests = []

  if scopes:
    for scope in scopes:
      request = service.GetRequestType('List')(
          filter=filter_expr,
          project=project,
          maxResults=constants.MAX_RESULTS_PER_PAGE)
      setattr(request, scope_name, scope)
      requests.append((service, 'List', request))

  elif not scope_name:
    requests.append((
        service,
        'List',
        service.GetRequestType('List')(
            filter=filter_expr,
            project=project,
            maxResults=constants.MAX_RESULTS_PER_PAGE)))

  else:
    requests.append((
        service,
        'AggregatedList',
        service.GetRequestType('AggregatedList')(
            filter=filter_expr,
            project=project,
            maxResults=constants.MAX_RESULTS_PER_PAGE)))

  return requests


def _GetResources(service, project, scopes, scope_name,
                  filter_expr, http, batch_url, errors, make_requests):
  """Helper for the Get{Zonal,Regional,Global}Resources functions."""
  requests = FormatListRequests(service, project, scopes, scope_name,
                                filter_expr)

  return make_requests(
      requests=requests,
      http=http,
      batch_url=batch_url,
      errors=errors)


def GetZonalResources(service, project, requested_zones,
                      filter_expr, http, batch_url, errors):
  """Lists resources that are scoped by zone.

  Args:
    service: An apitools service object.
    project: The Compute Engine project name for which listing should be
      performed.
    requested_zones: A list of zone names that can be used to control
      the scope of the list call.
    filter_expr: A filter to pass to the list API calls.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors.

  Returns:
    A generator that yields JSON-serializable dicts representing the results.
  """
  return _GetResources(
      service=service,
      project=project,
      scopes=requested_zones,
      scope_name='zone',
      filter_expr=filter_expr,
      http=http,
      batch_url=batch_url,
      errors=errors,
      make_requests=request_helper.MakeRequests)


def GetZonalResourcesDicts(service, project, requested_zones, filter_expr, http,
                           batch_url, errors):
  """Lists resources that are scoped by zone and returns them as dicts.

  It has the same functionality as GetZonalResouces but skips translating
  JSON to messages saving lot of CPU cycles.

  Args:
    service: An apitools service object.
    project: The Compute Engine project name for which listing should be
      performed.
    requested_zones: A list of zone names that can be used to control
      the scope of the list call.
    filter_expr: A filter to pass to the list API calls.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors.

  Returns:
    A list of dicts representing the results.
  """
  return _GetResources(
      service=service,
      project=project,
      scopes=requested_zones,
      scope_name='zone',
      filter_expr=filter_expr,
      http=http,
      batch_url=batch_url,
      errors=errors,
      make_requests=request_helper.ListJson)


def GetRegionalResources(service, project, requested_regions,
                         filter_expr, http, batch_url, errors):
  """Lists resources that are scoped by region.

  Args:
    service: An apitools service object.
    project: The Compute Engine project name for which listing should be
      performed.
    requested_regions: A list of region names that can be used to
      control the scope of the list call.
    filter_expr: A filter to pass to the list API calls.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors.

  Returns:
    A generator that yields JSON-serializable dicts representing the results.
  """
  return _GetResources(
      service=service,
      project=project,
      scopes=requested_regions,
      scope_name='region',
      filter_expr=filter_expr,
      http=http,
      batch_url=batch_url,
      errors=errors,
      make_requests=request_helper.MakeRequests)


def GetRegionalResourcesDicts(service, project, requested_regions, filter_expr,
                              http, batch_url, errors):
  """Lists resources that are scoped by region and returns them as dicts.

  Args:
    service: An apitools service object.
    project: The Compute Engine project name for which listing should be
      performed.
    requested_regions: A list of region names that can be used to
      control the scope of the list call.
    filter_expr: A filter to pass to the list API calls.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors.

  Returns:
    A list of dicts representing the results.
  """
  return _GetResources(
      service=service,
      project=project,
      scopes=requested_regions,
      scope_name='region',
      filter_expr=filter_expr,
      http=http,
      batch_url=batch_url,
      errors=errors,
      make_requests=request_helper.ListJson)


def GetGlobalResources(service, project, filter_expr, http,
                       batch_url, errors):
  """Lists resources in the global scope.

  Args:
    service: An apitools service object.
    project: The Compute Engine project name for which listing should be
      performed.
    filter_expr: A filter to pass to the list API calls.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors.

  Returns:
    A generator that yields JSON-serializable dicts representing the results.
  """
  return _GetResources(
      service=service,
      project=project,
      scopes=None,
      scope_name=None,
      filter_expr=filter_expr,
      http=http,
      batch_url=batch_url,
      errors=errors,
      make_requests=request_helper.MakeRequests)


def GetGlobalResourcesDicts(service, project, filter_expr, http, batch_url,
                            errors):
  """Lists resources in the global scope and returns them as dicts.

  Args:
    service: An apitools service object.
    project: The Compute Engine project name for which listing should be
      performed.
    filter_expr: A filter to pass to the list API calls.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors.

  Returns:
    A list of dicts representing the results.
  """
  return _GetResources(
      service=service,
      project=project,
      scopes=None,
      scope_name=None,
      filter_expr=filter_expr,
      http=http,
      batch_url=batch_url,
      errors=errors,
      make_requests=request_helper.ListJson)
