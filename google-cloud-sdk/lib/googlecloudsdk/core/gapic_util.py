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
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import requests
from googlecloudsdk.core import transport
from googlecloudsdk.core.credentials import creds
from googlecloudsdk.core.credentials import store


class MissingStoredCredentialsError(exceptions.Error):
  """Indicates stored credentials do not exist or are not available."""


def GetGapicCredentials(enable_resource_quota=True,
                        allow_account_impersonation=True):
  """Returns a credential object for use by gapic client libraries.

  Currently, we set _quota_project on the credentials, unlike for http requests,
  which add quota project through request wrapping to implement
  go/gcloud-quota-model-v2.

  Additionally, we wrap the refresh method and plug in our own
  google.auth.transport.Request object that uses our transport.

  Args:
    enable_resource_quota: bool, By default, we are going to tell APIs to use
        the quota of the project being operated on. For some APIs we want to use
        gcloud's quota, so you can explicitly disable that behavior by passing
        False here.
    allow_account_impersonation: bool, True to allow use of impersonated service
        account credentials for calls made with this client. If False, the
        active user credentials will always be used.

  Returns:
    A google auth credentials.Credentials object.

  Raises:
    MissingStoredCredentialsError: If a google-auth credential cannot be loaded.
  """

  stored_credentials = store.LoadIfEnabled(
      allow_account_impersonation=allow_account_impersonation,
      use_google_auth=True)
  if not creds.IsGoogleAuthCredentials(stored_credentials):
    raise MissingStoredCredentialsError('Unable to load credentials')

  if enable_resource_quota:
    # pylint: disable=protected-access
    stored_credentials._quota_project_id = creds.GetQuotaProject(credentials)

  # In order to ensure that credentials.Credentials:refresh is called with a
  # google.auth.transport.Request that uses our transport, we ignore the request
  # argument that is passed in and plug in our own.
  original_refresh = stored_credentials.refresh
  def WrappedRefresh(request):
    del request  # unused
    return original_refresh(requests.GoogleAuthRequest())
  stored_credentials.refresh = WrappedRefresh

  return stored_credentials


def MakeClient(client_class, address=None,
               enable_resource_quota=True,
               allow_account_impersonation=True):
  """Instantiates a gapic API client with gcloud defaults and configuration.


  grpc cannot be packaged like our other Python dependencies, due to platform
  differences and must be installed by the user. googlecloudsdk.core.gapic
  depends on grpc and must be imported lazily here so that this module can be
  imported safely anywhere.

  Args:
    client_class: a gapic client class.
    address: str, API endpoint override.
    enable_resource_quota: bool, By default, we are going to tell APIs to use
        the quota of the project being operated on. For some APIs we want to use
        gcloud's quota, so you can explicitly disable that behavior by passing
        False here.
    allow_account_impersonation: bool, True to allow use of impersonated service
        account credentials for calls made with this client. If False, the
        active user credentials will always be used.

  Returns:
    requests.Response object
  """
  # pylint: disable=g-import-not-at-top
  from googlecloudsdk.core import gapic_util_internal
  import google.api_core.gapic_v1.client_info
  # pylint: enable=g-import-not-at-top

  if not address:
    address = client_class.DEFAULT_ENDPOINT

  gapic_credentials = GetGapicCredentials(
      enable_resource_quota=enable_resource_quota,
      allow_account_impersonation=allow_account_impersonation)
  return client_class(
      transport=gapic_util_internal.MakeTransport(
          client_class.get_transport_class(), address, gapic_credentials),
      client_info=google.api_core.gapic_v1.client_info.ClientInfo(
          user_agent=transport.MakeUserAgentString())
      )
