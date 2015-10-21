# Copyright 2015 Google Inc. All Rights Reserved.

"""Generates Cloud SDK util code for apitools generated clients/messages."""

import os


# TODO(vilasj): Move out of the scripts directory so it can be used elsewhere.
class APIDef(object):
  """Struct for info required to instantiate clients/messages for API versions.

  Attributes:
    client_classpath: str, Path to the client class for an API version.
    messages_modulepath: str, Path to the messages module for an API version.
    default: bool, Whether this API version is the default version for the API.
  """

  def __init__(self, client_classpath, messages_modulepath, default=False):
    self.client_classpath = client_classpath
    self.messages_modulepath = messages_modulepath
    self.default = default

  def __eq__(self, other):
    return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __repr__(self):
    repr_fmt = 'client_classpath: {0}, messages_modulepath: {1}, default: {2}'
    return repr_fmt.format(self.client_classpath, self.messages_modulepath,
                           self.default)


def _GetAPIsMap(client_infos):
  """Get mapping of api name and version to APIDef.

  Args:
      client_infos: list(str), List of client info strings. Each string contains
      the client-file-path:default-marker, e.g. path/to/a/client.py:True.

  Returns:
    {str:{str:APIDef}}, mapping of api name and version to APIDef.

  Raises:
    Exception: if multiple clients are provided for the same api, version pair.
    Exception: if multiple default clients are provided for an api.
    Exception: if no default clients are provided for an api.
  """
  apis_map = {}
  apis_with_default = set()

  for client_info in client_infos:
    client_info_parts = client_info.split(':')
    client_file_path = client_info_parts[0]
    default = client_info_parts[1] == 'True'

    client_classpath = _GetClientClasspath(client_file_path)
    messages_modulepath = _GetMessagesModulepath(client_file_path)
    api, version = _GetAPIAndVersion(client_file_path)

    api_versions_map = apis_map.get(api)
    if not api_versions_map:
      api_versions_map = {}

    if version in api_versions_map:
      msg = 'Multiple clients found for [{0}:{1}]!'.format(api, version)
      raise Exception(msg)

    api_versions_map[version] = APIDef(client_classpath, messages_modulepath,
                                       default)
    apis_map[api] = api_versions_map

    if default:
      if api in apis_with_default:
        msg = 'Multiple default clients found for [{0}]!'.format(api)
        raise Exception(msg)
      else:
        apis_with_default.add(api)

  apis_without_default = set(apis_map.keys()).difference(apis_with_default)
  if apis_without_default:
    msg = 'No default clients found for [{0}]!'.format(
        ', '.join(sorted(apis_without_default)))
    raise Exception(msg)

  return apis_map


def _GetClientClasspath(client_file_path):
  """Returns the client_classpath for the given client_file_path.

  Args:
      client_file_path: str, Path to a client module, e.g. path/to/a/client.py.

  Returns:
    str, classpath for the given client_file_path, e.g. path.to.a.client.Client
  """
  client_module = os.path.basename(client_file_path).replace('.py', '')
  client_class_words = client_module.replace('_client', '').split('_')
  client_class_words = [word.capitalize() for word in client_class_words]
  client_class = ''.join(client_class_words)
  version_path = os.path.dirname(client_file_path)
  client_classpath = os.path.join(version_path, client_module, client_class)
  client_classpath = client_classpath.replace(os.sep, '.')
  return client_classpath


def _GetMessagesModulepath(client_file_path):
  """Returns the messages_modulepath for the given client_file_path.

  Args:
      client_file_path: str, Path to a client module, e.g. path/to/a/client.py.

  Returns:
    str, messages modulepath, e.g. path.to.a.messages
  """
  messages_modulepath = client_file_path.replace('_client.py', '_messages')
  messages_modulepath = messages_modulepath.replace(os.sep, '.')
  return messages_modulepath


def _GetAPIAndVersion(client_file_path):
  """Returns the api and version for the given client_file_path.

  Args:
      client_file_path: str, Path to a client module, e.g. path/to/a/client.py.

  Returns:
    (str, str), the api and version for the given client_file_path
  """
  version_path = os.path.dirname(client_file_path)
  version = os.path.basename(version_path)
  api_path = os.path.dirname(version_path)
  api = os.path.basename(api_path)
  return (api, version)
