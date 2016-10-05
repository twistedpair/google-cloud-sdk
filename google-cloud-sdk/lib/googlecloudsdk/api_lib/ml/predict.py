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

from googlecloudsdk.core import apis
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core.credentials import http


class InvalidInstancesFileError(core_exceptions.Error):
  """Indicates that the input file was invalid in some way."""
  pass


class HttpRequestFailError(core_exceptions.Error):
  """Indicates that the http request fails in some way."""
  pass


def Predict(model_name=None, version_name=None, input_file=None):
  """Perform online prediction on the input data file.

  Args:
      model_name: name of the model.
      version_name: name of the version.
      input_file: An open file object for the input file.
  Returns:
      A json object that contains predictions.
  Raises:
      InvalidInstancesFileError: if the input_file is empty, ill-formatted,
          or contains more than 100 instances.
      HttpRequestFailError: if error happens with http request, or parsing
          the http response.
  """

  # Get the url for the predict request.
  project_id = properties.VALUES.core.project.Get()
  # TODO(b/31504982): use Resources.SelfLink() to get the url
  # once b/31504982 is fixed.
  model_version = '{0}/models/{1}'.format(project_id, model_name)
  if version_name:
    model_version += '/versions/{0}'.format(version_name)
  url = (apis.GetEffectiveApiEndpoint('ml', 'v1beta1') + 'v1beta1/projects/' +
         model_version + ':predict')

  # Read the instances from input file
  instances = []
  cnt = 0
  for cnt, line in enumerate(input_file):
    if cnt > 100:
      raise InvalidInstancesFileError(
          'Online prediction can process no more than 100 '
          'instances per file. Please use batch prediction instead.')
    try:
      instances.append(json.loads(line.rstrip('\n')))
    except ValueError:
      raise InvalidInstancesFileError('Input instances must be in JSON format.'
                                      ' See "gcloud beta ml predict --help".')

  if not instances:
    raise InvalidInstancesFileError('Input file is empty.')

  # Construct the body for the predict request.
  body = {'instances': instances}

  headers = {'Content-Type': 'application/json'}
  # Workaround since current gcloud sdk cannot handle the httpbody properly.
  # TODO(b/31403673): use M1V1beta1.ProjectsService.Predict once b/31403673
  # is fixed.
  response, response_body = http.Http().request(
      uri=url, method='POST', body=json.dumps(body), headers=headers)
  if response.get('status') != '200':
    raise HttpRequestFailError('HTTP request failed. Response: ' +
                               response_body)
  try:
    return json.loads(response_body)
  except ValueError:
    raise HttpRequestFailError('No JSON object could be decoded from the '
                               'HTTP response body: ' + response_body)
