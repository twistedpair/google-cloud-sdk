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

"""Backend service."""

import urlparse

from apitools.base.py import batch
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.api_lib.util import exceptions as api_exceptions
from googlecloudsdk.core import exceptions as core_exceptions

# Upper bound on batch size
# https://cloud.google.com/compute/docs/api/how-tos/batch
_BATCH_SIZE_LIMIT = 1000


class Error(core_exceptions.Error):
  """Errors raised by this module."""


def GetBatchUrl(endpoint_url):
  """Return a batch URL for the given endpoint URL."""
  parsed_endpoint = urlparse.urlparse(endpoint_url)
  return urlparse.urljoin(
      '{0}://{1}'.format(parsed_endpoint.scheme, parsed_endpoint.netloc),
      'batch/compute')


class ClientAdapter(object):
  """Encapsulates compute apitools interactions."""
  _API_NAME = 'compute'

  def __init__(self, api_default_version='v1', no_http=False, client=None):
    self._api_version = core_apis.ResolveVersion(
        self._API_NAME, api_default_version)
    self._client = client or core_apis.GetClientInstance(
        self._API_NAME, self._api_version, no_http=no_http)

    # Turn the endpoint into just the host.
    # eg. https://www.googleapis.com/compute/v1 -> https://www.googleapis.com
    endpoint_url = core_apis.GetEffectiveApiEndpoint(
        self._API_NAME, self._api_version)
    self._batch_url = GetBatchUrl(endpoint_url)

  @property
  def api_version(self):
    return self._api_version

  @property
  def apitools_client(self):
    return self._client

  @property
  def batch_url(self):
    return self._batch_url

  @property
  def messages(self):
    return self._client.MESSAGES_MODULE

  def MakeRequests(self, requests, errors_to_collect=None):
    """Sends given request in batch mode."""
    errors = errors_to_collect if errors_to_collect is not None else []
    objects = list(request_helper.MakeRequests(
        requests=requests,
        http=self._client.http,
        batch_url=self._batch_url,
        errors=errors))
    if errors_to_collect is None and errors:
      utils.RaiseToolException(
          errors, error_message='Could not fetch resource:')
    return objects

  def BatchRequests(self, requests, errors_to_collect=None):
    """Issues batch request for given set of requests.

    Args:
      requests: list(tuple(service, method, payload)), where
        service is apitools.base.py.base_api.BaseApiService,
        method is str, method name, e.g. 'Get', 'CreateInstance',
        payload is a subclass of apitools.base.protorpclite.messages.Message.
      errors_to_collect: list, output only, can be None, contains instances of
        api_exceptions.HttpException for each request with exception.
    Returns:
      list of responses, matching list of requests. Some responses can be
        errors.
    """
    batch_request = batch.BatchApiRequest(batch_url=self._batch_url)
    for service, method, request in requests:
      batch_request.Add(service, method, request)

    payloads = batch_request.Execute(self._client.http,
                                     max_batch_size=_BATCH_SIZE_LIMIT)

    responses = []
    errors = errors_to_collect if errors_to_collect is not None else []

    for payload in payloads:
      if payload.is_error:
        if isinstance(payload.exception, apitools_exceptions.HttpError):
          errors.append(api_exceptions.HttpException(payload.exception))
        else:
          errors.append(Error(payload.exception.message))

      responses.append(payload.response)

    return responses
