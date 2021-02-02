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
"""Utilities for defining Tag resource manager arguments on a parser."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py.exceptions import HttpForbiddenError
from googlecloudsdk.api_lib.resource_manager import tags
from googlecloudsdk.api_lib.resource_manager.exceptions import ResourceManagerError


class InvalidInputError(ResourceManagerError):
  """Exception for invalid input."""

GetResourceFns = {
    'tagKeys': tags.TagMessages().CloudresourcemanagerTagKeysGetRequest,
    'tagValues': tags.TagMessages().CloudresourcemanagerTagValuesGetRequest
}

ListResourceFns = {
    'tagKeys': tags.TagMessages().CloudresourcemanagerTagKeysListRequest,
    'tagValues': tags.TagMessages().CloudresourcemanagerTagValuesListRequest
}

ServiceFns = {
    'tagKeys': tags.TagKeysService,
    'tagValues': tags.TagValuesService,
    'tagBindings': tags.TagBindingsService
}


def GetTagKeyFromNamespacedName(namespaced_name):
  """Gets the tag key from the namespaced name.

  Args:
    namespaced_name: Could be the resource name or namespaced name

  Returns:
    TagKey resource

  Raises:
    InvalidInputError: bad input
  """
  service = ServiceFns['tagKeys']()

  parts = namespaced_name.split('/')
  if len(parts) != 2:
    raise InvalidInputError(
        'TagKey namespaced name [{}] invalid'.format(namespaced_name))

  name = '/'.join(['organizations', parts[0]])
  req = ListResourceFns['tagKeys'](parent=name)

  try:
    response = service.List(req)
  except HttpForbiddenError:
    print('TagKey [{}] does not exist or user does not have permissions to '
          'resolve namespaced name. Retry using tagKey\'s resource name, such '
          'as tagKeys/123.'.format(namespaced_name))
    raise

  for key in response.tagKeys:
    if key.namespacedName == namespaced_name:
      return key

  raise InvalidInputError('TagKey [{}] not found'.format(namespaced_name))


def GetTagValueFromNamespacedName(namespaced_name):
  """Gets the tag value from the namespaced name.

  Args:
    namespaced_name: Could be the resource name or namespaced name

  Returns:
    TagValue resource

  Raises:
    InvalidInputError: bad input
  """

  service = ServiceFns['tagValues']()

  parts = namespaced_name.split('/')
  if len(parts) != 3:
    raise InvalidInputError(
        'TagValue namespaced name [{}] invalid'.format(namespaced_name))

  name = GetTagKeyFromNamespacedName('/'.join(parts[:2])).name

  req = ListResourceFns['tagValues'](parent=name)
  response = service.List(req)

  for value in response.tagValues:
    if value.namespacedName == namespaced_name:
      return value

  raise InvalidInputError('TagValue [{}] not found'.format(namespaced_name))


def GetResourceFromNamespacedName(namespaced_name, resource_type):
  """Gets the resource from the namespaced name.

  Args:
    namespaced_name: Could be the resource name or namespaced name
    resource_type: the type of the resource ie: 'tagKeys', 'tagValues'. Used to
      determine which GET function to call

  Returns:
    resource
  """
  service = ServiceFns[resource_type]()
  req = GetResourceFns[resource_type](name=namespaced_name)
  response = service.Get(req)

  return response

