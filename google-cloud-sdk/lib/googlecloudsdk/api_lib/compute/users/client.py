# Copyright 2014 Google Inc. All Rights Reserved.
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
"""Common functions for users."""
from socket import gethostname
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.util import time_util
from googlecloudsdk.core import exceptions as core_exceptions


class UserException(core_exceptions.Error):
  """UserException is for non-code-bug errors in user_utils."""


class UserResourceFetcher(object):
  """Mixin class for working with users."""

  def __init__(self, clouduseraccounts, project, http, batch_url):
    self.clouduseraccounts = clouduseraccounts
    self.project = project
    self.http = http
    self.batch_url = batch_url

  def LookupUsers(self, users):
    """Makes a get request for each user in users and returns results."""
    requests = []
    for user in users:
      request = (self.clouduseraccounts.users,
                 'Get',
                 self.clouduseraccounts.MESSAGES_MODULE.
                 ClouduseraccountsUsersGetRequest(
                     project=self.project,
                     user=user))
      requests.append(request)

    errors = []
    res = list(request_helper.MakeRequests(
        requests=requests,
        http=self.http,
        batch_url=self.batch_url,
        errors=errors))
    if errors:
      utils.RaiseException(errors, UserException,
                           error_message='Could not fetch some users:')
    return res

  def LookupUser(self, user):
    return self.LookupUsers([user])[0]

  def CreateUser(self, user, owner_email, description=None):
    """Creates an account service user."""

    user = self.clouduseraccounts.MESSAGES_MODULE.User(
        name=user,
        description=description,
        owner=owner_email,
    )

    request = (
        self.clouduseraccounts.users, 'Insert',
        self.clouduseraccounts.MESSAGES_MODULE.
        ClouduseraccountsUsersInsertRequest(
            project=self.project,
            user=user))

    errors = []
    res = list(request_helper.MakeRequests(
        requests=[request],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors))
    if errors:
      utils.RaiseException(errors, UserException,
                           error_message='Could not create user:')
    return res

  def RemovePublicKey(self, user, fingerprint):
    """Removes a public key from a user."""
    request = (
        self.clouduseraccounts.users, 'RemovePublicKey',
        self.clouduseraccounts.MESSAGES_MODULE
        .ClouduseraccountsUsersRemovePublicKeyRequest(
            project=self.project,
            fingerprint=fingerprint,
            user=user))

    requests = [request]

    errors = []
    res = list(request_helper.MakeRequests(
        requests=requests,
        http=self.http,
        batch_url=self.batch_url,
        errors=errors))
    if errors:
      utils.RaiseException(errors, UserException,
                           error_message='Could not remove public key:')
    return res

  def PublicKeyGenerateUploadRequest(
      self, user_name, public_key, expiration_time=None, description=None):
    """Helper function for uploading public keys to users."""
    public_key_message = self.clouduseraccounts.MESSAGES_MODULE.PublicKey(
        description=description,
        expirationTimestamp=expiration_time,
        key=public_key)

    request = (
        self.clouduseraccounts.users, 'AddPublicKey',
        self.clouduseraccounts.MESSAGES_MODULE
        .ClouduseraccountsUsersAddPublicKeyRequest(
            project=self.project,
            publicKey=public_key_message,
            user=user_name))
    return request

  def UploadPublicKey(self, user, public_key):
    """Uploads a public key to a user."""

    description = 'Added by gcloud compute from {0}'.format(self.GetHostName())
    default_expiration = '1d'
    parser = arg_parsers.Duration()
    expiration_rfc3339_str = time_util.CalculateExpiration(
        parser(default_expiration))

    request = self.PublicKeyGenerateUploadRequest(
        user, public_key, expiration_time=expiration_rfc3339_str,
        description=description)
    requests = [request]

    errors = []
    res = list(request_helper.MakeRequests(
        requests=requests,
        http=self.http,
        batch_url=self.batch_url,
        errors=errors))
    if errors:
      utils.RaiseException(errors, UserException,
                           error_message='Could not upload public key:')
    return res

  def GetHostName(self):
    """Returns the hostname of local user, wrapped for mocking."""
    return gethostname()
