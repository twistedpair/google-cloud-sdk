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
""""Helpers for making batch requests."""
import json
import logging

from apitools.base.py import batch
from apitools.base.py import exceptions


def MakeRequests(requests, http, batch_url=None):
  """Makes batch requests.

  Args:
    requests: A list of tuples. Each tuple must be of the form
        (service, method, request object).
    http: An HTTP object.
    batch_url: The URL to which to send the requests.

  Returns:
    A tuple where the first element is a list of all objects returned
    from the calls and the second is a list of error messages.
  """
  logging.debug('Starting batch request...')
  batch_request = batch.BatchApiRequest(batch_url=batch_url)
  for service, method, request in requests:
    logging.debug('Adding request: %s', (service, method, request))
    batch_request.Add(service, method, request)

  logging.debug('Making batch request...')
  responses = batch_request.Execute(http)

  objects = []
  errors = []

  for response in responses:
    objects.append(response.response)

    if response.is_error:
      logging.debug('Error response: %s', response.exception)

      error_message = None
      if isinstance(response.exception, exceptions.HttpError):
        try:
          data = json.loads(response.exception.content)
          error_message = (
              response.exception.status_code,
              data.get('error', {}).get('message'))
        except ValueError:
          pass
        if not error_message:
          error_message = (response.exception.status_code,
                           response.exception.content)
      else:
        error_message = (None, response.exception.message)

      errors.append(error_message)

  logging.debug('Batch request done; responses %s', objects)
  return objects, errors
