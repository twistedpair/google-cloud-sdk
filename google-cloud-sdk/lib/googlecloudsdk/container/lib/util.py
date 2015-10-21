# Copyright 2014 Google Inc. All Rights Reserved.

"""Common utilities for the containers tool."""
import cStringIO
import json
import os

import distutils.version as dist_version
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.updater import update_manager
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import platforms

from googlecloudsdk.container.lib import kubeconfig as kconfig


class Error(core_exceptions.Error):
  """Class for errors raised by container commands."""


class APIHttpError(Error, exceptions.HttpException):
  """Class for Http errors returned from Google API."""

  def __init__(self, code, message):
    super(APIHttpError, self).__init__(message)
    self.code = code
    self.message = message

  def __str__(self):
    return 'ResponseError: code={0}, message={1}'.format(
        self.code, self.message)


def GetError(error):
  """Parse HttpError returned from Google API into printable APIHttpError.

  Args:
    error: apitools_base.HttpError.
  Returns:
    APIHttpError containing http error code and error message.
  """
  data = json.loads(error.content)
  code = int(data['error']['code'])
  message = data['error']['message']
  return APIHttpError(code, message)


def ConstructList(title, items):
  buf = cStringIO.StringIO()
  printer = console_io.ListPrinter(title)
  printer.Print(items, output_stream=buf)
  return buf.getvalue()


def IsVersionOlderThan(first, second):
  """Compare version strings and return true if first < second.

  e.g. 0.5.0 < 0.5.1, 0.4.4 < 0.41.5

  Args:
    first: str, Kubernetes version to check.
    second: str, Kubernetes version to compare.

  Returns:
    bool: True, if first logically comes before second, else False.
  """

  return dist_version.LooseVersion(first) < dist_version.LooseVersion(second)


MISSING_KUBECTL_MSG = """\
Accessing a Container Engine cluster requires the kubernetes commandline
client [kubectl]. To install, run
  $ gcloud components update kubectl
"""


# Verify that the kubectl component is installed or print a warning.
def CheckKubectlInstalled():
  if config.Paths().sdk_root is not None:
    platform = platforms.Platform.Current()
    manager = update_manager.UpdateManager(platform_filter=platform, warn=False)
    installed_components = manager.GetCurrentVersionsInformation()
    if 'kubectl' not in installed_components:
      log.warn(MISSING_KUBECTL_MSG)


KMASTER_NAME_FORMAT = 'k8s-{cluster_name}-master'
# These are determined by the version of kubernetes the cluster is running.
# This needs kept up to date when validating new cluster api versions.
KMASTER_LEGACY_CERT_DIRECTORY = '/usr/share/nginx'
KMASTER_CERT_DIRECTORY = '/srv/kubernetes'
KMASTER_USER = 'root'  # for /usr/share/...
KMASTER_CLIENT_KEY = 'kubecfg.key'
KMASTER_CLIENT_CERT = 'kubecfg.crt'
KMASTER_CERT_AUTHORITY = 'ca.crt'
KMASTER_CERT_FILES = [KMASTER_CLIENT_KEY, KMASTER_CLIENT_CERT,
                      KMASTER_CERT_AUTHORITY]


def GetKmasterCertDirectory(version):
  """Returns the directory on the Kubernetes master where SSL certs are stored.

  Args:
    version: str, Kubernetes version (e.g. "0.4.4" or "0.5.2").

  Returns:
    str, the path to SSL certs on the Kubernetes master.
  """
  if IsVersionOlderThan(version, '0.5'):
    return KMASTER_LEGACY_CERT_DIRECTORY
  return KMASTER_CERT_DIRECTORY


KUBECONFIG_USAGE_FMT = '''\
kubeconfig entry generated for {cluster}.'''


class ClusterConfig(object):
  """Encapsulates persistent cluster config data.

  Call ClusterConfig.Load() or ClusterConfig.Persist() to create this
  object.
  """

  _CONFIG_DIR_FORMAT = '{project}_{zone}_{cluster}'

  KUBECONTEXT_FORMAT = 'gke_{project}_{zone}_{cluster}'

  def __init__(self, **kwargs):
    self.cluster_name = kwargs['cluster_name']
    self.zone_id = kwargs['zone_id']
    self.project_id = kwargs['project_id']
    self.server = kwargs['server']
    # auth options are basic (user,password) OR bearer token.
    self.username = kwargs.get('username')
    self.password = kwargs.get('password')
    self.token = kwargs.get('token')
    self.ca_data = kwargs.get('ca_data')
    self.client_cert_data = kwargs.get('client_cert_data')
    self.client_key_data = kwargs.get('client_key_data')
    self._has_cert_files = bool(kwargs.get('has_cert_files'))

  def __str__(self):
    return 'ClusterConfig{project:%s, cluster:%s, zone:%s, endpoint:%s}' % (
        self.project_id, self.cluster_name, self.zone_id, self.endpoint)

  def _Fullpath(self, filename):
    return os.path.abspath(os.path.join(self.config_dir, filename))

  @property
  def config_dir(self):
    return ClusterConfig.GetConfigDir(
        self.cluster_name, self.zone_id, self.project_id)

  @property
  def ca_path(self):
    if self.has_cert_files:
      return self._Fullpath(KMASTER_CERT_AUTHORITY)
    return None

  @property
  def client_cert_path(self):
    if self.has_cert_files:
      return self._Fullpath(KMASTER_CLIENT_CERT)
    return None

  @property
  def client_key_path(self):
    if self.has_cert_files:
      return self._Fullpath(KMASTER_CLIENT_KEY)
    return None

  @property
  def kube_context(self):
    return ClusterConfig.KubeContext(
        self.cluster_name, self.zone_id, self.project_id)

  @property
  def has_cert_data(self):
    return self.ca_data and self.client_key_data and self.client_cert_data

  @property
  def has_cert_files(self):
    return self._has_cert_files

  @property
  def has_certs(self):
    return self.has_cert_files or self.has_cert_data

  @staticmethod
  def GetConfigDir(cluster_name, zone_id, project_id):
    return os.path.join(
        config.Paths().container_config_path,
        ClusterConfig._CONFIG_DIR_FORMAT.format(
            project=project_id, zone=zone_id, cluster=cluster_name))

  @staticmethod
  def KubeContext(cluster_name, zone_id, project_id):
    return ClusterConfig.KUBECONTEXT_FORMAT.format(
        project=project_id, cluster=cluster_name, zone=zone_id)

  def GenKubeconfig(self):
    """Generate kubeconfig for this cluster."""
    context = self.kube_context
    kubeconfig = kconfig.Kubeconfig.Default()
    cluster_kwargs = {}
    user_kwargs = {
        'token': self.token,
        'username': self.username,
        'password': self.password,
    }
    if self.has_cert_files:
      cluster_kwargs['ca_path'] = self.ca_path
      user_kwargs['cert_path'] = self.client_cert_path
      user_kwargs['key_path'] = self.client_key_path
    elif self.has_cert_data:
      cluster_kwargs['ca_data'] = self.ca_data
      user_kwargs['cert_data'] = self.client_cert_data
      user_kwargs['key_data'] = self.client_key_data

    # Use same key for context, cluster, and user
    kubeconfig.contexts[context] = kconfig.Context(context, context, context)
    kubeconfig.users[context] = kconfig.User(context, **user_kwargs)
    kubeconfig.clusters[context] = kconfig.Cluster(
        context, self.server, **cluster_kwargs)
    kubeconfig.SetCurrentContext(context)
    kubeconfig.SaveToFile()

    path = kconfig.Kubeconfig.DefaultPath()
    log.debug('Saved kubeconfig to %s', path)
    log.status.Print(KUBECONFIG_USAGE_FMT.format(
        cluster=self.cluster_name, context=context))

  @classmethod
  def _ClusterVersion(cls, cluster):
    # TODO(user): use api_adapter instead of getattr
    version = getattr(cluster, 'initialClusterVersion', None)
    if not version:
      version = getattr(cluster, 'clusterApiVersion')
    return version

  @classmethod
  def Persist(cls, cluster, project_id, cli):
    """Save config data for the given cluster.

    Persists config file and kubernetes auth file for the given cluster
    to cloud-sdk config directory and returns ClusterConfig object
    encapsulating the same data.

    Args:
      cluster: valid Cluster message to persist config data for.
      project_id: project that owns this cluster.
      cli: calliope.cli.CLI, The top-level CLI object.
    Returns:
      ClusterConfig of the persisted data.
    """
    kwargs = {
        'cluster_name': cluster.name,
        'zone_id': cluster.zone,
        'project_id': project_id,
        'server': 'https://' + cluster.endpoint,
    }
    auth = cluster.masterAuth
    version = cls._ClusterVersion(cluster)
    if auth.clientCertificate and auth.clientKey and auth.clusterCaCertificate:
      kwargs['ca_data'] = auth.clusterCaCertificate
      kwargs['client_key_data'] = auth.clientKey
      kwargs['client_cert_data'] = auth.clientCertificate
    elif IsVersionOlderThan(version, '0.18'):
      # Manually copy cert files for legacy clusters.
      config_dir = cls.GetConfigDir(cluster.name, cluster.zone, project_id)
      file_utils.MakeDir(config_dir)
      certs = cls._FetchCertFiles(cluster, project_id, cli)
      kwargs['has_cert_files'] = bool(certs)
    else:
      # This should not happen unless the cluster is in an unusual error
      # state.
      log.error('Cluster is missing certificate data.')

    # TODO(user): these are not needed if cluster has certs, though they
    # are useful for testing, e.g. with curl. Consider removing if/when the
    # apiserver no longer supports insecure (no certs) requests.
    # TODO(user): use api_adapter instead of getattr, or remove bearerToken
    # support
    if getattr(auth, 'bearerToken', None):
      kwargs['token'] = auth.bearerToken
    else:
      username = getattr(auth, 'user', None) or getattr(auth, 'username', None)
      kwargs['username'] = username
      kwargs['password'] = auth.password

    c_config = cls(**kwargs)
    c_config.GenKubeconfig()
    return c_config

  @classmethod
  def Load(cls, cluster_name, zone_id, project_id):
    """Load and verify config for given cluster.

    Args:
      cluster_name: name of cluster to load config for.
      zone_id: compute zone the cluster is running in.
      project_id: project in which the cluster is running.
    Returns:
      ClusterConfig for the cluster, or None if config data is missing or
      incomplete.
    """
    log.debug('Loading cluster config for cluster=%s, zone=%s project=%s',
              cluster_name, zone_id, project_id)
    k = kconfig.Kubeconfig.Default()

    key = cls.KubeContext(cluster_name, zone_id, project_id)

    cluster = k.clusters.get(key) and k.clusters[key].get('cluster')
    user = k.users.get(key) and k.users[key].get('user')
    context = k.contexts.get(key) and k.contexts[key].get('context')
    if not cluster or not user or not context:
      log.debug('missing kubeconfig entries for %s', key)
      return None
    if context.get('user') != key or context.get('cluster') != key:
      log.debug('invalid context %s', context)
      return None

    # Verify cluster data
    server = cluster.get('server')
    insecure = cluster.get('insecure-skip-tls-verify')
    ca_path = cluster.get('certificate-authority')
    ca_data = cluster.get('certificate-authority-data')
    if not server:
      log.debug('missing cluster.server entry for %s', key)
      return None
    if insecure:
      if ca_path or ca_data:
        log.debug('cluster cannot specify both certificate-authority(-data) '
                  'and insecure-skip-tls-verify')
        return None
    elif ca_path and ca_data:
      log.debug('cluster cannot specify both certificate-authority '
                'and certificate-authority-data')
      return None
    elif not ca_path and not ca_data:
      log.debug('cluster must specify one of certificate-authority|'
                'certificate-authority-data|insecure-skip-tls-verify')
      return None

    # Verify user data
    username = user.get('username')
    password = user.get('password')
    token = user.get('token')
    cert_path = user.get('client-certificate')
    cert_data = user.get('client-certificate-data')
    key_path = user.get('client-key')
    key_data = user.get('client-key-data')
    if key_path and key_data:
      return None
    elif cert_path and cert_data:
      return None
    elif (not username or not password) and not token:
      log.debug('missing auth info for user %s: %s', key, user)
      return None
    # Verify cert files exist if specified
    for fname in ca_path, cert_path, key_path:
      if fname and not os.path.isfile(fname):
        log.debug('could not find %s', fname)
        return None

    # Construct ClusterConfig
    kwargs = {
        'cluster_name': cluster_name,
        'zone_id': zone_id,
        'project_id': project_id,
        'server': server,
        'username': username,
        'password': password,
        'token': token,
        'ca_data': ca_data,
        'client_key_data': key_data,
        'client_cert_data': cert_data,
        'has_cert_files': (key_path and cert_path and ca_path),
    }
    return cls(**kwargs)

  @classmethod
  def Purge(cls, cluster_name, zone_id, project_id):
    config_dir = cls.GetConfigDir(cluster_name, zone_id, project_id)
    if os.path.exists(config_dir):
      file_utils.RmTree(config_dir)
    # purge from kubeconfig
    kubeconfig = kconfig.Kubeconfig.Default()
    kubeconfig.Clear(cls.KubeContext(cluster_name, zone_id, project_id))
    kubeconfig.SaveToFile()
    log.debug('Purged cluster config from %s', config_dir)

  @classmethod
  def _FetchCertFiles(cls, cluster, project_id, cli):
    """Call into gcloud.compute.copy_files to copy certs from cluster.

    Copies cert files from Kubernetes master into local config directory
    for the provided cluster.

    Args:
      cluster: a valid Cluster message.
      project_id: str, project that owns this cluster.
      cli: calliope.cli.CLI, The top-level CLI object.
    Returns:
      bool, True if fetch succeeded, else False.
    """
    instance_name = KMASTER_NAME_FORMAT.format(cluster_name=cluster.name)

    version = cls._ClusterVersion(cluster)
    cert_dir = GetKmasterCertDirectory(version)
    paths = [os.path.join(cert_dir, cert_file) for
             cert_file in KMASTER_CERT_FILES]
    # Put all the paths together in the same CLI argument so that SCP copies all
    # the files in one go rather than separately, to keep the user from being
    # asked for their GCE SSH passphrase multiple times.
    remote_file_paths = '{user}@{instance_name}:{filepaths}'.format(
        user=KMASTER_USER, instance_name=instance_name,
        filepaths=' '.join(paths))

    config_dir = cls.GetConfigDir(cluster.name, cluster.zone, project_id)
    file_utils.MakeDir(config_dir)
    log.out.Print('Using gcloud compute copy-files to fetch ssl certs from '
                  'cluster master...')
    try:
      cli.Execute(['compute', 'copy-files', '--zone=' + cluster.zone,
                   remote_file_paths, config_dir])
      return True
    except exceptions.ToolException as error:
      log.error(
          'Fetching ssl certs from cluster master failed:\n\n%s\n\n'
          'You can still interact with the cluster, but you may see a warning '
          'that certificate checking is disabled.',
          error)
      return False
