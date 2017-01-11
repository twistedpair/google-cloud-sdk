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

from apitools.base.py import batch
from apitools.base.py import exceptions

# Upper bound on batch size
# https://cloud.google.com/compute/docs/api/how-tos/batch
_BATCH_SIZE_LIMIT = 1000


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
  batch_request = batch.BatchApiRequest(batch_url=batch_url)
  for service, method, request in requests:
    batch_request.Add(service, method, request)

  responses = batch_request.Execute(http, max_batch_size=_BATCH_SIZE_LIMIT)

  objects = []
  errors = []

  for response in responses:
    objects.append(response.response)

    if response.is_error:
      # TODO(b/33771874): Use HttpException to decode error payloads.
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

  return objects, errors
