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

"""Library for obtaining API clients and messages."""

from googlecloudsdk.api_lib.util import resource as resource_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apis import apis_map


class UnknownAPIError(exceptions.Error):
  """Unable to find API in APIs map."""

  def __init__(self, api_name):
    super(UnknownAPIError, self).__init__(
        'API named [{0}] does not exist in the APIs map'.format(api_name))


class UnknownVersionError(exceptions.Error):
  """Unable to find API version in APIs map."""

  def __init__(self, api_name, api_version):
    super(UnknownVersionError, self).__init__(
        'The [{0}] API does not have version [{1}] in the APIs map'.format(
            api_name, api_version))


# This is the map of API name aliases to actual API names.
# Do not add to this map unless the api definition uses different names for api
# name, endpoint and/or collection names.
# The apis_map keys are aliases and values are actual API names.
# The rest of the Cloud SDK, including
# property sections, and command surfaces should use the API name alias.

# The general rule for this module is: all apis_map lookups should use the real
# API name, and all property lookups should use the alias. Any api_name argument
# expects to receive the name alias (if one exists). The _GetApiNameAndAlias
# helper method can be used to convert it into a (name, alias) tuple.
# TODO(b/31163851): remove the need for this alias map.
_API_NAME_ALIASES = {
    'sql': 'sqladmin',
}


def _GetApiNameAndAlias(api_name):
  return (_API_NAME_ALIASES.get(api_name, api_name), api_name)


def _CamelCase(snake_case):
  parts = snake_case.split('_')
  return ''.join(s.capitalize() for s in parts)


def ConstructApiDef(api_name,
                    api_version,
                    is_default,
                    base_pkg='googlecloudsdk.third_party.apis'):
  """Creates and returns the APIDef specified by the given arguments.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.
    is_default: bool, Whether this API version is the default.
    base_pkg: str, Base package from which generated API files are accessed.

  Returns:
    APIDef, The APIDef created using the given args.
  """
  api_name, _ = _GetApiNameAndAlias(api_name)
  client_cls_name = _CamelCase(api_name) + _CamelCase(api_version)
  class_path = '{base}.{api_name}.{api_version}'.format(
      base=base_pkg, api_name=api_name, api_version=api_version,)

  common_fmt = '{api_name}_{api_version}_'
  client_cls_path_fmt = common_fmt + 'client.{api_client_class}'
  client_cls_path = client_cls_path_fmt.format(api_name=api_name,
                                               api_version=api_version,
                                               api_client_class=client_cls_name)

  messages_mod_path_fmt = common_fmt + 'messages'
  messages_mod_path = messages_mod_path_fmt.format(api_name=api_name,
                                                   api_version=api_version)
  return apis_map.APIDef(class_path, client_cls_path,
                         messages_mod_path, is_default)


def AddToApisMap(api_name, api_version, default=None,
                 base_pkg='googlecloudsdk.third_party.apis'):
  """Adds the APIDef specified by the given arguments to the APIs map.

  This method should only be used for runtime patcing of the APIs map. Additions
  to the map should ensure that there is only one and only one default version
  for each API.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.
    default: bool, Whether this API version is the default. If set to None
      will be set to True if this is first version of api, otherwise false.
    base_pkg: str, Base package from which generated API files are accessed.
  """
  api_name, _ = _GetApiNameAndAlias(api_name)
  api_def = ConstructApiDef(api_name, api_version, default, base_pkg)
  api_versions = apis_map.MAP.get(api_name, {})
  if default is None:
    api_def.default_version = not api_versions
  api_versions[api_version] = api_def
  apis_map.MAP[api_name] = api_versions


def GetDefaultVersion(api_name):
  api_name, _ = _GetApiNameAndAlias(api_name)
  api_vers = apis_map.MAP.get(api_name, {})
  for ver, api_def in api_vers.iteritems():
    if api_def.default_version:
      return ver
  return None


def SetDefaultVersion(api_name, api_version):
  """Resets default version for given api."""
  api_def = _GetApiDef(api_name, api_version)
  default_version = GetDefaultVersion(api_name)
  default_api_def = _GetApiDef(api_name, default_version)
  default_api_def.default_version = False
  api_def.default_version = True


def GetApiNames():
  """Returns list of avaibleable apis, ignoring the version."""
  return sorted(apis_map.MAP.keys())


def GetVersions(api_name):
  """Return available versions for given api.

  Args:
    api_name: str, The API name (or the command surface name, if different).

  Raises:
    UnknownAPIError: If api_name does not exist in the APIs map.

  Returns:
    list, of version names.
  """
  api_name, _ = _GetApiNameAndAlias(api_name)
  version_map = apis_map.MAP.get(api_name, None)
  if version_map is None:
    raise UnknownAPIError(api_name)
  return version_map.keys()


def ResolveVersion(api_name, default_override=None):
  """Resolves the version for an API based on the APIs map and API overrides.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    default_override: str, The override for the default version.

  Raises:
    UnknownAPIError: If api_name does not exist in the APIs map.

  Returns:
    str, The resolved version.
  """
  api_name, api_name_alias = _GetApiNameAndAlias(api_name)
  if api_name not in apis_map.MAP:
    raise UnknownAPIError(api_name)

  version_overrides = properties.VALUES.api_client_overrides.AllValues()
  version_override = version_overrides.get(api_name_alias, None)
  return version_override or default_override or GetDefaultVersion(api_name)


def _GetApiDef(api_name, api_version):
  """Returns the APIDef for the specified API and version.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.

  Raises:
    UnknownAPIError: If api_name does not exist in the APIs map.
    UnknownVersionError: If api_version does not exist for given api_name in the
    APIs map.

  Returns:
    APIDef, The APIDef for the specified API and version.
  """
  api_name, api_name_alias = _GetApiNameAndAlias(api_name)
  if api_name not in apis_map.MAP:
    raise UnknownAPIError(api_name)

  version_overrides = properties.VALUES.api_client_overrides.AllValues()
  version_override = version_overrides.get(api_name_alias, None)
  api_version = version_override or api_version

  api_versions = apis_map.MAP[api_name]
  if api_version is None or api_version not in api_versions:
    raise UnknownVersionError(api_name, api_version)
  else:
    api_def = api_versions[api_version]

  return api_def


def GetClientClass(api_name, api_version):
  """Returns the client class for the API specified in the args.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.

  Returns:
    base_api.BaseApiClient, Client class for the specified API.
  """
  api_def = _GetApiDef(api_name, api_version)

  module_path, client_class_name = api_def.client_full_classpath.rsplit('.', 1)
  module_obj = __import__(module_path, fromlist=[client_class_name])
  return getattr(module_obj, client_class_name)


def GetClientInstance(api_name, api_version, no_http=False):
  """Returns an instance of the API client specified in the args.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.
    no_http: bool, True to not create an http object for this client.

  Returns:
    base_api.BaseApiClient, An instance of the specified API client.
  """
  # pylint: disable=g-import-not-at-top
  if no_http:
    http_client = None
  else:
    # Import http only when needed, as it depends on credential infrastructure
    # which is not needed in all cases.
    from googlecloudsdk.core.credentials import http
    http_client = http.Http()

  client_class = GetClientClass(api_name, api_version)
  return client_class(
      url=GetEffectiveApiEndpoint(api_name, api_version, client_class),
      get_credentials=False,
      http=http_client)


def GetEffectiveApiEndpoint(api_name, api_version, client_class=None):
  """Returns effective endpoint for given api."""
  endpoint_overrides = properties.VALUES.api_endpoint_overrides.AllValues()
  endpoint_override = endpoint_overrides.get(api_name, '')
  if endpoint_override:
    return endpoint_override
  client_class = client_class or GetClientClass(api_name, api_version)
  return client_class.BASE_URL


def GetDefaultEndpointUrl(url):
  """Looks up default endpoint based on overridden endpoint value."""
  endpoint_overrides = properties.VALUES.api_endpoint_overrides.AllValues()
  for api_name, overridden_url in endpoint_overrides.iteritems():
    if url.startswith(overridden_url):
      api_version = GetDefaultVersion(api_name)
      return (GetClientClass(api_name, api_version).BASE_URL +
              url[len(overridden_url):])
  return url


def GetMessagesModule(api_name, api_version):
  """Returns the messages module for the API specified in the args.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.

  Returns:
    Module containing the definitions of messages for the specified API.
  """
  api_def = _GetApiDef(api_name, api_version)
  # fromlist below must not be empty, see:
  # http://stackoverflow.com/questions/2724260/why-does-pythons-import-require-fromlist.
  return __import__(api_def.messages_full_modulepath, fromlist=['something'])


def GetResourceModule(api_name, api_version):
  """Imports and returns given api resources module."""

  api_def = _GetApiDef(api_name, api_version)
  # fromlist below must not be empty, see:
  # http://stackoverflow.com/questions/2724260/why-does-pythons-import-require-fromlist.
  return __import__(api_def.class_path + '.' + 'resources',
                    fromlist=['something'])


def GetApiCollections(api_name, api_version):
  """Yields all collections for for given api."""

  try:
    resources_module = GetResourceModule(api_name, api_version)
  except ImportError:
    pass
  else:
    for collection in resources_module.Collections:
      yield resource_util.CollectionInfo(
          api_name,
          api_version,
          resources_module.BASE_URL,
          collection.collection_name,
          collection.path,
          collection.flat_paths,
          collection.params)
