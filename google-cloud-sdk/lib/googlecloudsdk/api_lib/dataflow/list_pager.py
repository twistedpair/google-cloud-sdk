# Copyright 2015 Google Inc. All Rights Reserved.
"""A helper function that executes a series of List queries for many APIs.

Based on list_pager.py from //cloud/bigscience/apitools/base/py/list_pager.py,
but modified to use pageSize rather than maxResults.
"""

from googlecloudsdk.api_lib.dataflow import dataflow_util
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.third_party.apitools.base import py as apitools_base
from googlecloudsdk.third_party.py27 import copy


def YieldFromList(
    service, request, limit=None, batch_size=100,
    method='List', field='items', predicate=None,
    current_token_attribute='pageToken',
    next_token_attribute='nextPageToken'):
  """Make a series of List requests, keeping track of page tokens.

  Args:
    service: apitools_base.BaseApiService, A service with a .List() method.
    request: protorpc.messages.Message, The request message corresponding to the
        service's .List() method, with all the attributes populated except
        the .maxResults and .pageToken attributes.
    limit: int, The maximum number of records to yield. None if all available
        records should be yielded.
    batch_size: int, The number of items to retrieve per request.
    method: str, The name of the method used to fetch resources.
    field: str, The field in the response that will be a list of items.
    predicate: lambda, A function that returns true for items to be yielded.
    current_token_attribute: str, The name of the attribute in a request message
        holding the page token for the page being requested.
    next_token_attribute: str, The name of the attribute in a response message
        holding the page token for the next page.

  Yields:
    protorpc.message.Message, The resources listed by the service.

  """
  request = copy.deepcopy(request)
  request.pageSize = batch_size
  request.pageToken = None
  while limit is None or limit:
    try:
      response = getattr(service, method)(request)
    except apitools_base.HttpError as error:
      raise calliope_exceptions.HttpException('RPC Failed: {0}'.format(
          dataflow_util.GetErrorMessage(error)))
    items = getattr(response, field)
    if predicate:
      items = filter(predicate, items)
    for item in items:
      yield item
      if limit is None:
        continue
      limit -= 1
      if not limit:
        return
    token = getattr(response, next_token_attribute)
    if not token:
      return
    setattr(request, current_token_attribute, token)
