# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Errors for the compute VM instances Ops Agents policy commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions

import six


class OpsAgentsPolicyValidationError(exceptions.Error):
  """Raised when Ops agent policy validation fails."""


class OpsAgentsPolicyValidationMultiError(OpsAgentsPolicyValidationError):
  """Raised when multiple Ops agent policy validations fail."""

  def __init__(self, errors):
    super(OpsAgentsPolicyValidationMultiError, self).__init__(
        ' | '.join(six.text_type(error) for error in errors))
    self.errors = errors
