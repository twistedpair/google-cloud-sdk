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
"""Utilities for dealing with ML predict API."""

import json

from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core.credentials import http


class InstancesEncodeError(core_exceptions.Error):
  """Indicates that error occurs while decoding the instances in http body."""
  pass


class HttpRequestFailError(core_exceptions.Error):
  """Indicates that the http request fails in some way."""
  pass


def Predict(model_or_version_ref, instances):
  """Performs online prediction on the input data file.

  Args:
      model_or_version_ref: a Resource representing either a model or a version.
      instances: a list of JSON or UTF-8 encoded instances to perform
          prediction on.

  Returns:
      A json object that contains predictions.

  Raises:
      HttpRequestFailError: if error happens with http request, or parsing
          the http response.
  """
  url = model_or_version_ref.SelfLink() + ':predict'
  # Construct the body for the predict request.
  headers = {'Content-Type': 'application/json'}
  try:
    body = json.dumps({'instances': instances}, sort_keys=True)
  except UnicodeDecodeError:
    raise InstancesEncodeError('Instances cannot be JSON encoded, probably '
                               'because the input is not utf-8 encoded.')

  # Workaround since current gcloud sdk cannot handle the httpbody properly.
  # TODO(b/31403673): use MlV1.ProjectsService.Predict once b/31403673
  # is fixed.
  response, response_body = http.Http().request(
      uri=url, method='POST', body=body, headers=headers)
  if response.get('status') != '200':
    raise HttpRequestFailError('HTTP request failed. Response: ' +
                               response_body)
  try:
    return json.loads(response_body)
  except ValueError:
    raise HttpRequestFailError('No JSON object could be decoded from the '
                               'HTTP response body: ' + response_body)
