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

from googlecloudsdk.api_lib.resource_manager import tags
from googlecloudsdk.api_lib.resource_manager.exceptions import ResourceManagerError


class InvalidInputError(ResourceManagerError):
  """Exception for invalid input."""

ResourceFns = {
    'tagKeys': tags.TagMessages().CloudresourcemanagerTagKeysGetRequest,
    'tagValues': tags.TagMessages().CloudresourcemanagerTagValuesGetRequest
}

ServiceFns = {
    'tagKeys': tags.TagKeysService,
    'tagValues': tags.TagValuesService
}


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
  req = ResourceFns[resource_type](name=namespaced_name)
  response = service.Get(req)

  return response

