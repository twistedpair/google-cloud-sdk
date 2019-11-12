# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Utilities for defining Label Manager arguments on a parser."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.labelmanager import service as labelmanager
from googlecloudsdk.core import exceptions


class LabelManagerError(exceptions.Error):
  """Top-level exception for Label Manager errors."""


class InvalidInputError(LabelManagerError):
  """Exception for invalid input."""


def GetLabelKeyFromDisplayName(display_name, label_parent):
  """Returns the LabelKey with display_name under label_parent if it exists.

  Args:
    display_name: String, display name of the LabelKey
    label_parent: String, resource name of the parent of the LabelKey

  Raises:
    InvalidInputError: if the specified display_name does not exist under the
    label_parent

  Returns:
    The resource name of the LabelKey associated with the display_name
  """
  labelkeys_service = labelmanager.LabelKeysService()
  labelmanager_messages = labelmanager.LabelManagerMessages()

  list_request = labelmanager_messages.LabelmanagerLabelKeysListRequest(
      parent=label_parent)
  response = labelkeys_service.List(list_request)

  for key in response.keys:
    if key.displayName == display_name:
      return key.name

  raise InvalidInputError(
      'Invalid display_name for label key [{}] in parent [{}]'.format(
          display_name, label_parent))


def GetLabelValueFromDisplayName(display_name, label_key):
  """Returns the LabelValue with display_name under label_key if it exists.

  Args:
    display_name: String, display name of the LabelValue
    label_key: String, resource name of the parent of the LabelKey

  Raises:
    InvalidInputError: if the specified display_name does not exist under the
    label_key

  Returns:
    The resource name of the LabelValue associated with the display_name
  """
  labelvalues_service = labelmanager.LabelValuesService()
  labelmanager_messages = labelmanager.LabelManagerMessages()

  list_request = labelmanager_messages.LabelmanagerLabelValuesListRequest(
      parent=label_key)
  response = labelvalues_service.List(list_request)

  for value in response.values:
    if value.displayName == display_name:
      return value.name

  raise InvalidInputError(
      'Invalid display_name for label value [{}] in parent [{}]'.format(
          display_name, label_key))
