# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utilities for retrying requests on failures."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import http_wrapper as apitools_http_wrapper
from googlecloudsdk.api_lib.storage import errors


def set_retry_func(apitools_transfer_object):
  """Sets the retry function for the apitools transfer object.

  Replaces the Apitools' default retry function
  HandleExceptionsAndRebuildHttpConnections with a custom one which calls
  HandleExceptionsAndRebuildHttpConnections and then raise a custom exception.
  This is useful when we don't want MakeRequest method in Apitools to retry
  the http request directly and instead let the caller decide the next action.

  Args:
    apitools_transfer_object (apitools.base.py.transfer.Transfer): The
    Apitools' transfer object.
  """
  def _handle_error_and_raise(retry_args):
    # HandleExceptionsAndRebuildHttpConnections will re-raise any exception
    # that cannot be handled. For example, 404, 500, etc.
    apitools_http_wrapper.HandleExceptionsAndRebuildHttpConnections(retry_args)

    # If it did not raise any error, we want to raise a custom error to
    # inform the caller to retry the request.
    raise errors.RetryableApiError()
  apitools_transfer_object.retry_func = _handle_error_and_raise
