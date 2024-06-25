# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Errors for Fleet memberships commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions


class InvalidFlagValueError(exceptions.Error):
  """An error raised when a flag is given an invalid argument."""

  def __init__(self, msg):
    message = 'Invalid flag value: {}'.format(msg)
    super(InvalidFlagValueError, self).__init__(message)


class InvalidComplianceMode(InvalidFlagValueError):
  """An error raised when the caller specifies an invalid Compliance mode."""


class MutuallyExclusiveFlags(InvalidFlagValueError):
  """An error raised when the caller specifies mutually exclusive flags."""


class ConfiguringDisabledCompliance(MutuallyExclusiveFlags):
  """Compliance does not support disabling and configuring standards at once.

  This error is raised when the caller tries to specify the compliance mode of
  disabled along with compliance standards configuration at the same time.
  """
