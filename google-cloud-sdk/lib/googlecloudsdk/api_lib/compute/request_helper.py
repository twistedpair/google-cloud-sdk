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
"""Module for making API requests."""
import copy

from googlecloudsdk.api_lib.compute import batch_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.api_lib.compute import waiters
from googlecloudsdk.core import log


def _RequestsAreListRequests(requests):
  list_requests = [method in ('List', 'AggregatedList')
                   for _, method, _ in requests]
  if all(list_requests):
    return True
  elif not any(list_requests):
    return False
  else:
    raise ValueError(
        'All requests must be either list requests or non-list requests.')


def _List(requests, http, batch_url, errors):
  """Makes a series of list and/or aggregatedList batch requests.

  Args:
    requests: A list of requests to make. Each element must be a 3-element
      tuple where the first element is the service, the second element is
      the method ('List' or 'AggregatedList'), and the third element
      is a protocol buffer representing either a list or aggregatedList
      request.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors. If any response contains an error,
      it is added to this list.

  Yields:
    Resources encapsulated as protocol buffers as they are received
      from the server.
  """
  while requests:
    responses, request_errors = batch_helper.MakeRequests(
        requests=requests,
        http=http,
        batch_url=batch_url)
    errors.extend(request_errors)

    new_requests = []

    for i, response in enumerate(responses):
      if not response:
        continue

      service, method, request_protobuf = requests[i]

      # If the request is a list call, then yield the items directly.
      if method == 'List':
        for item in response.items:
          yield item

      # If the request is an aggregatedList call, then do all the
      # magic necessary to get the actual resources because the
      # aggregatedList responses are very complicated data
      # structures...
      else:
        items_field_name = service.GetMethodConfig(
            'AggregatedList').relative_path.split('/')[-1]
        for scope_result in response.items.additionalProperties:
          # If the given scope is unreachable, record the warning
          # message in the errors list.
          warning = scope_result.value.warning
          if (warning and
              warning.code == warning.CodeValueValuesEnum.UNREACHABLE):
            errors.append((None, warning.message))

          items = getattr(scope_result.value, items_field_name)
          for item in items:
            yield item

      next_page_token = response.nextPageToken
      if next_page_token:
        new_request_protobuf = copy.deepcopy(request_protobuf)
        new_request_protobuf.pageToken = next_page_token
        new_requests.append((service, method, new_request_protobuf))

    requests = new_requests


def MakeRequests(requests, http, batch_url, errors):
  """Makes one or more requests to the API.

  Each request can be either a synchronous API call or an asynchronous
  one. For synchronous calls (e.g., get and list), the result from the
  server is yielded immediately. For asynchronous calls (e.g., calls
  that return operations like insert), this function waits until the
  operation reaches the DONE state and fetches the corresponding
  object and yields that object (nothing is yielded for deletions).

  Currently, a heterogenous set of synchronous calls can be made
  (e.g., get request to fetch a disk and instance), however, the
  asynchronous requests must be homogenous (e.g., they must all be the
  same verb on the same collection). In the future, heterogenous
  asynchronous requests will be supported. For now, it is up to the
  client to ensure that the asynchronous requests are
  homogenous. Synchronous and asynchronous requests can be mixed.

  Args:
    requests: A list of requests to make. Each element must be a 3-element
      tuple where the first element is the service, the second element is
      the string name of the method on the service, and the last element
      is a protocol buffer representing the request.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors. If any response contains an error,
      it is added to this list.

  Yields:
    A response for each request. For deletion requests, no corresponding
    responses are returned.
  """
  if _RequestsAreListRequests(requests):
    for item in _List(
        requests=requests, http=http, batch_url=batch_url, errors=errors):
      yield item
    return

  # TODO(user): Delete the batch_helper module and move its logic
  # here. To do this, we also have to edit the lister module to depend
  # on this module instead of batch_helper.
  responses, new_errors = batch_helper.MakeRequests(
      requests=requests, http=http, batch_url=batch_url)
  errors.extend(new_errors)

  operation_service = None
  resource_service = None
  project = None

  # Collects all operation objects in a list so they can be waited on
  # and yields all non-operation objects since non-operation responses
  # cannot be waited on.
  operations = []

  for request, response in zip(requests, responses):
    if response is None:
      continue

    service, _, request_body = request
    if (isinstance(response, service.client.MESSAGES_MODULE.Operation) and
        service.__class__.__name__ not in (
            'GlobalOperationsService',
            'RegionOperationsService',
            'ZoneOperationsService',
            'GlobalAccountsOperationsService')):

      operations.append(response)

      # This logic assumes that all requests are homogenous, i.e.,
      # they all make calls to the same service and verb. This is
      # temporary. In the future, we will push this logic into the
      # function that does the actual waiting. For now, we have to
      # deal with existing interfaces to keep the scopes of the
      # refactoring CLs small.
      # TODO(b/32276307)
      if not operation_service:
        resource_service = service
        project = request_body.project

        if response.kind == 'clouduseraccounts#operation':
          operation_service = service.client.globalAccountsOperations
        elif response.zone:
          operation_service = service.client.zoneOperations
        elif response.region:
          operation_service = service.client.regionOperations
        else:
          operation_service = service.client.globalOperations

    else:
      yield response

  if operations:
    warnings = []
    # TODO(user): Delete the waiters module and move the logic
    # here. We can also get a rid of parameters like operation_service
    # and project since they can be inferred from the other args.
    for response in waiters.WaitForOperations(
        operations=operations,
        project=project,
        operation_service=operation_service,
        resource_service=resource_service,
        http=http,
        batch_url=batch_url,
        warnings=warnings or [],
        errors=errors):
      yield response

    if warnings:
      log.warn(utils.ConstructList('Some requests generated warnings:',
                                   warnings))
