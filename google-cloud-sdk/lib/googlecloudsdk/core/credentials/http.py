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


def Http(timeout='unset', disable_resource_quota=False):
  """Get an httplib2.Http client for working with the Google API.

  Args:
    timeout: double, The timeout in seconds to pass to httplib2.  This is the
        socket level timeout.  If timeout is None, timeout is infinite.  If
        default argument 'unset' is given, a sensible default is selected.
    disable_resource_quota: bool, By default, we are going to tell APIs to use
        the quota of the project being operated on. For some APIs we want to use
        gcloud's quota, so you can explicitly disable that behavior by passing
        True here.

  Returns:
    An authorized httplib2.Http client object, or a regular httplib2.Http object
    if no credentials are available.

  Raises:
    c_store.Error: If an error loading the credentials occurs.
  """
  http_client = http.Http(timeout=timeout)

  # Wrappers for IAM header injection.
  authority_selector = properties.VALUES.auth.authority_selector.Get()
  authorization_token_file = (
      properties.VALUES.auth.authorization_token_file.Get())
  handlers = _GetIAMAuthHandlers(authority_selector, authorization_token_file)

  # Inject the resource project header for quota unless explicitly disabled.
  if not (disable_resource_quota or
          properties.VALUES.billing.disable_resource_project_quota.GetBool()):
    quota_project = (properties.VALUES.billing.quota_project.Get() or
                     properties.VALUES.core.project.Get())
    handlers.append(http.Modifiers.Handler(
        http.Modifiers.SetHeader('X-Goog-User-Project', quota_project)))

  creds = store.LoadIfEnabled()
  if creds:
    http_client = creds.authorize(http_client)
    # Wrap the request method to put in our own error handling.
    http_client = http.Modifiers.WrapRequest(
        http_client, handlers, _HandleAuthError, client.AccessTokenRefreshError)

  return http_client


def _GetIAMAuthHandlers(authority_selector, authorization_token_file):
  """Get the request handlers for IAM authority selctors and auth tokens..

  Args:
    authority_selector: str, The authority selector string we want to use for
        the request or None.
    authorization_token_file: str, The file that contains the authorization
        token we want to use for the request or None.

  Returns:
    [http.Modifiers]: A list of request modifier functions to use to wrap an
    http request.
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

  return handlers


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
