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
"""Errors for GKE Hub memberships commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions


class InsufficientPermissionsError(exceptions.Error):
  """An error raised when the caller does not have sufficient permissions."""

  def __init__(self):
    message = "Caller doesn't have sufficient permissions."
    super(InsufficientPermissionsError, self).__init__(message)


class UnknownApiEndpointOverrideError(exceptions.Error):
  """An error raised for an invalid value for `api_endpoint_overrides`."""

  def __init__(self, api_name):
    message = 'Unknown api_endpoint_overrides value for {}'.format(api_name)
    super(UnknownApiEndpointOverrideError, self).__init__(message)
