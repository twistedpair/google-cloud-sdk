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
"""Utilities for Multicloud errors."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions


class UnknownApiEndpointOverride(exceptions.Error):
  """Class for errors by unknown endpoint override."""

  def __init__(self, api_name):
    message = 'Unknown api_endpoint_overrides value for {}'.format(api_name)
    super(UnknownApiEndpointOverride, self).__init__(message)


class MissingClusterField(exceptions.Error):
  """Class for errors by missing cluster fields."""

  def __init__(self, field):
    message = 'Cluster is missing field {}'.format(field)
    super(MissingClusterField, self).__init__(message)


class UnsupportedClusterVersion(exceptions.Error):
  """Class for errors by unsupported cluster versions."""

