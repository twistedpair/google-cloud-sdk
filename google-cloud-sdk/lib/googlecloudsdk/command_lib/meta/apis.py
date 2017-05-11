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
from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.apis import apis_map


API_VERSION_FLAG = base.Argument(
    '--api-version',
    help='The version of the given API to use. If not provided, the default '
         'version of the API will be used.')


NAME_SEPARATOR = '.'


class Error(exceptions.Error):
  pass


class NoDefaultVersionError(Error):

  def __init__(self, api_name):
    super(NoDefaultVersionError, self).__init__(
        'API [{api}] does not have a default version. You must specify which '
        'version to use.'.format(api=api_name)
    )


class UnknownCollectionError(Error):

  def __init__(self, api_name, api_version, collection):
    super(UnknownCollectionError, self).__init__(
        'Collection [{collection}] does not exist for [{api}] [{version}].'
        .format(collection=collection, api=api_name, version=api_version)
    )


class UnknownMethodError(Error):

  def __init__(self, method, collection):
    super(UnknownMethodError, self).__init__(
        'Method [{method}] does not exist for collection [{collection}].'
        .format(method=method, collection=collection)
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

  def __init__(self, collection_info):
    self.api_name = collection_info.api_name
    self.api_version = collection_info.api_version
    self.base_url = collection_info.base_url
    self.name = collection_info.name
    self.full_name = collection_info.full_name
    self.detailed_path = collection_info.GetPath('')
    self.detailed_params = collection_info.GetParams('')
    self.path = collection_info.path
    self.params = collection_info.params


class APIMethod(object):
  """A data holder for method information for an API collection."""

  def __init__(self, service, name, api_collection, method_config):
    self._service = service
    self._method_name = name

    self.collection = api_collection

    self.name = method_config.method_id
    dotted_path = self.collection.full_name + NAME_SEPARATOR
    if self.name.startswith(dotted_path):
      self.name = self.name[len(dotted_path):]

    self.path = _RemoveVersionPrefix(
        self.collection.api_version, method_config.relative_path)
    self.params = method_config.path_params
    self.detailed_path = _RemoveVersionPrefix(
        self.collection.api_version, method_config.flat_path)

    self.http_method = method_config.http_method
    self.request_type = method_config.request_type_name
    self.response_type = method_config.response_type_name

  def GetRequestType(self):
    """Gets the apitools request class for this method."""
    return self._service.GetRequestType(self._method_name)

  def Call(self, *args, **kwargs):
    """Executes this method with the given arguments."""
    return getattr(self._service, self._method_name)(*args, **kwargs)


def _RemoveVersionPrefix(api_version, path):
  """Trims the version number off the front of a URL path if present."""
  if not path:
    return None
  if path.startswith(api_version):
    return path[len(api_version) + 1:]
  return path


def GetAPI(api_name, api_version=None):
  """Get a specific API definition.

  Args:
    api_name: str, The name of the API.
    api_version: str, The version string of the API.

  Returns:
    API, The API definition.
  """
  api_version = api_version or _GetDefaultVersion(api_name)
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


def _SplitFullCollectionName(collection):
  return tuple(collection.split(NAME_SEPARATOR, 1))


def GetAPICollections(api_name=None, api_version=None):
  """Gets the registered collections for the given API version.

  Args:
    api_name: str, The name of the API or None for all apis.
    api_version: str, The version string of the API or None to use the default
      version.

  Returns:
    [APICollection], A list of the registered collections.
  """
  if api_name:
    all_apis = {api_name: api_version or _GetDefaultVersion(api_name)}
  else:
    all_apis = {x.name: x.version for x in GetAllAPIs() if x.is_default}

  collections = []
  for n, v in all_apis.iteritems():
    # pylint:disable=protected-access
    collections.extend(
        [APICollection(c) for c in apis_internal._GetApiCollections(n, v)])
  return collections


def GetAPICollection(full_collection_name, api_version=None):
  """Gets the given collection for the given API version.

  Args:
    full_collection_name: str, The collection to get including the api name.
    api_version: str, The version string of the API or None to use the default
      for this API.

  Returns:
    APICollection, The requested API collection.

  Raises:
    UnknownCollectionError: If the collection does not exist for the given API
    and version.
  """
  api_name, collection = _SplitFullCollectionName(full_collection_name)
  api_version = api_version or _GetDefaultVersion(api_name)
  collections = GetAPICollections(api_name, api_version)
  for c in collections:
    if c.name == collection:
      return c
  raise UnknownCollectionError(api_name, api_version, collection)


def _GetDefaultVersion(api_name):
  """Gets the default version for the given api."""
  # pylint:disable=protected-access
  api_version = apis_internal._GetDefaultVersion(api_name)
  if not api_version:
    raise NoDefaultVersionError(api_name)
  log.warning('Using default version [{}] for api [{}].'
              .format(api_version, api_name))
  return api_version


def GetMethod(full_collection_name, method, api_version=None, no_http=True):
  """Gets the specification for the given API method.

  Args:
    full_collection_name: str, The collection including the api name.
    method: str, The name of the method.
    api_version: str, The version string of the API or None to use the default
      for this API.
    no_http: bool, True to not create an authenticated http object for this
      API Client.

  Returns:
    APIMethod, The method specification.

  Raises:
    UnknownMethodError: If the method does not exist on the collection.
  """
  methods = GetMethods(full_collection_name, api_version=api_version,
                       no_http=no_http)
  for m in methods:
    if m.name == method:
      return m
  raise UnknownMethodError(method, full_collection_name)


def GetMethods(full_collection_name, api_version=None, no_http=True):
  """Gets all the methods available on the given collection.

  Args:
    full_collection_name: str, The collection including the api name.
    api_version: str, The version string of the API or None to use the default
      for this API.
    no_http: bool, True to not create an authenticated http object for this
      API Client.

  Returns:
    [APIMethod], The method specifications.
  """
  api_name, collection = _SplitFullCollectionName(full_collection_name)
  api_version = api_version or _GetDefaultVersion(api_name)
  # pylint:disable=protected-access
  client = apis_internal._GetClientInstance(api_name, api_version,
                                            no_http=no_http)
  api_collection = GetAPICollection(full_collection_name,
                                    api_version=api_version)
  service = getattr(client, collection.replace(NAME_SEPARATOR, '_'))

  method_names = service.GetMethodsList()
  method_configs = [(name, service.GetMethodConfig(name))
                    for name in method_names]
  return [APIMethod(service, name, api_collection, config)
          for name, config in method_configs]
