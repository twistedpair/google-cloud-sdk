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

from googlecloudsdk.api_lib.util import apis_internal
from googlecloudsdk.api_lib.util import apis_util
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apis import apis_map


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
  # pylint:disable=protected-access
  api_name, _ = apis_internal._GetApiNameAndAlias(api_name)
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
  # pylint:disable=protected-access
  api_name, _ = apis_internal._GetApiNameAndAlias(api_name)
  api_def = ConstructApiDef(api_name, api_version, default, base_pkg)
  api_versions = apis_map.MAP.get(api_name, {})
  if default is None:
    api_def.default_version = not api_versions
  api_versions[api_version] = api_def
  apis_map.MAP[api_name] = api_versions


def SetDefaultVersion(api_name, api_version):
  """Resets default version for given api."""
  # pylint:disable=protected-access
  api_def = apis_internal._GetApiDef(api_name, api_version)
  # pylint:disable=protected-access
  default_version = apis_internal._GetDefaultVersion(api_name)
  # pylint:disable=protected-access
  default_api_def = apis_internal._GetApiDef(api_name, default_version)
  default_api_def.default_version = False
  api_def.default_version = True


def GetVersions(api_name):
  """Return available versions for given api.

  Args:
    api_name: str, The API name (or the command surface name, if different).

  Raises:
    UnknownAPIError: If api_name does not exist in the APIs map.

  Returns:
    list, of version names.
  """
  # pylint:disable=protected-access
  return apis_internal._GetVersions(api_name)


def ResolveVersion(api_name, default_override=None):
  """Resolves the version for an API based on the APIs map and API overrides.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    default_override: str, The override for the default version.

  Raises:
    apis_internal.UnknownAPIError: If api_name does not exist in the APIs map.

  Returns:
    str, The resolved version.
  """
  # pylint:disable=protected-access
  api_name, api_name_alias = apis_internal._GetApiNameAndAlias(api_name)
  if api_name not in apis_map.MAP:
    raise apis_util.UnknownAPIError(api_name)

  version_overrides = properties.VALUES.api_client_overrides.AllValues()
  version_override = version_overrides.get(api_name_alias, None)
  return (version_override or default_override or
          # pylint:disable=protected-access
          apis_internal._GetDefaultVersion(api_name))


def GetClientClass(api_name, api_version):
  """Returns the client class for the API specified in the args.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.

  Returns:
    base_api.BaseApiClient, Client class for the specified API.
  """
  # pylint:disable=protected-access
  return apis_internal._GetClientClass(api_name, api_version)


def GetClientInstance(api_name, api_version, no_http=False):
  """Returns an instance of the API client specified in the args.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.
    no_http: bool, True to not create an http object for this client.

  Returns:
    base_api.BaseApiClient, An instance of the specified API client.
  """
  # pylint:disable=protected-access
  return apis_internal._GetClientInstance(api_name, api_version, no_http)


def GetEffectiveApiEndpoint(api_name, api_version, client_class=None):
  """Returns effective endpoint for given api."""
  # pylint:disable=protected-access
  return apis_internal._GetEffectiveApiEndpoint(api_name,
                                                api_version,
                                                client_class)


def GetMessagesModule(api_name, api_version):
  """Returns the messages module for the API specified in the args.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.

  Returns:
    Module containing the definitions of messages for the specified API.
  """
  # pylint:disable=protected-access
  api_def = apis_internal._GetApiDef(api_name, api_version)
  # fromlist below must not be empty, see:
  # http://stackoverflow.com/questions/2724260/why-does-pythons-import-require-fromlist.
  return __import__(api_def.messages_full_modulepath, fromlist=['something'])
