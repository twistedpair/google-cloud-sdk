# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Utilities for loading and parsing kubeconfig."""
import os

from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files as file_utils

import yaml


class Error(core_exceptions.Error):
  """Class for errors raised by kubeconfig utilities."""


class MissingEnvVarError(Error):
  """An exception raised when required environment variables are missing."""


# TODO(user): marshal yaml directly into a type with a
# matching structure.
class Kubeconfig(object):
  """Interface for interacting with a kubeconfig file."""

  def __init__(self, raw_data, filename):
    self._filename = filename
    self._data = raw_data
    self.clusters = {}
    self.users = {}
    self.contexts = {}
    for cluster in self._data['clusters']:
      self.clusters[cluster['name']] = cluster
    for user in self._data['users']:
      self.users[user['name']] = user
    for context in self._data['contexts']:
      self.contexts[context['name']] = context

  @property
  def current_context(self):
    return self._data['current-context']

  def Clear(self, key):
    self.contexts.pop(key, None)
    self.clusters.pop(key, None)
    self.users.pop(key, None)
    if self._data.get('current-context') == key:
      self._data['current-context'] = ''

  def SaveToFile(self):
    self._data['clusters'] = self.clusters.values()
    self._data['users'] = self.users.values()
    self._data['contexts'] = self.contexts.values()
    # We use os.open here to explicitly set file mode 0600.
    # the flags passed should mimic behavior of open(self._filename, 'w'),
    # which does write with truncate and creates file if not existing.
    flags = os.O_WRONLY | os.O_TRUNC | os.O_CREAT
    with os.fdopen(os.open(self._filename, flags, 0o600), 'w') as fp:
      yaml.safe_dump(self._data, fp, default_flow_style=False)

  def SetCurrentContext(self, context):
    self._data['current-context'] = context

  @classmethod
  def _Validate(cls, data):
    try:
      if not data:
        raise Error('empty file')
      for key in ('clusters', 'users', 'contexts'):
        if not isinstance(data[key], list):
          raise Error(
              'invalid type for %s: %s', data[key], type(data[key]))
    except KeyError as error:
      raise Error('expected key %s not found', error)

  @classmethod
  def LoadFromFile(cls, filename):
    try:
      with open(filename, 'r') as fp:
        data = yaml.load(fp)
        cls._Validate(data)
        return cls(data, filename)
    except yaml.YAMLError as error:
      raise Error('unable to load kubeconfig for %s: %s', filename, error)

  @classmethod
  def LoadOrCreate(cls, filename):
    try:
      return cls.LoadFromFile(filename)
    except (Error, IOError) as error:
      log.debug('unable to load default kubeconfig: %s; recreating %s',
                error, filename)
      file_utils.MakeDir(os.path.dirname(filename))
      kubeconfig = cls(EmptyKubeconfig(), filename)
      kubeconfig.SaveToFile()
      return kubeconfig

  @classmethod
  def Default(cls):
    return cls.LoadOrCreate(Kubeconfig.DefaultPath())

  @staticmethod
  def DefaultPath():
    """Return default path for kubeconfig file."""

    if os.environ.get('KUBECONFIG'):
      return os.environ['KUBECONFIG']
    # kubectl doesn't do windows-compatible homedir detection, it
    # expects HOME to be set.
    # TODO(user): remove this once
    # https://github.com/kubernetes/kubernetes/issues/23199
    if not os.environ.get('HOME'):
      raise MissingEnvVarError(
          'environment variable HOME or KUBECONFIG must be set to store '
          'credentials for kubectl')
    return os.path.join(os.environ.get('HOME'), '.kube/config')


def Cluster(name, server, ca_path=None, ca_data=None):
  """Generate and return a cluster kubeconfig object."""
  cluster = {
      'server': server,
  }
  if ca_path and ca_data:
    raise Error('cannot specify both ca_path and ca_data')
  if ca_path:
    cluster['certificate-authority'] = ca_path
  elif ca_data:
    cluster['certificate-authority-data'] = ca_data
  else:
    cluster['insecure-skip-tls-verify'] = True
  return {
      'name': name,
      'cluster': cluster
  }


def User(name, token=None, username=None, password=None, auth_provider=None,
         cert_path=None, cert_data=None, key_path=None, key_data=None):
  """Generate and return a user kubeconfig object.

  Args:
    name: str, nickname for this user entry.
    token: str, bearer token.
    username: str, basic auth user.
    password: str, basic auth password.
    auth_provider: str, authentication provider.
    cert_path: str, path to client certificate file.
    cert_data: str, base64 encoded client certificate data.
    key_path: str, path to client key file.
    key_data: str, base64 encoded client key data.
  Returns:
    dict, valid kubeconfig user entry.

  Raises:
    Error: if no auth info is provided (token or username AND password)
  """
  if not auth_provider and not token and (not username or not password):
    raise Error('either auth_provider, token or username & password must be'
                ' provided')
  user = {}
  if auth_provider:
    user['auth-provider'] = {'name': auth_provider}
  elif token:
    user['token'] = token
  else:
    user['username'] = username
    user['password'] = password

  if cert_path and cert_data:
    raise Error('cannot specify both cert_path and cert_data')
  if cert_path:
    user['client-certificate'] = cert_path
  elif cert_data:
    user['client-certificate-data'] = cert_data

  if key_path and key_data:
    raise Error('cannot specify both key_path and key_data')
  if key_path:
    user['client-key'] = key_path
  elif key_data:
    user['client-key-data'] = key_data

  return {
      'name': name,
      'user': user
  }


def Context(name, cluster, user):
  """Generate and return a context kubeconfig object."""
  return {
      'name': name,
      'context': {
          'cluster': cluster,
          'user': user,
      },
  }


def EmptyKubeconfig():
  return {
      'apiVersion': 'v1',
      'contexts': [],
      'clusters': [],
      'current-context': '',
      'kind': 'Config',
      'preferences': {},
      'users': [],
  }

