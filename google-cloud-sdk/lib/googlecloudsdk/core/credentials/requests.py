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

"""A module to get a credentialed http object for making API calls."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import requests
from googlecloudsdk.core.credentials import creds as core_creds
from googlecloudsdk.core.credentials import transport

import httplib2
from google.auth.transport import requests as google_auth_requests


class Error(exceptions.Error):
  """Exceptions for this module."""


class UnsupportedCredentialsException(Error):
  """An error for when we fail to determine the type of the credentials."""


def GetSession(timeout='unset',
               response_encoding=None,
               ca_certs=None,
               enable_resource_quota=True,
               force_resource_quota=False,
               allow_account_impersonation=True):
  """Get requests.Session object for working with the Google API.

  Args:
    timeout: double, The timeout in seconds to pass to httplib2.  This is the
        socket level timeout.  If timeout is None, timeout is infinite.  If
        default argument 'unset' is given, a sensible default is selected.
    response_encoding: str, the encoding to use to decode the response.
    ca_certs: str, absolute filename of a ca_certs file that overrides the
        default
    enable_resource_quota: bool, By default, we are going to tell APIs to use
        the quota of the project being operated on. For some APIs we want to use
        gcloud's quota, so you can explicitly disable that behavior by passing
        False here.
    force_resource_quota: bool, If true resource project quota will be used by
      this client regardless of the settings in gcloud. This should be used for
      newer APIs that cannot work with legacy project quota.
    allow_account_impersonation: bool, True to allow use of impersonated service
      account credentials for calls made with this client. If False, the active
      user credentials will always be used.

  Returns:
    1. A regular requests.Session object if no credentials are available;
    2. Or an authorized requests.Session object authorized by google-auth
       credentials.

  Raises:
    c_store.Error: If an error loading the credentials occurs.
    UnsupportedCredentialsException: If the attached credentails are not
      supported by requests.
  """
  session = requests.GetSession(timeout=timeout,
                                response_encoding=response_encoding,
                                ca_certs=ca_certs)
  session = RequestWrapper().WrapCredentials(
      session, enable_resource_quota, force_resource_quota,
      allow_account_impersonation)

  if hasattr(session, '_googlecloudsdk_credentials'):
    creds = session._googlecloudsdk_credentials  # pylint: disable=protected-access
    # The requests transport only supports google auth credentials
    if not core_creds.IsGoogleAuthCredentials(creds):
      raise UnsupportedCredentialsException(
          'Requests does not support credentials of this type: {}'.format(
              creds))
  return session


class RequestWrapper(transport.CredentialWrappingMixin,
                     requests.RequestWrapper):
  """Class for wrapping requests.Session requests."""

  def AuthorizeClient(self, http_client, creds):
    """Returns an http_client authorized with the given credentials."""
    orig_request = http_client.request

    def WrappedRequest(method, url, data=None, headers=None, **kwargs):
      auth_request = google_auth_requests.Request(http_client)
      creds.before_request(auth_request, method, url, headers)
      return orig_request(method, url, data=data, headers=headers or {},
                          **kwargs)

    http_client.request = WrappedRequest
    return http_client


class _GoogleAuthApitoolsCredentials():

  def __init__(self, credentials):
    self.credentials = credentials

  def refresh(self, http_client):  # pylint: disable=invalid-name
    auth_request = google_auth_requests.Request(http_client)
    self.credentials.refresh(auth_request)


def GetApitoolsRequests(session):
  """Returns an authenticated httplib2.Http-like object for use by apitools."""
  http_client = _ApitoolsRequests(session)
  # apitools needs this attribute to do credential refreshes during batch API
  # requests.
  if hasattr(session, '_googlecloudsdk_credentials'):
    creds = _GoogleAuthApitoolsCredentials(
        session._googlecloudsdk_credentials)  # pylint: disable=protected-access

    orig_request_method = http_client.request
    # The closure that will replace 'httplib2.Http.request'.
    def Request(*args, **kwargs):
      return orig_request_method(*args, **kwargs)

    http_client.request = Request
    setattr(http_client.request, 'credentials', creds)

  return http_client


class _ApitoolsRequests():
  """A httplib2.Http-like object for use by apitools."""

  def __init__(self, session):
    self.session = session

  def request(
      self,
      uri,
      method='GET',
      body=None,
      headers=None,
      redirections=None,
      connection_type=None,
  ):  # pylint: disable=invalid-name
    """Makes an HTTP request using httplib2 semantics."""
    del connection_type  # Unused

    self.session.max_redirects = redirections
    response = self.session.request(method, uri, data=body, headers=headers)
    headers = dict(response.headers)
    headers['status'] = response.status_code

    if response.encoding is not None:
      content = response.text
    else:
      content = response.content

    return httplib2.Response(headers), content
