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

"""Utilities for the gcloud meta apis surface."""

from googlecloudsdk.api_lib.util import apis_internal
from googlecloudsdk.core import exceptions
from googlecloudsdk.third_party.apis import apis_map


class Error(exceptions.Error):
  pass


class UnknownCollectionError(Error):

  def __init__(self, api_name, api_version, collection):
    super(UnknownCollectionError, self).__init__(
        'Collection [{collection}] does not exist for [{api}] [{version}].'
        .format(collection=collection, api=api_name, version=api_version)
    )


class API(object):
  """A data holder for returning API data for display."""

  def __init__(self, name, version, is_default, base_url):
    self.name = name
    self.version = version
    self.is_default = is_default
    self.base_url = base_url


class APICollection(object):
  """A data holder for collection information for an API."""

  def __init__(self, collections_info):
    self.api_name = collections_info.api_name
    self.api_version = collections_info.api_version
    self.base_url = collections_info.base_url
    self.name = collections_info.name
    self.path = collections_info.GetPath('')
    self.params = collections_info.GetParams('')


def GetAPI(api_name, api_version):
  """Get a specific API definition.

  Args:
    api_name: str, The name of the API.
    api_version: str, The version string of the API.

  Returns:
    API, The API definition.
  """
  # pylint: disable=protected-access
  api_def = apis_internal._GetApiDef(api_name, api_version)
  api_client = apis_internal._GetClientClassFromDef(api_def)
  return API(api_name, api_version,
             api_def.default_version, api_client.BASE_URL)


def GetAllAPIs():
  """Gets all registered APIs.

  Returns:
    [API], A list of API definitions.
  """
  all_apis = []
  for api_name, versions in apis_map.MAP.iteritems():
    for api_version, _ in versions.iteritems():
      all_apis.append(GetAPI(api_name, api_version))
  return all_apis


def GetAPICollections(api_name, api_version):
  """Gets the registered collections for the given API version.

  Args:
    api_name: str, The name of the API.
    api_version: str, The version string of the API.

  Returns:
    [APICollection], A list of the registered collections.
  """
  # pylint:disable=protected-access
  return [APICollection(c)
          for c in apis_internal._GetApiCollections(api_name, api_version)]


def GetAPICollection(api_name, api_version, collection):
  """Gets the given collection for the given API version.

  Args:
    api_name: str, The name of the API.
    api_version: str, The version string of the API.
    collection: str, The collection to get.

  Returns:
    APICollection, The requested API collection.

  Raises:
    UnknownCollectionError: If the collection does not exist for the given API
    and version.
  """
  collections = GetAPICollections(api_name, api_version)
  for c in collections:
    if c.name == collection:
      return c
  raise UnknownCollectionError(api_name, api_version, collection)
