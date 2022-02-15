# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Utilities for generating kubeconfig entries."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64
import os
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import encoding
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import platforms

COMMAND_DESCRIPTION = """
Fetch credentials for a running {kind} cluster.
This command updates a kubeconfig file with appropriate credentials and
endpoint information to point kubectl at a specific {kind} cluster.
By default, credentials are written to ``HOME/.kube/config''.
You can provide an alternate path by setting the ``KUBECONFIG'' environment
variable. If ``KUBECONFIG'' contains multiple paths, the first one is used.
This command enables switching to a specific cluster, when working
with multiple clusters. It can also be used to access a previously created
cluster from a new workstation.
The command will configure kubectl to automatically refresh its
credentials using the same identity as the gcloud command-line tool.
See [](https://cloud.google.com/kubernetes-engine/docs/kubectl) for
kubectl documentation.
"""

COMMAND_EXAMPLE = """
To get credentials of a cluster named ``my-cluster'' managed in location ``us-west1'',
run:
$ {command} my-cluster --location=us-west1
"""


class Error(core_exceptions.Error):
  """Class for errors raised by edgecontainer kubeconfig utilities."""


class MissingEnvVarError(Error):
  """An exception raised when required environment variables are missing."""


def GenerateContext(project_id, location, cluster_id):
  """Generates a kubeconfig context for a Edge Container cluster.

  Args:
    project_id: str, project ID associated with the cluster.
    location: str, Google location of the cluster.
    cluster_id: str, ID of the cluster.

  Returns:
    The context for the kubeconfig entry.
  """
  template = 'edgecontainer_{project_id}_{location}_{cluster_id}'
  return template.format(
      project_id=project_id, location=location, cluster_id=cluster_id)


def GenerateAuthProviderCmdArgs(track, cluster_id, project_id, location):
  """Generates command arguments for kubeconfig's authorization provider.

  Args:
    track: ReleaseTrack of gcloud command.
    cluster_id: str, ID of the cluster.
    project_id: str, ID of the project of the cluster.
    location: str, Google location of the cluster.

  Returns:
    The command arguments for kubeconfig's authorization provider.
  """
  template = ('{prefix}edge-cloud container clusters print-access-token '
              '{cluster_id} --project={project_id} --location={location}')
  return template.format(
      prefix='' if track.prefix is None else track.prefix + ' ',
      cluster_id=cluster_id,
      project_id=project_id,
      location=location)


def GenerateKubeconfig(cluster, context, cmd_path, cmd_args):
  """Generates a kubeconfig entry for a Edge Container cluster.

  Args:
    cluster: object, Edge Container cluster.
    context: str, context for the kubeconfig entry.
    cmd_path: str, authentication provider command path.
    cmd_args: str, authentication provider command arguments.

  Raises:
      Error: don't have the permission to open kubeconfig file
  """
  kubeconfig = Kubeconfig.Default()
  # Use the same key for context, cluster, and user.
  kubeconfig.contexts[context] = Context(context, context, context)
  user_kwargs = {
      'auth_provider': 'gcp',
      'auth_provider_cmd_path': cmd_path,
      'auth_provider_cmd_args': cmd_args,
      'auth_provider_expiry_key': '{.expireTime}',
      'auth_provider_token_key': '{.accessToken}'
  }
  user = User(context, **user_kwargs)
  kubeconfig.users[context] = user
  cluster_kwargs = {}
  if cluster.clusterCaCertificate is None:
    log.warning('Cluster is missing certificate authority data.')
  else:
    cluster_kwargs['ca_data'] = _GetCaData(cluster.clusterCaCertificate)
  kubeconfig.clusters[context] = Cluster(
      context, 'https://{}:6443'.format(cluster.endpoint), **cluster_kwargs)
  kubeconfig.SetCurrentContext(context)
  kubeconfig.SaveToFile()
  log.status.Print(
      'A new kubeconfig entry "{}" has been generated and set as the '
      'current context.'.format(context))


def _GetCaData(pem):
  # Field certificate-authority-data in kubeconfig
  # expects a base64 encoded string of a PEM.
  return base64.b64encode(pem.encode('utf-8')).decode('utf-8')


# kubeconfig code lifted from googlecloudsdk/api_lib/container/kubeconfig.py
# with a few tweaks.
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

  @property
  def filename(self):
    return self._filename

  def Clear(self, key):
    self.contexts.pop(key, None)
    self.clusters.pop(key, None)
    self.users.pop(key, None)
    if self._data.get('current-context') == key:
      self._data['current-context'] = ''

  def SaveToFile(self):
    """Save kubeconfig to file.

    Raises:
      Error: don't have the permission to open kubeconfig file.
    """
    self._data['clusters'] = list(self.clusters.values())
    self._data['users'] = list(self.users.values())
    self._data['contexts'] = list(self.contexts.values())
    with file_utils.FileWriter(self._filename, private=True) as fp:
      yaml.dump(self._data, fp)

  def SetCurrentContext(self, context):
    self._data['current-context'] = context

  @classmethod
  def _Validate(cls, data):
    """Make sure we have the main fields of a kubeconfig."""
    if not data:
      raise Error('empty file')
    try:
      for key in ('clusters', 'users', 'contexts'):
        if not isinstance(data[key], list):
          raise Error('invalid type for {0}: {1}'.format(
              data[key], type(data[key])))
    except KeyError as error:
      raise Error('expected key {0} not found'.format(error))

  @classmethod
  def LoadFromFile(cls, filename):
    try:
      data = yaml.load_path(filename)
    except yaml.Error as error:
      raise Error('unable to load kubeconfig for {0}: {1}'.format(
          filename, error.inner_error))
    cls._Validate(data)
    return cls(data, filename)

  @classmethod
  def LoadOrCreate(cls, filename):
    """Read in the kubeconfig, and if it doesn't exist create one there."""
    try:
      return cls.LoadFromFile(filename)
    except (Error, IOError) as error:
      log.debug('unable to load default kubeconfig: {0}; recreating {1}'.format(
          error, filename))
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

    kubeconfig = encoding.GetEncodedValue(os.environ, 'KUBECONFIG')
    if kubeconfig:
      kubeconfig = kubeconfig.split(os.pathsep)[0]
      return os.path.abspath(kubeconfig)

    # This follows the same resolution process as kubectl for the config file.
    home_dir = encoding.GetEncodedValue(os.environ, 'HOME')
    if not home_dir and platforms.OperatingSystem.IsWindows():
      home_drive = encoding.GetEncodedValue(os.environ, 'HOMEDRIVE')
      home_path = encoding.GetEncodedValue(os.environ, 'HOMEPATH')
      if home_drive and home_path:
        home_dir = os.path.join(home_drive, home_path)
      if not home_dir:
        home_dir = encoding.GetEncodedValue(os.environ, 'USERPROFILE')

    if not home_dir:
      raise MissingEnvVarError(
          'environment variable {vars} or KUBECONFIG must be set to store '
          'credentials for kubectl'.format(
              vars='HOMEDRIVE/HOMEPATH, USERPROFILE, HOME,' if platforms
              .OperatingSystem.IsWindows() else 'HOME'))
    return os.path.join(home_dir, '.kube', 'config')

  def Merge(self, kubeconfig):
    """Merge another kubeconfig into self.

    In case of overlapping keys, the value in self is kept and the value in
    the other kubeconfig is lost.

    Args:
      kubeconfig: a Kubeconfig instance
    """
    self.SetCurrentContext(self.current_context or kubeconfig.current_context)
    self.clusters = dict(
        list(kubeconfig.clusters.items()) + list(self.clusters.items()))
    self.users = dict(list(kubeconfig.users.items()) + list(self.users.items()))
    self.contexts = dict(
        list(kubeconfig.contexts.items()) + list(self.contexts.items()))


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
  return {'name': name, 'cluster': cluster}


def User(name,
         auth_provider=None,
         auth_provider_cmd_path=None,
         auth_provider_cmd_args=None,
         auth_provider_expiry_key=None,
         auth_provider_token_key=None,
         cert_path=None,
         cert_data=None,
         key_path=None,
         key_data=None):
  """Generates and returns a user kubeconfig object.

  Args:
    name: str, nickname for this user entry.
    auth_provider: str, authentication provider.
    auth_provider_cmd_path: str, authentication provider command path.
    auth_provider_cmd_args: str, authentication provider command args.
    auth_provider_expiry_key: str, authentication provider expiry key.
    auth_provider_token_key: str, authentication provider token key.
    cert_path: str, path to client certificate file.
    cert_data: str, base64 encoded client certificate data.
    key_path: str, path to client key file.
    key_data: str, base64 encoded client key data.

  Returns:
    dict, valid kubeconfig user entry.

  Raises:
    Error: if no auth info is provided (auth_provider or cert AND key)
  """
  # TODO(b/70856999) Figure out what the correct behavior for client certs is.
  if not (auth_provider or (cert_path and key_path) or
          (cert_data and key_data)):
    raise Error('either auth_provider or cert & key must be provided')
  user = {}
  # Setup ExecAuth if USE_GKE_GCLOUD_AUTH_PLUGIN is True
  use_exec_auth = False
  use_gke_gcloud_auth_plugin = encoding.GetEncodedValue(
      os.environ, 'USE_GKE_GCLOUD_AUTH_PLUGIN')
  if use_gke_gcloud_auth_plugin == 'True':
    use_exec_auth = True

  if auth_provider:
    # Setup authprovider
    # if certain 'auth_provider_' fields are "present" OR
    # if use_exec_auth is set to False
    if auth_provider_cmd_path or auth_provider_cmd_args or auth_provider_expiry_key or auth_provider_token_key or not use_exec_auth:
      # auth-provider is being deprecated in favor of "exec" in k8s 1.25.
      user['auth-provider'] = _AuthProvider(
          name=auth_provider,
          cmd_path=auth_provider_cmd_path,
          cmd_args=auth_provider_cmd_args,
          expiry_key=auth_provider_expiry_key,
          token_key=auth_provider_token_key)
    else:
      user['exec'] = _ExecAuthPlugin()

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

  return {'name': name, 'user': user}


SDK_BIN_PATH_NOT_FOUND = """\
Path to sdk installation not found. Please check your installation or use the
`--auth-provider-cmd-path` flag to provide the path to gcloud manually."""


def _ExecAuthPlugin():
  """Generate and return an exec auth plugin config.

  Constructs an exec auth plugin config entry readable by kubectl.
  This tells kubectl to call out to gke-gcloud-auth-plugin and
  parse the output to retrieve access tokens to authenticate to
  the kubernetes master.

  Kubernetes GKE Auth Provider plugin is defined at
  https://kubernetes.io/docs/reference/access-authn-authz/authentication/#client-go-credential-plugins

  GKE GCloud Exec Auth Plugin code is at
  https://github.com/kubernetes/cloud-provider-gcp/tree/master/cmd/gke-gcloud-auth-plugin

  Returns:
    dict, valid exec auth plugin config entry.
  """
  bin_name = 'gke-gcloud-auth-plugin'
  if platforms.OperatingSystem.IsWindows():
    bin_name = 'gke-gcloud-auth-plugin.exe'
  command = bin_name

  sdk_bin_path = config.Paths().sdk_bin_path
  if sdk_bin_path is not None:
    command = os.path.join(sdk_bin_path, bin_name)
  exec_cfg = {
      'command': command,
      'apiVersion': 'client.authentication.k8s.io/v1beta1',
      'installHint': 'Install gke-gcloud-auth-plugin by running: '
                     'gcloud components install gke-gcloud-auth-plugin',
      'provideClusterInfo': True,
  }

  if properties.VALUES.container.use_app_default_credentials.GetBool():
    exec_cfg['args'] = ['--use_application_default_credentials']
  return exec_cfg


def _AuthProvider(name='gcp',
                  cmd_path=None,
                  cmd_args=None,
                  expiry_key=None,
                  token_key=None):
  """Generates and returns an auth provider config.

  Constructs an auth provider config entry readable by kubectl. This tells
  kubectl to call out to a specific gcloud command and parse the output to
  retrieve access tokens to authenticate to the kubernetes master.
  Kubernetes gcp auth provider plugin at
  https://github.com/kubernetes/kubernetes/tree/master/staging/src/k8s.io/client-go/plugin/pkg/client/auth/gcp

  Args:
    name: auth provider name
    cmd_path: str, authentication provider command path.
    cmd_args: str, authentication provider command arguments.
    expiry_key: str, authentication provider expiry key.
    token_key: str, authentication provider token key.

  Returns:
    dict, valid auth provider config entry.
  Raises:
    Error: Path to sdk installation not found. Please switch to application
    default credentials using one of

    $ gcloud config set container/use_application_default_credentials true
    $ export CLOUDSDK_CONTAINER_USE_APPLICATION_DEFAULT_CREDENTIALS=true.
  """
  provider = {'name': name}
  if name == 'gcp':
    bin_name = 'gcloud'
    if platforms.OperatingSystem.IsWindows():
      bin_name = 'gcloud.cmd'

    if cmd_path is None:
      sdk_bin_path = config.Paths().sdk_bin_path
      if sdk_bin_path is None:
        raise Error(SDK_BIN_PATH_NOT_FOUND)
      cmd_path = os.path.join(sdk_bin_path, bin_name)

    cfg = {
        # Command for gcloud credential helper
        'cmd-path':
            cmd_path,
        # Args for gcloud credential helper
        'cmd-args':
            cmd_args if cmd_args else 'config config-helper --format=json',
        # JSONpath to the field that is the raw access token
        'token-key':
            token_key if token_key else '{.credential.access_token}',
        # JSONpath to the field that is the expiration timestamp
        'expiry-key':
            expiry_key if expiry_key else '{.credential.token_expiry}'
        # Note: we're omitting 'time-fmt' field, which if provided, is a
        # format string of the golang reference time. It can be safely omitted
        # because config-helper's default time format is RFC3339, which is the
        # same default kubectl assumes.
    }
    provider['config'] = cfg
  return provider


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
