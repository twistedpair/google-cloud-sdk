# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Helpers for making single request requests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json

from apitools.base.py import exceptions


def MakeSingleRequest(service, method, request_body):
  """Makes single request.

  Args:
    service: a BaseApiService Object.
    method: a string of method name.
    request_body: a protocol buffer requesting the requests.

  Returns:
    a length-one response list and error list.
  """
  responses, errors = [], []
  try:
    response = getattr(service, method)(request=request_body)
    responses.append(response)
  except exceptions.HttpError as exception:

    # TODO(b/260144046): Add Enable Service Prompt and Retry.
    error_message = None
    try:
      data = json.loads(exception.content)
      error_message = (exception.status_code, data.get('error',
                                                       {}).get('message'))
    except ValueError:
      pass
    if not error_message:
      error_message = (exception.status_code, exception.content)
    errors.append(error_message)
  return responses, errors
