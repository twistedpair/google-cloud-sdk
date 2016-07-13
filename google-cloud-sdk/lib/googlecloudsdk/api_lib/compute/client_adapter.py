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

from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.core import apis as core_apis


class ClientAdapter(object):
  """Encapsulates compute apitools interactions."""
  _API_NAME = 'compute'

  def __init__(self, api_default_version='v1'):
    self._api_version = core_apis.ResolveVersion(
        self._API_NAME, api_default_version)
    self._client = core_apis.GetClientInstance(
        self._API_NAME, self._api_version)

    # Turn the endpoint into just the host.
    # eg. https://www.googleapis.com/compute/v1 -> https://www.googleapis.com
    endpoint_url = core_apis.GetEffectiveApiEndpoint(
        self._API_NAME, self._api_version)
    parsed_endpoint = urlparse.urlparse(endpoint_url)
    self._batch_url = urlparse.urljoin(
        '{0}://{1}'.format(parsed_endpoint.scheme, parsed_endpoint.netloc),
        'batch')

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
        errors=errors,
        custom_get_requests=None))
    if errors_to_collect is None and errors:
      utils.RaiseToolException(
          errors, error_message='Could not fetch resource:')
    return objects

