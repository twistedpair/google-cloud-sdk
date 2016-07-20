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

import datetime
import os
import textwrap

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import http
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.credentials import devshell as c_devshell
from googlecloudsdk.core.credentials import gce as c_gce
from googlecloudsdk.core.credentials import legacy
from googlecloudsdk.core.util import files
import httplib2
from oauth2client import client
from oauth2client import multistore_file
from oauth2client.contrib import gce as oauth2client_gce


GOOGLE_OAUTH2_PROVIDER_AUTHORIZATION_URI = (
    'https://accounts.google.com/o/oauth2/auth')
GOOGLE_OAUTH2_PROVIDER_REVOKE_URI = (
    'https://accounts.google.com/o/oauth2/revoke')
GOOGLE_OAUTH2_PROVIDER_TOKEN_URI = (
    'https://accounts.google.com/o/oauth2/token')


REDIRECT_URI_AUTH_CODE_IN_TITLE_BAR = 'urn:ietf:wg:oauth:2.0:oob'


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


class InvalidCredentialFileException(Error):
  """Exception for when an external credential file could not be loaded."""

  def __init__(self, f, e):
    super(InvalidCredentialFileException, self).__init__(
        'Failed to load credential file: [{f}].  {message}'
        .format(f=f, message=str(e)))


class FlowError(Error):
  """Exception for when something goes wrong with a web flow."""


class RevokeError(Error):
  """Exception for when there was a problem revoking."""


def _GetStorageKeyForAccount(account):
  return {
      'type': 'google-cloud-sdk',
      'account': account,
  }


# TODO(user): use _GetStorageKeyForAccount instead, but in meantime since the
# key format has changed this will not invalidate existing auth credentials and
# will move over existing credentials under new key format.
def _FindStorageKeyForAccount(account):
  """Scans credential file for keys matching given account.

  If such key(s) is found it checks that current set of scopes is a subset of
  scopes associated with the key.

  Args:
    account: str, The account tied to the storage key being fetched.

  Returns:
    dict, key to be used in the credentials store.
  """
  storage_path = config.Paths().credentials_path
  current_scopes = set(config.CLOUDSDK_SCOPES)
  equivalent_keys = [key for key in
                     multistore_file.get_all_credential_keys(
                         filename=storage_path)
                     if (key.get('type') == 'google-cloud-sdk' and
                         key.get('account') == account and (
                             'scope' not in key or
                             set(key.get('scope').split()) >= current_scopes))]

  preferred_key = _GetStorageKeyForAccount(account)
  if preferred_key in equivalent_keys:
    equivalent_keys.remove(preferred_key)
  elif equivalent_keys:  # Migrate credentials over to new key format.
    storage = multistore_file.get_credential_storage_custom_key(
        filename=storage_path,
        key_dict=equivalent_keys[0])
    creds = storage.get()
    storage = multistore_file.get_credential_storage_custom_key(
        filename=storage_path,
        key_dict=preferred_key)
    storage.put(creds)

  # Remove all other entries.
  for key in equivalent_keys:
    storage = multistore_file.get_credential_storage_custom_key(
        filename=storage_path,
        key_dict=key)
    storage.delete()

  return preferred_key


def _StorageForAccount(account):
  """Get the oauth2client.multistore_file storage.

  Args:
    account: str, The account tied to the storage being fetched.

  Returns:
    oauth2client.client.Storage, A credentials store.
  """
  storage_path = config.Paths().credentials_path
  parent_dir, unused_name = os.path.split(storage_path)
  files.MakeDir(parent_dir)

  storage = multistore_file.get_credential_storage_custom_key(
      filename=storage_path,
      key_dict=_FindStorageKeyForAccount(account))
  return storage


def AvailableAccounts():
  """Get all accounts that have credentials stored for the CloudSDK.

  This function will also ping the GCE metadata server to see if GCE credentials
  are available.

  Returns:
    [str], List of the accounts.

  """
  all_keys = multistore_file.get_all_credential_keys(
      filename=config.Paths().credentials_path)

  accounts = [key['account'] for key in all_keys
              if key.get('type') == 'google-cloud-sdk']

  accounts.extend(c_gce.Metadata().Accounts())

  devshell_creds = c_devshell.LoadDevshellCredentials()
  if devshell_creds:
    accounts.append(devshell_creds.devshell_response.user_email)

  accounts.sort()

  return accounts


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


def Load(account=None, scopes=None):
  """Get the credentials associated with the provided account.

  Args:
    account: str, The account address for the credentials being fetched. If
        None, the account stored in the core.account property is used.
    scopes: tuple, Custom auth scopes to request. By default CLOUDSDK_SCOPES
        are requested.

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
  """
  # If a credential file is set, just use that and ignore the active account
  # and whatever is in the credential store.
  cred_file_override = properties.VALUES.auth.credential_file_override.Get()
  if cred_file_override:
    log.info('Using alternate credentials from file: [%s]',
             cred_file_override)
    try:
      cred = client.GoogleCredentials.from_stream(cred_file_override)
      if cred.create_scoped_required():
        if scopes is None:
          scopes = config.CLOUDSDK_SCOPES
        cred = cred.create_scoped(scopes)
      return cred
    except client.Error as e:
      raise InvalidCredentialFileException(cred_file_override, e)

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

  store = _StorageForAccount(account)
  if not store:
    raise NoCredentialsForAccountException(account)
  cred = store.get()
  if not cred:
    raise NoCredentialsForAccountException(account)

  # cred.token_expiry is in UTC time.
  if not cred.token_expiry or cred.token_expiry < cred.token_expiry.utcnow():
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
  """
  try:
    creds.refresh(http_client or http.Http())
  except (client.AccessTokenRefreshError, httplib2.ServerNotFoundError) as e:
    raise TokenRefreshError(e.message)


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

  # We never serialize devshell credentials.
  if isinstance(creds, c_devshell.DevshellCredentials):
    return

  if not account:
    account = properties.VALUES.core.account.Get()
  if not account:
    raise NoActiveAccountException()

  store = _StorageForAccount(account)
  store.put(creds)
  creds.set_store(store)
  _GetLegacyGen(account, creds, scopes).WriteTemplate()


def _GetLegacyGen(account, creds, scopes=None):
  if scopes is None:
    scopes = config.CLOUDSDK_SCOPES
  return legacy.LegacyGenerator(
      multistore_path=config.Paths().LegacyCredentialsMultistorePath(account),
      json_path=config.Paths().LegacyCredentialsJSONPath(account),
      gae_java_path=config.Paths().LegacyCredentialsGAEJavaPath(account),
      gsutil_path=config.Paths().LegacyCredentialsGSUtilPath(account),
      key_path=config.Paths().LegacyCredentialsKeyPath(account),
      json_key_path=config.Paths().LegacyCredentialsJSONKeyPath(account),
      credentials=creds, scopes=scopes)


def RevokeCredentials(creds):
  # TODO(user): Remove this condition when oauth2client does not crash while
  # revoking SignedJwtAssertionCredentials.
  if creds and (not client.HAS_CRYPTO or
                not isinstance(creds, client.SignedJwtAssertionCredentials)):
    creds.revoke(http.Http())


def Revoke(account=None):
  """Revoke credentials and clean up related files.

  Args:
    account: str, The account address for the credentials to be revoked. If
        None, the currently active account is used.

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

  creds = Load(account)
  if not creds:
    raise NoCredentialsForAccountException(account)

  if isinstance(creds, c_devshell.DevshellCredentials):
    raise RevokeError(
        'Cannot revoke the automatically provisioned Cloud Shell credential.'
        'This comes from your browser session and will not persist outside'
        'of your connected Cloud Shell session.')

  RevokeCredentials(creds)

  store = _StorageForAccount(account)
  if store:
    store.delete()

  _GetLegacyGen(account, creds).Clean()
  files.RmTree(config.Paths().LegacyCredentialsDir(account))


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

  # pylint:disable=g-import-not-at-top, This is imported on demand for
  # performance reasons.
  from googlecloudsdk.core.credentials import flow

  try:
    cred = flow.Run(webflow, launch_browser=launch_browser, http=http.Http())
  except flow.Error as e:
    raise FlowError(e)
  return cred


def AcquireFromWebFlowAndClientIdFile(client_id_file,
                                      scopes,
                                      launch_browser=True):
  """Get credentials via a web flow.

  Args:
    client_id_file: str, file path with client id information
    scopes: string or iterable of strings, scope(s) of the credentials being
      requested.
    launch_browser: bool, Open a new web browser window for authorization.

  Returns:
    client.Credentials, Newly acquired credentials from the web flow.

  Raises:
    FlowError: If there is a problem with the web flow.
  """
  webflow = client.flow_from_clientsecrets(
      filename=client_id_file,
      scope=scopes,
      redirect_uri=REDIRECT_URI_AUTH_CODE_IN_TITLE_BAR)

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
