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
"""Custom errors for SCC IaC Remediation."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions


class Error(exceptions.Error):
  """Base error for this module."""


class InvalidFindingNameError(Error):
  """An error respresenting an invalid finding canonical format name error."""

  def __init__(self, bad_finding_name: str):
    if bad_finding_name is None:
      super(Error, self).__init__('Missing finding canonical name.')
    else:
      super(Error, self).__init__(
          f"""Invalid finding canonical name: {bad_finding_name}
          Correct format: projects/*/sources/*/locations/*/findings/*"""
      )


class UnsupportedFindingCategoryError(Error):
  """An error representing an unsupported finding category error."""

  def __init__(self, invalid_category_name: str):
    if invalid_category_name is None:
      super(Error, self).__init__('Missing finding category name.')
    else:
      super(Error, self).__init__(
          f'Finding category not supported: {invalid_category_name}.'
      )


class FindingNotFoundError(Error):
  """An error representing a SCC finding not found error."""

  def __init__(self):
    super(Error, self).__init__(
        'Finding not found for the given name and organization.'
    )
