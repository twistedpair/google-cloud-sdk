# Copyright 2017 Google Inc. All Rights Reserved.
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

"""Utilities to manage credentials."""

import abc
import enum

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.credentials import devshell as c_devshell
from oauth2client import client
from oauth2client import service_account
from oauth2client.contrib import gce as oauth2client_gce
from oauth2client.contrib import multistore_file


class Error(exceptions.Error):
  """Exceptions for this module."""


class UnknownCredentialsType(Error):
  """An error for when we fail to determine the type of the credentials."""
  pass


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


def GetCredentialStore():
  return Oauth2ClientCredentialStore(config.Paths().credentials_path)


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


class CredentialType(enum.Enum):
  """Enum of credential types managed by gcloud."""

  UNKNOWN = (0, 'unknown', False)
  USER_ACCOUNT = (1, client.AUTHORIZED_USER, True)
  SERVICE_ACCOUNT = (2, client.SERVICE_ACCOUNT, True)
  P12_SERVICE_ACCOUNT = (3, 'service_account_p12', True)
  DEVSHELL = (4, 'devshell', False)
  GCE = (5, 'gce', False)

  def __init__(self, type_id, key, is_serializable):
    self.type_id = type_id
    self.key = key
    self.is_serializable = is_serializable

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
