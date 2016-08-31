# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Utilities for cloud resources."""


class CollectionInfo(object):
  """Holds information about a resource collection.

  Attributes:
      api_name: str, name of the api of resources parsed by this parser.
      api_version: str, version id for this api.
      path: str, URI template for this resource.
      params: list(str), description of parameters in the path.
      request_type:  apitools.base.protorpclite.messages.Message, Message type
        for Get request.
      name: str, collection name for this resource without leading api_name.
      base_url: str, URL for service providing these resources.
  """

  def __init__(self, api_name, api_version, base_url, name,
               request_type, path, params):
    self.api_name = api_name
    self.api_version = api_version
    self.base_url = base_url
    self.name = name
    self.request_type = request_type
    self.path = path
    self.params = params

  @property
  def full_name(self):
    return self.api_name + '.'  + self.name

  def __cmp__(self, other):
    return cmp((self.api_name, self.api_version, self.name),
               (other.api_name, other.api_version, other.name))

  def __str__(self):
    return self.full_name
