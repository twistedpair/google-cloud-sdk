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

from googlecloudsdk.api_lib.compute import operation_quota_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import exceptions as http_exception
from googlecloudsdk.core import properties


def _GenerateErrorMessage(exception):
  """Generate Error Message given exception."""
  error_message = None
  try:
    data = json.loads(exception.content)
    if isinstance(
        exception, exceptions.HttpError
    ) and utils.JsonErrorHasDetails(data):
      error_message = (
          exception.status_code,
          BuildMessageForErrorWithDetails(data),
      )
    else:
      error_message = (
          exception.status_code,
          data.get('error', {}).get('message'),
      )
  except ValueError:
    pass
  if not error_message:
    error_message = (exception.status_code, exception.content)
  return error_message


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
  # Catch all 403 forbidden errors and give a special
  # treatment to the "Compute API not enabled" error.
  except exceptions.HttpForbiddenError as exception:
    # check if gcloud should prompt
    if properties.VALUES.core.should_prompt_to_enable_api.GetBool():
      enablement_info = apis.GetApiEnablementInfo(exception)
      if enablement_info:
        project, service_token, enable_exception = enablement_info
        try:
          # prompt to enable then retry request
          apis.PromptToEnableApi(
              project, service_token, enable_exception, is_batch_request=True)
          response = getattr(service, method)(request=request_body)
          responses.append(response)
          return responses, errors
          # if not attempt enabled
        except http_exception.HttpException:
          pass
    error_message = _GenerateErrorMessage(exception)
    errors.append(error_message)
    return responses, errors
  except exceptions.HttpError as exception:
    # TODO(b/260144046): Add Enable Service Prompt and Retry.
    error_message = _GenerateErrorMessage(exception)
    errors.append(error_message)
  return responses, errors


# TODO(b/269805885): move to common formatter library
def BuildMessageForErrorWithDetails(json_data):
  if operation_quota_utils.IsJsonOperationQuotaError(
      json_data.get('error', {})
  ):
    return operation_quota_utils.CreateOperationQuotaExceededMsg(json_data)
  else:
    return json_data.get('error', {}).get('message')
