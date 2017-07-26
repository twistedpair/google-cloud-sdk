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
"""Convenience functions for dealing with gaia accounts."""

from apitools.base.py import credentials_lib

from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core.credentials import store as c_store

# API restriction: account names cannot be greater than 32 characters.
_MAX_ACCOUNT_NAME_LENGTH = 32


class GaiaException(core_exceptions.Error):
  """GaiaException is for non-code-bug errors in gaia."""


def MapGaiaEmailToDefaultAccountName(email):
  """Returns the default account name given a GAIA email."""
  # Maps according to following rules:
  # 1) Remove all characters following and including '@'.
  # 2) Lowercase all alpha characters.
  # 3) Replace all non-alphanum characters with '_'.
  # 4) Prepend with 'g' if the username does not start with an alpha character.
  # 5) Truncate the username to 32 characters.
  account_name = email.partition('@')[0].lower()
  if not account_name:
    raise GaiaException('Invalid email address [{email}].'
                        .format(email=email))
  account_name = ''.join(
      [char if char.isalnum() else '_' for char in account_name])
  if not account_name[0].isalpha():
    account_name = 'g' + account_name
  return account_name[:_MAX_ACCOUNT_NAME_LENGTH]


def GetDefaultAccountName(http):
  return MapGaiaEmailToDefaultAccountName(GetAuthenticatedGaiaEmail(http))


def GetAuthenticatedGaiaEmail(http):
  """Get the email associated with the active credentails."""
  # If there are no credentials in the c_store c_store.Load() will throw an
  # error with a nice message on how to get credentials.
  email = credentials_lib.GetUserinfo(c_store.Load(), http).get('email')
  # GetUserinfo depends on the token having either the userinfo.email or
  # userinfo.profile scope for the given token. Otherwise it will return empty
  # JSON and email will be None.
  if not email:
    raise c_store.AuthenticationException(
        'An error occured while obtaining your email from your active'
        ' credentials.')
  return email
