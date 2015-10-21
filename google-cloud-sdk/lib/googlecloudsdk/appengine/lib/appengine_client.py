# Copyright 2015 Google Inc. All Rights Reserved.

"""Module used by gcloud to communicate with appengine services."""

from __future__ import with_statement

import urllib
import urllib2

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.credentials import devshell as c_devshell
from googlecloudsdk.core.credentials import service_account as c_service_account
from googlecloudsdk.core.credentials import store as c_store
from oauth2client import gce as oauth2client_gce
import yaml

from googlecloudsdk.appengine.lib.external.api import appinfo
from googlecloudsdk.appengine.lib.external.datastore import datastore_index
from googlecloudsdk.appengine.lib.external.tools import appengine_rpc_httplib2

from googlecloudsdk.appengine.lib import appengine_deployments
from googlecloudsdk.appengine.lib import logs_requestor
from googlecloudsdk.appengine.lib import module_downloader
from googlecloudsdk.appengine.lib import util
from googlecloudsdk.appengine.lib import yaml_parsing


APPCFG_SCOPES = ('https://www.googleapis.com/auth/appengine.admin',)

# Parameters for reading from the GCE metadata service.
METADATA_BASE = 'http://metadata.google.internal'
SERVICE_ACCOUNT_BASE = (
    'computeMetadata/v1beta1/instance/service-accounts/default')

RpcServerClass = appengine_rpc_httplib2.HttpRpcServerOAuth2  # pylint: disable=invalid-name


class Error(exceptions.Error):
  """Base exception for the module."""
  pass


class UnknownConfigType(Error):
  """An exception for when trying to update a config type we don't know."""
  pass


class AppengineClient(object):
  """Client used by gcloud to communicate with appengine services.

  Attributes:
    server: The appengine server to which requests are sent.
    project: The appengine application in use.
    oauth2_access_token: An existing OAuth2 access token to use.
    oauth2_refresh_token: An existing OAuth2 refresh token to use.
    authenticate_service_account: Authenticate using the default service account
      for the Google Compute Engine VM in which gcloud is being called.
    ignore_bad_certs: Whether to ignore certificate errors when talking to the
      server.
  """

  def __init__(self, server=None, ignore_bad_certs=False):
    self.server = server or 'appengine.google.com'
    self.project = properties.VALUES.core.project.Get(required=True)
    self.ignore_bad_certs = ignore_bad_certs
    # Auth related options
    self.oauth2_access_token = None
    self.oauth2_refresh_token = None
    self.oauth_scopes = APPCFG_SCOPES
    self.authenticate_service_account = False

    account = properties.VALUES.core.account.Get()
    # This statement will raise a c_store.Error if there is a problem
    # fetching credentials.
    credentials = c_store.Load(account=account)
    if (isinstance(credentials, c_devshell.DevshellCredentials) or
        isinstance(credentials, c_service_account.ServiceAccountCredentials)):
      # TODO(user): This passes the access token to use for API calls to
      # appcfg which means that commands that are longer than the lifetime
      # of the access token may fail - e.g. some long deployments.  The proper
      # solution is to integrate appcfg closer with the Cloud SDK libraries,
      # this code will go away then and the standard credentials flow will be
      # used.
      self.oauth2_access_token = credentials.access_token
    elif isinstance(credentials, oauth2client_gce.AppAssertionCredentials):
      # If we are on GCE, use the service account
      self.authenticate_service_account = True
    else:
      # Otherwise use a stored refresh token
      self.oauth2_refresh_token = credentials.refresh_token

  def CancelDeployment(self, module, version, force=False):
    """Cancels the deployment of the given module version.

    Args:
      module: str, The module deployment to cancel.
      version: str, The version deployment to cancel.
      force: bool, True to force the cancellation.
    """
    rpcserver = self._GetRpcServer()
    rpcserver.Send('/api/appversion/rollback',
                   app_id=self.project, module=module, version=version,
                   force_rollback='1' if force else '0')

  def CleanupIndexes(self, index_yaml):
    """Removes unused datastore indexes.

    Args:
      index_yaml: The parsed yaml file with index data.
    """
    rpcserver = self._GetRpcServer()
    response = rpcserver.Send('/api/datastore/index/diff',
                              app_id=self.project, payload=index_yaml.ToYAML())
    unused_new_indexes, notused_indexes = (
        datastore_index.ParseMultipleIndexDefinitions(response))

    # Get confirmation from user which indexes should be deleted.
    deletions = datastore_index.IndexDefinitions(indexes=[])
    if notused_indexes.indexes:
      for index in notused_indexes.indexes:
        msg = ('This index is no longer defined in your index.yaml file.\n{0}'
               .format(str(index.ToYAML())))
        prompt = 'Do you want to delete this index'
        if console_io.PromptContinue(msg, prompt, default=True):
          deletions.indexes.append(index)

    # Do deletions of confirmed indexes.
    if deletions.indexes:
      response = rpcserver.Send('/api/datastore/index/delete',
                                app_id=self.project, payload=deletions.ToYAML())
      not_deleted = datastore_index.ParseIndexDefinitions(response)

      # Notify the user when indexes are not deleted.
      if not_deleted.indexes:
        not_deleted_count = len(not_deleted.indexes)
        if not_deleted_count == 1:
          warning_message = ('An index was not deleted.  Most likely this is '
                             'because it no longer exists.\n\n')
        else:
          warning_message = ('%d indexes were not deleted.  Most likely this '
                             'is because they no longer exist.\n\n'
                             % not_deleted_count)
        for index in not_deleted.indexes:
          warning_message += index.ToYAML()
        log.warning(warning_message)

  def DownloadModule(self, module, version, output_dir):
    """Downloads the given version of the module.

    Args:
      module: str, The module to download.
      version: str, The version of the module to download.
      output_dir: str, The directory to download the module to.
    """
    rpcserver = self._GetRpcServer()
    downloader = module_downloader.ModuleDownloader(
        rpcserver, self.project, module, version)
    (full_version, file_lines) = downloader.GetFileList()
    with console_io.ProgressBar(
        label='Downloading [{0}] files...'.format(len(file_lines)),
        stream=log.status) as pb:
      downloader.Download(full_version, file_lines, output_dir, pb.SetProgress)

  def GetLogs(self, module, version, severity, vhost, include_vhost,
              include_all, num_days, end_date, output_file):
    """Get application logs for the given version of the module.

    Args:
      module: str, The module of the app to fetch logs from.
      version: str, The version of the app to fetch logs for.
      severity: int, App log severity to request (0-4); None for request logs
        only.
      vhost: str, The virtual host of log messages to get. None for all hosts.
      include_vhost: bool, If true, the virtual host is included in log
        messages.
      include_all: bool, If true, we add to the log message everything we know
        about the request.
      num_days: int, Number of days worth of logs to export; 0 for all
        available.
      end_date: datetime.date, Date object representing last day of logs to
        return.  If None, today is used.
      output_file: Output file name or '-' for standard out.
    """
    rpcserver = self._GetRpcServer()
    requestor = logs_requestor.LogsRequester(
        rpcserver, self.project, module, version, severity, vhost,
        include_vhost, include_all)
    requestor.DownloadLogs(num_days, end_date, output_file)

  def GetLogsAppend(self, module, version, severity, vhost, include_vhost,
                    include_all, end_date, output_file):
    """Get application logs and append them to an existing file.

    Args:
      module: str, The module of the app to fetch logs from.
      version: str, The version of the app to fetch logs for.
      severity: int, App log severity to request (0-4); None for request logs
        only.
      vhost: str, The virtual host of log messages to get. None for all hosts.
      include_vhost: bool, If true, the virtual host is included in log
        messages.
      include_all: bool, If true, we add to the log message everything we know
        about the request.
      end_date: datetime.date, Date object representing last day of logs to
        return.  If None, today is used.
      output_file: Output file name or '-' for standard out.
    """
    rpcserver = self._GetRpcServer()
    requestor = logs_requestor.LogsRequester(
        rpcserver, self.project, module, version, severity, vhost,
        include_vhost, include_all)
    requestor.DownloadLogsAppend(end_date, output_file)

  def ListModules(self):
    """Lists all versions for an app.

    Returns:
      {str: [str]}, A mapping of module name to a list of version for that
      module.
    """
    rpcserver = self._GetRpcServer()
    response = rpcserver.Send('/api/versions/list', app_id=self.project)
    return yaml.safe_load(response)

  def DeployModule(self, module, version, module_yaml, module_yaml_path):
    """Updates and deploys new app versions based on given config.

    Args:
      module: str, The module to deploy.
      version: str, The version of the module to deploy.
      module_yaml: AppInfoExternal, Module info parsed from a module yaml file.
      module_yaml_path: str, Path of the module yaml file.

    Returns:
      An appinfo.AppInfoSummary if one was returned from the Deploy, None
      otherwise.
    """
    precompilation = True

    # Hack for Admin Console
    # Admin Console will continue to use 'module' instead of 'service'
    if module_yaml.service:
      module = module_yaml.service
      module_yaml.module = module
      module_yaml.service = None

    if module_yaml.runtime == 'vm':
      precompilation = False
    elif (module_yaml.runtime.startswith('java') and
          appinfo.JAVA_PRECOMPILED not in
          (module_yaml.derived_file_type or [])):
      precompilation = False

    if precompilation:
      if not module_yaml.derived_file_type:
        module_yaml.derived_file_type = []
      if appinfo.PYTHON_PRECOMPILED not in module_yaml.derived_file_type:
        module_yaml.derived_file_type.append(appinfo.PYTHON_PRECOMPILED)

    rpcserver = self._GetRpcServer()

    appversion = appengine_deployments.AppVersionUploader(
        rpcserver,
        self.project,
        module,
        version,
        module_yaml,
        module_yaml_path,
        self.ResourceLimitsInfo(version))
    return appversion.DoUpload()

  def PrepareVmRuntime(self):
    """Prepare the application for vm runtimes and return state."""
    rpcserver = self._GetRpcServer()
    rpcserver.Send('/api/vms/prepare', app_id=self.project)

  def ResourceLimitsInfo(self, version):
    """Returns the current resource limits."""
    rpcserver = self._GetRpcServer()
    request_params = {'app_id': self.project, 'version': version}
    logging_context = util.ClientDeployLoggingContext(rpcserver,
                                                      request_params,
                                                      usage_reporting=False)

    log.debug('Getting current resource limits.')
    yaml_data = logging_context.Send('/api/appversion/getresourcelimits')
    resource_limits = yaml.safe_load(yaml_data)
    log.debug('Using resource limits: {0}'.format(resource_limits))
    return resource_limits

  def SetDefaultVersion(self, modules, version):
    """Sets the default serving version of the given modules.

    Args:
      modules: [str], The module names
      version: str, The version to set at the default.

    Raises:
      ValueError: If modules, or version is not set correctly.
    """
    if not modules:
      raise ValueError('You must specify at least one module.')
    if not version:
      raise ValueError('You must specify a version to set as the default.')

    params = [('app_id', self.project), ('version', version)]
    params.extend(('module', module) for module in modules)
    url = '/api/appversion/setdefault?' + urllib.urlencode(sorted(params))
    self._GetRpcServer().Send(url)

  def SetManagedByGoogle(self, module, version, instance=None, wait=True):
    """Sets a module version (and optionally an instance) to Google managed.

    This will reboot the machine and restore the instance with a fresh runtime.

    Args:
      module: str, The module to update.
      version: str, The version of the module to update.
      instance: str, The instance id of a single instance to update.
      wait: bool, True to wait until it takes effect.

    Returns:
      None, if not waiting.  If waiting, returns (bool, message) for the last
      attempt at checking state.
    """
    return self._SetManagedBy(module, version, instance, '/api/vms/lock', wait)

  def SetManagedBySelf(self, module, version, instance=None, wait=True):
    """Sets a module version (and optionally a single instance) as self managed.

    This is the 'break the glass' mode that lets you ssh into the machine and
    debug.

    Args:
      module: str, The module to update.
      version: str, The version of the module to update.
      instance: str, The instance id of a single instance to update.
      wait: bool, True to wait until it takes effect.

    Returns:
      None, if not waiting.  If waiting, returns (bool, message) for the last
      attempt at checking state.
    """
    return self._SetManagedBy(module, version, instance, '/api/vms/debug', wait)

  def _SetManagedBy(self, module, version, instance, url, wait):
    """Switches a module version between management modes.

    Args:
      module: str, The module to update.
      version: str, The version of the module to update.
      instance: str, The instance id of a single instance to update.
      url: str, The URL of the API to call to make the update.
      wait: bool, True to wait until it takes effect.

    Returns:
      None, if not waiting.  If waiting, returns (bool, message) for the last
      attempt at checking state.
    """
    rpcserver = self._GetRpcServer()
    kwargs = {'app_id': self.project,
              'version_match': version,
              'module': module}
    if instance:
      kwargs['instance'] = instance

    rpcserver.Send(url, **kwargs)

    if wait:
      def GetState():
        yaml_data = rpcserver.Send(
            '/api/vms/debugstate', app_id=self.project, version_match=version,
            module=module)
        state = yaml.safe_load(yaml_data)
        done = state['state'] != 'PENDING'
        return (done, state['message'])

      def PrintRetryMessage(msg, delay):
        log.status.Print('{0}.  Will try again in {1} seconds.'
                         .format(msg, delay))

      return util.RetryWithBackoff(GetState, PrintRetryMessage, initial_delay=1,
                                   backoff_factor=2, max_delay=5, max_tries=20)

  def StartModule(self, module, version):
    """Starts serving a the given version of the module.

    This only works if scaling is set to manual.

    Args:
      module: str, The module to start.
      version: str, The version of the module to start.
    """
    self._GetRpcServer().Send('/api/modules/start', app_id=self.project,
                              module=module, version=version)

  def StopModule(self, module, version):
    """Stop serving a the given version of the module.

    This only works if scaling is set to manual.

    Args:
      module: str, The module to stop.
      version: str, The version of the module to stop.
    """
    self._GetRpcServer().Send('/api/modules/stop', app_id=self.project,
                              module=module, version=version)

  def UpdateConfig(self, config_name, parsed_yaml):
    """Updates any of the supported config file types.

    Args:
      config_name: str, The name of the config to deploy.
      parsed_yaml: The parsed object corresponding to that config type.

    Raises:
      UnknownConfigType: If config_name is not a value config type.

    Returns:
      Whatever the underlying update methods return.
    """
    if config_name == yaml_parsing.ConfigYamlInfo.CRON:
      return self.UpdateCron(parsed_yaml)
    if config_name == yaml_parsing.ConfigYamlInfo.DISPATCH:
      return self.UpdateDispatch(parsed_yaml)
    if config_name == yaml_parsing.ConfigYamlInfo.DOS:
      return self.UpdateDos(parsed_yaml)
    if config_name == yaml_parsing.ConfigYamlInfo.INDEX:
      return self.UpdateIndexes(parsed_yaml)
    if config_name == yaml_parsing.ConfigYamlInfo.QUEUE:
      return self.UpdateQueues(parsed_yaml)
    raise UnknownConfigType(
        'Config type [{0}] is not a known config type'.format(config_name))

  def UpdateCron(self, cron_yaml):
    """Updates any new or changed cron definitions.

    Args:
      cron_yaml: The parsed yaml file with cron data.
    """
    self._GetRpcServer().Send('/api/cron/update',
                              app_id=self.project, payload=cron_yaml.ToYAML())

  def UpdateDispatch(self, dispatch_yaml):
    """Updates new or changed dispatch definitions.

    Args:
      dispatch_yaml: The parsed yaml file with dispatch data.
    """
    self._GetRpcServer().Send('/api/dispatch/update',
                              app_id=self.project,
                              payload=dispatch_yaml.ToYAML())

  def UpdateDos(self, dos_yaml):
    """Updates any new or changed dos definitions.

    Args:
      dos_yaml: The parsed yaml file with dos data.
    """
    self._GetRpcServer().Send('/api/dos/update',
                              app_id=self.project, payload=dos_yaml.ToYAML())

  def UpdateIndexes(self, index_yaml):
    """Updates indexes.

    Args:
      index_yaml: The parsed yaml file with index data.
    """
    self._GetRpcServer().Send('/api/datastore/index/add',
                              app_id=self.project, payload=index_yaml.ToYAML())

  def UpdateQueues(self, queue_yaml):
    """Updates any new or changed task queue definitions.

    Args:
      queue_yaml: The parsed yaml file with queue data.
    """
    self._GetRpcServer().Send('/api/queue/update',
                              app_id=self.project, payload=queue_yaml.ToYAML())

  def _GetRpcServer(self):
    """Returns an instance of an AbstractRpcServer.

    Returns:
      A new AbstractRpcServer, on which RPC calls can be made.
    """
    log.debug('Host: {0}'.format(self.server))

    # In this case, the get_user_credentials parameters to the RPC server
    # constructor is actually an OAuth2Parameters.
    get_user_credentials = (
        appengine_rpc_httplib2.HttpRpcServerOAuth2.OAuth2Parameters(
            access_token=self.oauth2_access_token,
            client_id=config.CLOUDSDK_CLIENT_ID,
            client_secret=config.CLOUDSDK_CLIENT_NOTSOSECRET,
            scope=APPCFG_SCOPES,
            refresh_token=self.oauth2_refresh_token,
            credential_file=None,
            token_uri=self._GetTokenUri()))
    # Also set gflags flag... this is a bit of a hack.
    if hasattr(appengine_rpc_httplib2.tools, 'FLAGS'):
      appengine_rpc_httplib2.tools.FLAGS.auth_local_webserver = True

    server = RpcServerClass(
        self.server,
        get_user_credentials,
        util.GetUserAgent(),
        util.GetSourceName(),
        host_override=None,
        save_cookies=True,
        auth_tries=3,
        account_type='HOSTED_OR_GOOGLE',
        secure=True,
        ignore_certs=self.ignore_bad_certs)
    # TODO(user) Hack to avoid failure due to missing cacerts.txt resource.
    server.certpath = None
    # Don't use a cert file if the user passed ignore-bad-certs.
    server.cert_file_available = not self.ignore_bad_certs
    return util.RPCServer(server)

  def _GetTokenUri(self):
    """Returns the OAuth2 token_uri, or None to use the default URI.

    Returns:
      A string that is the token_uri, or None.

    Raises:
      Error: The user has requested authentication for a service account but the
      environment is not correct for that to work.
    """
    if self.authenticate_service_account:
      # Avoid hard-to-understand errors later by checking that we have a
      # metadata service (so we are in a GCE VM) and that the VM is configured
      # with access to the appengine.admin scope.
      url = '%s/%s/scopes' % (METADATA_BASE, SERVICE_ACCOUNT_BASE)
      try:
        req = urllib2.Request(url)
        vm_scopes_string = urllib2.urlopen(req).read()
      except urllib2.URLError, e:
        raise Error(
            'Could not obtain scope list from metadata service: %s: %s. This '
            'may be because we are not running in a Google Compute Engine VM.' %
            (url, e))
      vm_scopes = vm_scopes_string.split()
      missing = list(set(self.oauth_scopes).difference(vm_scopes))
      if missing:
        raise Error(
            'Required scopes %s missing from %s. '
            'This VM instance probably needs to be recreated '
            'with the missing scopes.' % (missing, vm_scopes))
      return '%s/%s/token' % (METADATA_BASE, SERVICE_ACCOUNT_BASE)
    else:
      return None
