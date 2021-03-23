# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Helper Classes for using gapic clients in gcloud."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from google.auth import credentials
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core.credentials import creds
from googlecloudsdk.core.credentials import store


class MissingStoredCredentialsError(Exception):
  """Indicates stored credentials do not exist or are not available."""


class StoredCredentials(credentials.Credentials):
  """Implements the Credentials interface required by gapic."""

  def __init__(self,
               enable_resource_quota=True,
               force_resource_quota=False,
               allow_account_impersonation=True):
    super(StoredCredentials, self).__init__()
    self.stored_credentials = store.LoadIfEnabled(
        allow_account_impersonation=allow_account_impersonation,
        use_google_auth=True)
    if self.stored_credentials is None:
      raise MissingStoredCredentialsError()
    if creds.IsOauth2ClientCredentials(self.stored_credentials):
      self.token = self.stored_credentials.access_token
    else:
      self.token = self.stored_credentials.token
    if enable_resource_quota or force_resource_quota:
      self._quota_project_id = creds.GetQuotaProject(self.stored_credentials,
                                                     force_resource_quota)
    else:
      self._quota_project_id = None

  def refresh(self, request):
    pass


class NoGRPCInstalledError(exceptions.ToolException):
  """Unable to import grpc-based modules."""

  def __init__(self):
    super(NoGRPCInstalledError, self).__init__(
        'Please ensure the grpc module is installed.  Run:\n'
        'pip install grpcio')


def MakeClient(transport_class, client_class, address=None):
  """Instantiates a gapic API client with gcloud defaults and configuration."""
  if not address:
    address = client_class.SERVICE_ADDRESS

  transport = transport_class(credentials=StoredCredentials(),
                              address=address)
  return client_class(transport=transport)
