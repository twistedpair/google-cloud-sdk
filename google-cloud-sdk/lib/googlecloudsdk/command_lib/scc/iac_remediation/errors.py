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

from googlecloudsdk.api_lib.scc.iac_remediation import const
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


class GitRepoNotFoundError(Error):
  """An error representing a git repo not found error."""

  def __init__(self):
    super(Error, self).__init__(
        'Command is being invoked from a non-git repo'
    )


class InvalidGitConfigError(Error):
  """An error representing missing field in the git config file."""

  def __init__(self, missing_field: str):
    if missing_field is None:
      super(Error, self).__init__('Missing git config field name.')
    else:
      super(Error, self).__init__(
          f'Field missing from the git config file: {missing_field}.'
      )


class EmptyLLMResponseError(Error):
  """An error representing an invalid LLM response error."""

  def __init__(self):
    super(Error, self).__init__(
        'LLM response is empty.'
    )


class InvalidLLMResponseError(Error):
  """An error representing an invalid LLM response error."""

  def __init__(self, error_message: str):
    if error_message is None:
      super(Error, self).__init__('Invalid LLM response.')
    else:
      super(Error, self).__init__(f'Invalid LLM response: {error_message}')


class ExcessiveMembersError(Error):
  """An error representing an excessive members error."""

  def __init__(self, num_members: int):
    super(Error, self).__init__(
        f'Excessive members in the finding: {num_members}, expected atmost'
        f' {const.SUPPORTED_IAM_MEMBER_COUNT_LIMIT}.'
    )
