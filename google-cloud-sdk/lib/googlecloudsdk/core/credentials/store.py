# Copyright 2013 Google Inc. All Rights Reserved.
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

"""One-line documentation for auth module.

A detailed description of auth.
"""

import abc
import datetime
import json
import os
import textwrap
import enum

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import http
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.credentials import devshell as c_devshell
from googlecloudsdk.core.credentials import gce as c_gce
from googlecloudsdk.core.util import files
import httplib2
from oauth2client import client
from oauth2client import service_account
from oauth2client.contrib import gce as oauth2client_gce
from oauth2client.contrib import multistore_file
from oauth2client.contrib import reauth_errors


GOOGLE_OAUTH2_PROVIDER_AUTHORIZATION_URI = (
    'https://accounts.google.com/o/oauth2/auth')
GOOGLE_OAUTH2_PROVIDER_REVOKE_URI = (
    'https://accounts.google.com/o/oauth2/revoke')
GOOGLE_OAUTH2_PROVIDER_TOKEN_URI = (
    'https://accounts.google.com/o/oauth2/token')


class Error(exceptions.Error):
  """Exceptions for the credentials module."""


class AuthenticationException(Error):
  """Exceptions that tell the users to run auth login."""

  def __init__(self, message):
    super(AuthenticationException, self).__init__(textwrap.dedent("""\
        {message}
        Please run:

          $ gcloud auth login

        to obtain new credentials, or if you have already logged in with a
        different account:

          $ gcloud config set account ACCOUNT

        to select an already authenticated account to use.""".format(
            message=message)))


class NoCredentialsForAccountException(AuthenticationException):
  """Exception for when no credentials are found for an account."""

  def __init__(self, account):
    super(NoCredentialsForAccountException, self).__init__(
        'Your current active account [{account}] does not have any'
        ' valid credentials'.format(account=account))


class NoActiveAccountException(AuthenticationException):
  """Exception for when there are no valid active credentials."""

  def __init__(self):
    super(NoActiveAccountException, self).__init__(
        'You do not currently have an active account selected.')


class TokenRefreshError(AuthenticationException,
                        client.AccessTokenRefreshError):
  """An exception raised when the auth tokens fail to refresh."""

  def __init__(self, error):
    message = ('There was a problem refreshing your current auth tokens: {0}'
               .format(error))
    super(TokenRefreshError, self).__init__(message)


class ReauthenticationException(Error):
  """Exceptions that tells the user to retry his command or run auth login."""

  def __init__(self, message):
    super(ReauthenticationException, self).__init__(textwrap.dedent("""\
        {message}
        Please retry your command or run:

          $ gcloud auth login

        To obtain new credentials.""".format(message=message)))


class TokenRefreshReauthError(ReauthenticationException):
  """An exception raised when the auth tokens fail to refresh due to reauth."""

  def __init__(self, error):
    message = ('There was a problem reauthenticating while refreshing your '
               'current auth tokens: {0}').format(error)
    super(TokenRefreshReauthError, self).__init__(message)


class InvalidCredentialFileException(Error):
  """Exception for when an external credential file could not be loaded."""

  def __init__(self, f, e):
    super(InvalidCredentialFileException, self).__init__(
        'Failed to load credential file: [{f}].  {message}'
        .format(f=f, message=str(e)))


class CredentialFileSaveError(Error):
  """An error for when we fail to save a credential file."""
  pass


class UnknownCredentialsType(Error):
  """An error for when we fail to determine the type of the credentials."""
  pass


class FlowError(Error):
  """Exception for when something goes wrong with a web flow."""


class RevokeError(Error):
  """Exception for when there was a problem revoking."""


class CredentialStore(object):
  """Abstract definition of credential store."""
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def GetAccounts(self):
    """Get all accounts that have credentials stored for the CloudSDK.

    Returns:
      {str}, Set of accounts.
    """
    return NotImplemented

  @abc.abstractmethod
  def Load(self, account_id):
    return NotImplemented

  @abc.abstractmethod
  def Store(self, account_id, credentials):
    return NotImplemented

  @abc.abstractmethod
  def Remove(self, account_id):
    return NotImplemented


class Oauth2ClientCredentialStore(CredentialStore):
  """Implementation of credential sotore over oauth2client.multistore_file."""

  def __init__(self, store_file=None):
    self._store_file = store_file or config.Paths().credentials_path

  def GetAccounts(self):
    """Overrides."""
    all_keys = multistore_file.get_all_credential_keys(
        filename=self._store_file)

    return {self._StorageKey2AccountId(key) for key in all_keys}

  def Load(self, account_id):
    credential_store = self._GetStorageByAccountId(account_id)
    return credential_store.get()

  def Store(self, account_id, credentials):
    credential_store = self._GetStorageByAccountId(account_id)
    credential_store.put(credentials)
    credentials.set_store(credential_store)

  def Remove(self, account_id):
    credential_store = self._GetStorageByAccountId(account_id)
    credential_store.delete()

  def _GetStorageByAccountId(self, account_id):
    storage_key = self._AcctountId2StorageKey(account_id)
    return multistore_file.get_credential_storage_custom_key(
        filename=self._store_file, key_dict=storage_key)

  def _AcctountId2StorageKey(self, account_id):
    """Converts account id into storage key."""
    all_storage_keys = multistore_file.get_all_credential_keys(
        filename=self._store_file)
    matching_keys = [k for k in all_storage_keys if k['account'] == account_id]
    if not matching_keys:
      return {'type': 'google-cloud-sdk', 'account': account_id}

    # We do not expect any other type keys in the credential store. Just in case
    # somehow they occur:
    #  1. prefer key with no type
    #  2. use google-cloud-sdk type
    #  3. use any other
    # Also log all cases where type was present but was not google-cloud-sdk.
    right_key = matching_keys[0]
    for key in matching_keys:
      if 'type' in key:
        if key['type'] == 'google-cloud-sdk' and 'type' in right_key:
          right_key = key
        else:
          log.file_only_logger.warn(
              'Credential store has unknown type [{0}] key for account [{1}]'
              .format(key['type'], key['account']))
      else:
        right_key = key
    if 'type' in right_key:
      right_key['type'] = 'google-cloud-sdk'
    return right_key

  def _StorageKey2AccountId(self, storage_key):
    return storage_key['account']


def AvailableAccounts():
  """Get all accounts that have credentials stored for the CloudSDK.

  This function will also ping the GCE metadata server to see if GCE credentials
  are available.

  Returns:
    [str], List of the accounts.

  """
  store = Oauth2ClientCredentialStore(config.Paths().credentials_path)
  accounts = store.GetAccounts() | set(c_gce.Metadata().Accounts())

  devshell_creds = c_devshell.LoadDevshellCredentials()
  if devshell_creds:
    accounts.add(devshell_creds.devshell_response.user_email)

  return sorted(accounts)


def LoadIfValid(account=None, scopes=None):
  """Gets the credentials associated with the provided account if valid.

  Args:
    account: str, The account address for the credentials being fetched. If
        None, the account stored in the core.account property is used.
    scopes: tuple, Custom auth scopes to request. By default CLOUDSDK_SCOPES
        are requested.

  Returns:
    oauth2client.client.Credentials, The credentials if they were found and
    valid, or None otherwise.
  """
  try:
    return Load(account=account, scopes=scopes)
  except Error:
    return None


def Load(account=None, scopes=None, prevent_refresh=False):
  """Get the credentials associated with the provided account.

  Args:
    account: str, The account address for the credentials being fetched. If
        None, the account stored in the core.account property is used.
    scopes: tuple, Custom auth scopes to request. By default CLOUDSDK_SCOPES
        are requested.
    prevent_refresh: bool, If True, do not refresh the access token even if it
        is out of date. (For use with operations that do not require a current
        access token, such as credential revocation.)

  Returns:
    oauth2client.client.Credentials, The specified credentials.

  Raises:
    NoActiveAccountException: If account is not provided and there is no
        active account.
    NoCredentialsForAccountException: If there are no valid credentials
        available for the provided or active account.
    c_gce.CannotConnectToMetadataServerException: If the metadata server cannot
        be reached.
    TokenRefreshError: If the credentials fail to refresh.
    TokenRefreshReauthError: If the credentials fail to refresh due to reauth.
  """
  # If a credential file is set, just use that and ignore the active account
  # and whatever is in the credential store.
  cred_file_override = properties.VALUES.auth.credential_file_override.Get()
  if cred_file_override:
    log.info('Using alternate credentials from file: [%s]',
             cred_file_override)
    try:
      cred = client.GoogleCredentials.from_stream(cred_file_override)
    except client.Error as e:
      raise InvalidCredentialFileException(cred_file_override, e)

    if cred.create_scoped_required():
      if scopes is None:
        scopes = config.CLOUDSDK_SCOPES
      cred = cred.create_scoped(scopes)

    # Set token_uri after scopes since token_uri needs to be explicitly
    # preserved when scopes are applied.
    token_uri_override = properties.VALUES.auth.token_host.Get()
    if token_uri_override:
      cred_type = CredentialType.FromCredentials(cred)
      if cred_type in (CredentialType.SERVICE_ACCOUNT,
                       CredentialType.P12_SERVICE_ACCOUNT):
        cred.token_uri = token_uri_override
    return cred

  if not account:
    account = properties.VALUES.core.account.Get()

  if not account:
    raise NoActiveAccountException()

  devshell_creds = c_devshell.LoadDevshellCredentials()
  if devshell_creds and (
      devshell_creds.devshell_response.user_email == account):
    return devshell_creds

  if account in c_gce.Metadata().Accounts():
    return AcquireFromGCE(account)

  store = Oauth2ClientCredentialStore(config.Paths().credentials_path)
  cred = store.Load(account)
  if not cred:
    raise NoCredentialsForAccountException(account)

  # cred.token_expiry is in UTC time.
  if (not prevent_refresh and
      (not cred.token_expiry or
       cred.token_expiry < cred.token_expiry.utcnow())):
    Refresh(cred)

  return cred


def Refresh(creds, http_client=None):
  """Refresh credentials.

  Calls creds.refresh(), unless they're SignedJwtAssertionCredentials.

  Args:
    creds: oauth2client.client.Credentials, The credentials to refresh.
    http_client: httplib2.Http, The http transport to refresh with.

  Raises:
    TokenRefreshError: If the credentials fail to refresh.
    TokenRefreshReauthError: If the credentials fail to refresh due to reauth.
  """
  try:
    creds.refresh(http_client or http.Http())
  except (client.AccessTokenRefreshError, httplib2.ServerNotFoundError) as e:
    raise TokenRefreshError(e.message)
  except reauth_errors.ReauthError as e:
    raise TokenRefreshReauthError(e.message)


def Store(creds, account=None, scopes=None):
  """Store credentials according for an account address.

  Args:
    creds: oauth2client.client.Credentials, The credentials to be stored.
    account: str, The account address of the account they're being stored for.
        If None, the account stored in the core.account property is used.
    scopes: tuple, Custom auth scopes to request. By default CLOUDSDK_SCOPES
        are requested.

  Raises:
    NoActiveAccountException: If account is not provided and there is no
        active account.
  """

  cred_type = CredentialType.FromCredentials(creds)
  if cred_type in (CredentialType.DEVSHELL, CredentialType.GCE):
    # We never serialize devshell or GCE credentials.
    return

  if not account:
    account = properties.VALUES.core.account.Get()
  if not account:
    raise NoActiveAccountException()

  store = Oauth2ClientCredentialStore(config.Paths().credentials_path)
  store.Store(account, creds)
  _LegacyGenerator(account, creds, scopes).WriteTemplate()


def ActivateCredentials(account, creds):
  """Validates, stores and activates credentials with given account."""
  Refresh(creds)
  Store(creds, account)

  properties.PersistProperty(properties.VALUES.core.account, account)


def RevokeCredentials(creds):
  creds.revoke(http.Http())


def Revoke(account=None):
  """Revoke credentials and clean up related files.

  Args:
    account: str, The account address for the credentials to be revoked. If
        None, the currently active account is used.

  Returns:
    'True' if this call revoked the account; 'False' if the account was already
    revoked.

  Raises:
    NoActiveAccountException: If account is not provided and there is no
        active account.
    NoCredentialsForAccountException: If the provided account is not tied to any
        known credentials.
    RevokeError: If there was a more general problem revoking the account.
  """
  if not account:
    account = properties.VALUES.core.account.Get()
  if not account:
    raise NoActiveAccountException()

  if account in c_gce.Metadata().Accounts():
    raise RevokeError('Cannot revoke GCE-provided credentials.')

  creds = Load(account, prevent_refresh=True)
  if not creds:
    raise NoCredentialsForAccountException(account)

  if isinstance(creds, c_devshell.DevshellCredentials):
    raise RevokeError(
        'Cannot revoke the automatically provisioned Cloud Shell credential.'
        'This comes from your browser session and will not persist outside'
        'of your connected Cloud Shell session.')

  rv = True
  try:
    RevokeCredentials(creds)
  except client.TokenRevokeError as e:
    if e.args[0] == 'invalid_token':
      rv = False
    else:
      raise

  store = Oauth2ClientCredentialStore(config.Paths().credentials_path)
  store.Remove(account)

  _LegacyGenerator(account, creds).Clean()
  files.RmTree(config.Paths().LegacyCredentialsDir(account))
  return rv


def AcquireFromWebFlow(launch_browser=True,
                       auth_uri=None,
                       token_uri=None,
                       scopes=None,
                       client_id=None,
                       client_secret=None):
  """Get credentials via a web flow.

  Args:
    launch_browser: bool, Open a new web browser window for authorization.
    auth_uri: str, URI to open for authorization.
    token_uri: str, URI to use for refreshing.
    scopes: string or iterable of strings, scope(s) of the credentials being
      requested.
    client_id: str, id of the client requesting authorization
    client_secret: str, client secret of the client requesting authorization

  Returns:
    client.Credentials, Newly acquired credentials from the web flow.

  Raises:
    FlowError: If there is a problem with the web flow.
  """
  if auth_uri is None:
    auth_uri = properties.VALUES.auth.auth_host.Get(required=True)
  if token_uri is None:
    token_uri = properties.VALUES.auth.token_host.Get(required=True)
  if scopes is None:
    scopes = config.CLOUDSDK_SCOPES
  if client_id is None:
    client_id = properties.VALUES.auth.client_id.Get(required=True)
  if client_secret is None:
    client_secret = properties.VALUES.auth.client_secret.Get(required=True)

  webflow = client.OAuth2WebServerFlow(
      client_id=client_id,
      client_secret=client_secret,
      scope=scopes,
      user_agent=config.CLOUDSDK_USER_AGENT,
      auth_uri=auth_uri,
      token_uri=token_uri,
      prompt='select_account')
  return RunWebFlow(webflow, launch_browser=launch_browser)


def RunWebFlow(webflow, launch_browser=True):
  """Runs a preconfigured webflow to get an auth token.

  Args:
    webflow: client.OAuth2WebServerFlow, The configured flow to run.
    launch_browser: bool, Open a new web browser window for authorization.

  Returns:
    client.Credentials, Newly acquired credentials from the web flow.

  Raises:
    FlowError: If there is a problem with the web flow.
  """
  # pylint:disable=g-import-not-at-top, This is imported on demand for
  # performance reasons.
  from googlecloudsdk.core.credentials import flow

  try:
    cred = flow.Run(webflow, launch_browser=launch_browser, http=http.Http())
  except flow.Error as e:
    raise FlowError(e)
  return cred


def AcquireFromToken(refresh_token,
                     token_uri=GOOGLE_OAUTH2_PROVIDER_TOKEN_URI,
                     revoke_uri=GOOGLE_OAUTH2_PROVIDER_REVOKE_URI):
  """Get credentials from an already-valid refresh token.

  Args:
    refresh_token: An oauth2 refresh token.
    token_uri: str, URI to use for refreshing.
    revoke_uri: str, URI to use for revoking.

  Returns:
    client.Credentials, Credentials made from the refresh token.
  """
  cred = client.OAuth2Credentials(
      access_token=None,
      client_id=properties.VALUES.auth.client_id.Get(required=True),
      client_secret=properties.VALUES.auth.client_secret.Get(required=True),
      refresh_token=refresh_token,
      # always start expired
      token_expiry=datetime.datetime.utcnow(),
      token_uri=token_uri,
      user_agent=config.CLOUDSDK_USER_AGENT,
      revoke_uri=revoke_uri)
  return cred


def AcquireFromGCE(account=None):
  """Get credentials from a GCE metadata server.

  Args:
    account: str, The account name to use. If none, the default is used.

  Returns:
    client.Credentials, Credentials taken from the metadata server.

  Raises:
    c_gce.CannotConnectToMetadataServerException: If the metadata server cannot
      be reached.
    TokenRefreshError: If the credentials fail to refresh.
    TokenRefreshReauthError: If the credentials fail to refresh due to reauth.
    Error: If a non-default service account is used.
  """
  default_account = c_gce.Metadata().DefaultAccount()
  if account is None:
    account = default_account
  if account != default_account:
    raise Error('Unable to use non-default GCE service accounts.')
  # TODO(user): Update oauth2client to fetch alternate credentials. This
  # inability is not currently a problem, because the metadata server does not
  # yet provide multiple service accounts.

  creds = oauth2client_gce.AppAssertionCredentials()
  Refresh(creds)
  return creds


def SaveCredentialsAsADC(creds, file_path):
  """Saves the credentials to the given file.

  This file can be read back via
    cred = client.GoogleCredentials.from_stream(file_path)

  Args:
    creds: client.OAuth2Credentials, obtained from a web flow
        or service account.
    file_path: str, file path to store credentials to. The file will be created.

  Raises:
    CredentialFileSaveError: on file io errors.
  """
  creds_type = CredentialType.FromCredentials(creds)
  if creds_type == CredentialType.P12_SERVICE_ACCOUNT:
    raise CredentialFileSaveError(
        'Error saving Application Default Credentials: p12 keys are not'
        'supported in this format')

  if creds_type == CredentialType.USER_ACCOUNT:
    creds = client.GoogleCredentials(
        creds.access_token, creds.client_id, creds.client_secret,
        creds.refresh_token, creds.token_expiry, creds.token_uri,
        creds.user_agent, creds.revoke_uri)
  try:
    with files.OpenForWritingPrivate(file_path) as f:
      json.dump(creds.serialization_data, f, sort_keys=True,
                indent=2, separators=(',', ': '))
  except IOError as e:
    log.debug(e, exc_info=True)
    raise CredentialFileSaveError(
        'Error saving Application Default Credentials: ' + str(e))


class CredentialType(enum.Enum):
  UNKNOWN = 0
  USER_ACCOUNT = 1
  SERVICE_ACCOUNT = 2
  P12_SERVICE_ACCOUNT = 3
  DEVSHELL = 4
  GCE = 5

  @staticmethod
  def FromCredentials(creds):
    if isinstance(creds, c_devshell.DevshellCredentials):
      return CredentialType.DEVSHELL
    if isinstance(creds, oauth2client_gce.AppAssertionCredentials):
      return CredentialType.GCE
    if isinstance(creds, service_account.ServiceAccountCredentials):
      if getattr(creds, '_private_key_pkcs12', None) is not None:
        return CredentialType.P12_SERVICE_ACCOUNT
      return CredentialType.SERVICE_ACCOUNT
    if getattr(creds, 'refresh_token', None) is not None:
      return CredentialType.USER_ACCOUNT
    return CredentialType.UNKNOWN


class _LegacyGenerator(object):
  """A class to generate the credential file for legacy tools."""

  def __init__(self, account, credentials, scopes=None):
    self.credentials = credentials
    self.credentials_type = CredentialType.FromCredentials(credentials)
    if self.credentials_type == CredentialType.UNKNOWN:
      raise UnknownCredentialsType('Unknown credentials type.')
    if scopes is None:
      self.scopes = config.CLOUDSDK_SCOPES
    else:
      self.scopes = scopes

    paths = config.Paths()
    # Single store file while not generated here can be created for caching
    # credentials by legacy tools, register so it is cleaned up.
    self._single_store = paths.LegacyCredentialsSingleStorePath(account)
    self._gsutil_path = paths.LegacyCredentialsGSUtilPath(account)
    self._p12_key_path = paths.LegacyCredentialsP12KeyPath(account)
    self._adc_path = paths.LegacyCredentialsAdcPath(account)

  def Clean(self):
    """Remove the credential file."""

    paths = [
        self._single_store,
        self._gsutil_path,
        self._p12_key_path,
        self._adc_path,
    ]
    for p in paths:
      try:
        os.remove(p)
      except OSError:
        # file did not exist, so we're already done.
        pass

  def WriteTemplate(self):
    """Write the credential file."""

    # General credentials used by bq and gsutil.
    if self.credentials_type != CredentialType.P12_SERVICE_ACCOUNT:
      SaveCredentialsAsADC(self.credentials, self._adc_path)

      if self.credentials_type == CredentialType.USER_ACCOUNT:
        # we create a small .boto file for gsutil, to be put in BOTO_PATH
        self._WriteFileContents(self._gsutil_path, textwrap.dedent("""\
            [Credentials]
            gs_oauth2_refresh_token = {token}
            """).format(token=self.credentials.refresh_token))
      elif self.credentials_type == CredentialType.SERVICE_ACCOUNT:
        self._WriteFileContents(self._gsutil_path, textwrap.dedent("""\
            [Credentials]
            gs_service_key_file = {key_file}
            """).format(key_file=self._adc_path))
      else:
        raise CredentialFileSaveError(
            'Unsupported credentials type {0}'.format(type(self.credentials)))
    else:  # P12 service account
      cred = self.credentials
      key = cred._private_key_pkcs12  # pylint: disable=protected-access
      password = cred._private_key_password  # pylint: disable=protected-access

      with files.OpenForWritingPrivate(self._p12_key_path, binary=True) as pk:
        pk.write(key)

      # the .boto file gets some different fields
      self._WriteFileContents(self._gsutil_path, textwrap.dedent("""\
          [Credentials]
          gs_service_client_id = {account}
          gs_service_key_file = {key_file}
          gs_service_key_file_password = {key_password}
          """).format(account=self.credentials.service_account_email,
                      key_file=self._p12_key_path,
                      key_password=password))

  def _WriteFileContents(self, filepath, contents):
    """Writes contents to a path, ensuring mkdirs.

    Args:
      filepath: str, The path of the file to write.
      contents: str, The contents to write to the file.
    """

    full_path = os.path.realpath(os.path.expanduser(filepath))

    try:
      with files.OpenForWritingPrivate(full_path) as cred_file:
        cred_file.write(contents)
    except (OSError, IOError), e:
      raise Exception('Failed to open %s for writing: %s' % (filepath, e))
