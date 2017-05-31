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

"""A module to get a credentialed http object for making API calls."""


from googlecloudsdk.core import exceptions
from googlecloudsdk.core import http
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.credentials import store

from oauth2client import client


class Error(exceptions.Error):
  """Exceptions for the http module."""


def Http(timeout='unset'):
  """Get an httplib2.Http client for working with the Google API.

  Args:
    timeout: double, The timeout in seconds to pass to httplib2.  This is the
        socket level timeout.  If timeout is None, timeout is infinite.  If
        default argument 'unset' is given, a sensible default is selected.

  Returns:
    An authorized httplib2.Http client object, or a regular httplib2.Http object
    if no credentials are available.

  Raises:
    c_store.Error: If an error loading the credentials occurs.
  """
  http_client = http.Http(timeout=timeout)

  authority_selector = properties.VALUES.auth.authority_selector.Get()
  authorization_token_file = (
      properties.VALUES.auth.authorization_token_file.Get())
  if authority_selector or authorization_token_file:
    http_client = _WrapRequestForIAMAuth(
        http_client, authority_selector, authorization_token_file)

  creds = store.LoadIfEnabled()
  if creds:
    http_client = creds.authorize(http_client)
    # Wrap the request method to put in our own error handling.
    http_client = http.Modifiers.WrapRequest(
        http_client, [], _HandleAuthError, client.AccessTokenRefreshError)

  return http_client


def _WrapRequestForIAMAuth(http_client, authority_selector,
                           authorization_token_file):
  """Wrap request with IAM authority seelctor.

  Args:
    http_client: The original http object.
    authority_selector: str, The authority selector string we want to use for
        the request.
    authorization_token_file: str, The file that contains the authorization
        token we want to use for the request.

  Returns:
    http: The same http object but with the request method wrapped.
  """
  authorization_token = None
  if authorization_token_file:
    try:
      authorization_token = open(authorization_token_file, 'r').read()
    except IOError as e:
      raise Error(e)

  handlers = []
  if authority_selector:
    handlers.append(http.Modifiers.Handler(
        http.Modifiers.SetHeader('x-goog-iam-authority-selector',
                                 authority_selector)))

  if authorization_token:
    handlers.append(http.Modifiers.Handler(
        http.Modifiers.SetHeader('x-goog-iam-authorization-token',
                                 authorization_token)))

  return http.Modifiers.WrapRequest(http_client, handlers)


def _HandleAuthError(e):
  """Handle a generic auth error and raise a nicer message.

  Args:
    e: The exception that was caught.

  Raises:
    sore.TokenRefreshError: If an auth error occurs.
  """
  log.debug('Exception caught during HTTP request: %s', e.message,
            exc_info=True)
  raise store.TokenRefreshError(e.message)
