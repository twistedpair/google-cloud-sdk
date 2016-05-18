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


def Http(auth=True, creds=None, timeout='unset'):
  """Get an httplib2.Http client for working with the Google API.

  Args:
    auth: bool, True if the http client returned should be authorized.
    creds: oauth2client.client.Credentials, If auth is True and creds is not
        None, use those credentials to authorize the httplib2.Http client.
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

  if auth:
    if not creds:
      creds = store.Load()
    http_client = creds.authorize(http_client)
    # Wrap the request method to put in our own error handling.
    http_client = _WrapRequestForAuthErrHandling(http_client)

  return http_client


# TODO(b/25115137): Refactor the wrapper functions to be more clear.
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
  orig_request = http_client.request

  authorization_token = None
  if authorization_token_file:
    try:
      authorization_token = open(authorization_token_file, 'r').read()
    except IOError as e:
      raise Error(e)

  def RequestWithIAMAuthoritySelector(*args, **kwargs):
    """Wrap request with IAM authority selector.

    Args:
      *args: Positional arguments.
      **kwargs: Keyword arguments.

    Returns:
      Wrapped request with IAM authority selector.
    """
    modified_args = list(args)
    if authority_selector:
      http.RequestArgsSetHeader(
          modified_args, kwargs,
          'x-goog-iam-authority-selector', authority_selector)
    if authorization_token:
      http.RequestArgsSetHeader(
          modified_args, kwargs,
          'x-goog-iam-authorization-token', authorization_token)
    return orig_request(*modified_args, **kwargs)

  http_client.request = RequestWithIAMAuthoritySelector

  # apitools needs this attribute to do credential refreshes during batch API
  # requests.
  if hasattr(orig_request, 'credentials'):
    setattr(http_client.request, 'credentials', orig_request.credentials)

  return http_client


# TODO(b/25115137): Refactor the wrapper functions to be more clear.
def _WrapRequestForAuthErrHandling(http_client):
  """Wrap request with exception handling for auth.

  We need to wrap exception handling because oauth2client does similar wrapping
  when you authorize the http object.  Because of this, a credential refresh
  error can get raised wherever someone makes an http request.  With no common
  place to handle this exception, we do more wrapping here so we can convert it
  to one of our typed exceptions.

  Args:
    http_client: The original http object.

  Returns:
    http, The same http object but with the request method wrapped.
  """
  orig_request = http_client.request

  def RequestWithErrHandling(*args, **kwargs):
    try:
      return orig_request(*args, **kwargs)
    except client.AccessTokenRefreshError as e:
      log.debug('Exception caught during HTTP request: %s', e.message,
                exc_info=True)
      raise store.TokenRefreshError(e.message)

  http_client.request = RequestWithErrHandling

  # apitools needs this attribute to do credential refreshes during batch API
  # requests.  Ideally we would patch the refresh() method on the credentials to
  # catch the same error as above, but if we do, the credentials are no longer
  # serializable.  The batch API bypasses the error handling we add above so
  # we just need a top level error handler in the CLI for that.
  if hasattr(orig_request, 'credentials'):
    setattr(http_client.request, 'credentials', orig_request.credentials)

  return http_client
