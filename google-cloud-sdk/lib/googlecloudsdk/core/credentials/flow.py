# -*- coding: utf-8 -*- #
# Copyright 2013 Google LLC. All Rights Reserved.
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

"""Run a web flow for oauth2.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib
import json
import select
import socket
import webbrowser
import wsgiref
from google_auth_oauthlib import flow as google_auth_flow

from googlecloudsdk.core import exceptions as c_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import requests
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import pkg_resources

from oauthlib.oauth2.rfc6749 import errors as rfc6749_errors

from requests import exceptions as requests_exceptions
import six
from six.moves import input  # pylint: disable=redefined-builtin
from six.moves.urllib import parse

_PORT_SEARCH_ERROR_MSG = (
    'Failed to start a local webserver listening on any port '
    'between {start_port} and {end_port}. Please check your '
    'firewall settings or locally running programs that may be '
    'blocking or using those ports.')

_PORT_SEARCH_START = 8085
_PORT_SEARCH_END = _PORT_SEARCH_START + 100


class Error(c_exceptions.Error):
  """Exceptions for the flow module."""


class AuthRequestRejectedError(Error):
  """Exception for when the authentication request was rejected."""


class AuthRequestFailedError(Error):
  """Exception for when the authentication request failed."""


class LocalServerCreationError(Error):
  """Exception for when a local server cannot be created."""


class LocalServerTimeoutError(Error):
  """Exception for when the local server timeout before receiving request."""


def RaiseProxyError(source_exc):
  six.raise_from(AuthRequestFailedError(
      'Could not reach the login server. A potential cause of this could be '
      'because you are behind a proxy. Please set the environment variables '
      'HTTPS_PROXY and HTTP_PROXY to the address of the proxy in the format '
      '"protocol://address:port" (without quotes) and try again.\n'
      'Example: HTTPS_PROXY=https://192.168.0.1:8080'), source_exc)


def PromptForAuthCode(message, authorize_url):
  log.err.Print(message.format(url=authorize_url))
  return input('Enter verification code: ').strip()


def CreateGoogleAuthFlow(scopes, client_id_file=None):
  """Creates a Google auth oauthlib browser flow."""
  client_config = _CreateGoogleAuthClientConfig(client_id_file)
  return InstalledAppFlow.from_client_config(
      client_config,
      scopes,
      autogenerate_code_verifier=not properties.VALUES.auth
      .disable_code_verifier.GetBool())


def _CreateGoogleAuthClientConfig(client_id_file=None):
  """Creates a client config from a client id file or gcloud's properties."""
  if client_id_file:
    with files.FileReader(client_id_file) as f:
      return json.load(f)
  return _CreateGoogleAuthClientConfigFromProperties()


def _CreateGoogleAuthClientConfigFromProperties():
  auth_uri = properties.VALUES.auth.auth_host.Get(required=True)
  token_uri = properties.VALUES.auth.token_host.Get(required=True)
  client_id = properties.VALUES.auth.client_id.Get(required=True)
  client_secret = properties.VALUES.auth.client_secret.Get(required=True)
  return {
      'installed': {
          'client_id': client_id,
          'client_secret': client_secret,
          'auth_uri': auth_uri,
          'token_uri': token_uri
      }
  }


@contextlib.contextmanager
def HandleOauth2FlowErrors():
  try:
    yield
  except requests_exceptions.ProxyError as e:
    RaiseProxyError(e)
  except rfc6749_errors.AccessDeniedError as e:
    six.raise_from(AuthRequestRejectedError(e), e)
  except ValueError as e:
    raise six.raise_from(AuthRequestFailedError(e), e)


def _RunGoogleAuthFlowLaunchBrowser(flow):
  """Runs oauth2 3LO flow and auto launch the browser."""
  authorization_prompt_msg_launch_browser = (
      'Your browser has been opened to visit:\n\n    {url}\n')
  with HandleOauth2FlowErrors():
    return flow.run_local_server(
        authorization_prompt_message=authorization_prompt_msg_launch_browser)


def _RunGoogleAuthFlowNoLaunchBrowser(flow):
  """Runs oauth2 3LO flow without auto-launching the browser."""
  authorization_prompt_msg_no_launch_browser = (
      'Go to the following link in your browser:\n\n    {url}\n')
  with HandleOauth2FlowErrors():
    return flow.run_console(
        authorization_prompt_message=authorization_prompt_msg_no_launch_browser)


def RunGoogleAuthFlow(flow, launch_browser=False):
  """Runs a Google auth oauthlib web flow.

  Args:
    flow: InstalledAppFlow, A web flow to run.
    launch_browser: bool, True to launch the web browser automatically and and
      use local server to handle the redirect. False to ask users to paste the
      url in a browser.

  Returns:
    google.auth.credentials.Credentials, The credentials obtained from the flow.
  """
  if launch_browser:
    try:
      return _RunGoogleAuthFlowLaunchBrowser(flow)
    except LocalServerCreationError as e:
      log.warning(e)
      log.warning('Defaulting to URL copy/paste mode.')
  return _RunGoogleAuthFlowNoLaunchBrowser(flow)


class WSGIServer(wsgiref.simple_server.WSGIServer):
  """WSGI server to handle more than one connections.

  A normal WSGI server will handle connections one-by-one. When running a local
  server to handle auth redirects, browser opens two connections. One connection
  is used to send the authorization code. The other one is opened but not used.
  Some browsers (i.e. Chrome) send data in the first connection. Other browsers
  (i.e. Safari) send data in the second connection. To make the server working
  for all these browsers, the server should be able to handle two connections
  and smartly read data from the correct connection.
  """

  # pylint: disable=invalid-name, follow the style of the base class.
  def _conn_closed(self, conn):
    """Check if conn is closed at the client side."""
    return not conn.recv(1024, socket.MSG_PEEK)

  def _handle_closed_conn(self, closed_socket, sockets_to_read,
                          client_connections):
    sockets_to_read.remove(closed_socket)
    client_connections[:] = [
        conn for conn in client_connections if conn[0] is not closed_socket
    ]
    self.shutdown_request(closed_socket)

  def _handle_new_client(self, listening_socket, socket_to_read,
                         client_connections):
    request, client_address = listening_socket.accept()
    client_connections.append((request, client_address))
    socket_to_read.append(request)

  def _handle_non_data_conn(self, data_conn, client_connections):
    for request, _ in client_connections:
      if request is not data_conn:
        self.shutdown_request(request)

  def _find_data_conn_with_client_address(self, data_conn, client_connections):
    for request, client_address in client_connections:
      if request is data_conn:
        return request, client_address

  def _find_data_conn(self):
    """Finds the connection which will be used to send data."""
    sockets_to_read = [self.socket]
    client_connections = []
    while True:
      sockets_ready_to_read, _, _ = select.select(sockets_to_read, [], [])
      for s in sockets_ready_to_read:
        # Listening socket is ready to accept client.
        if s is self.socket:
          self._handle_new_client(s, sockets_to_read, client_connections)
        else:
          if self._conn_closed(s):
            self._handle_closed_conn(s, sockets_to_read, client_connections)
          # Found the connection which will be used to send data.
          else:
            self._handle_non_data_conn(s, client_connections)
            return self._find_data_conn_with_client_address(
                s, client_connections)

  # pylint: enable=invalid-name

  def handle_request(self):
    """Handle one request."""
    request, client_address = self._find_data_conn()
    # The following section largely copies the
    # socketserver.BaseSever._handle_request_noblock.
    if self.verify_request(request, client_address):
      try:
        self.process_request(request, client_address)
      except Exception:  # pylint: disable=broad-except
        self.handle_error(request, client_address)
        self.shutdown_request(request)
      except:
        self.shutdown_request(request)
        raise
    else:
      self.shutdown_request(request)


class InstalledAppFlow(google_auth_flow.InstalledAppFlow):
  """Installed app flow.

  This class overrides base class's run_local_server() method to provide
  customized behaviors for gcloud auth login:
    1. Try to find an available port for the local server which handles the
       redirect.
    2. A WSGI app on the local server which can direct browser to
       Google's confirmation pages for authentication.

  This class overrides base class's run_console() method so that the auth code
  fetching step can be easily mocked in login integration testing.
  """

  def __init__(
      self, oauth2session, client_type, client_config,
      redirect_uri=None, code_verifier=None,
      autogenerate_code_verifier=False):
    """Initializes a google_auth_flow.InstalledAppFlow.

    Args:
        oauth2session (requests_oauthlib.OAuth2Session):
            The OAuth 2.0 session from ``requests-oauthlib``.
        client_type (str): The client type, either ``web`` or
            ``installed``.
        client_config (Mapping[str, Any]): The client
            configuration in the Google `client secrets`_ format.
        redirect_uri (str): The OAuth 2.0 redirect URI if known at flow
            creation time. Otherwise, it will need to be set using
            :attr:`redirect_uri`.
        code_verifier (str): random string of 43-128 chars used to verify
            the key exchange.using PKCE.
        autogenerate_code_verifier (bool): If true, auto-generate a
            code_verifier.
    .. _client secrets:
        https://developers.google.com/api-client-library/python/guide
        /aaa_client_secrets
    """
    session = requests.GetSession(session=oauth2session)
    super(InstalledAppFlow, self).__init__(
        session, client_type, client_config,
        redirect_uri, code_verifier,
        autogenerate_code_verifier)
    self.app = None
    self.server = None

  def initialize_server(self):
    if not self.app or not self.server:
      self.app = _RedirectWSGIApp()
      self.server = CreateLocalServer(self.app, _PORT_SEARCH_START,
                                      _PORT_SEARCH_END)

  def run_local_server(self,
                       host='localhost',
                       authorization_prompt_message=google_auth_flow
                       .InstalledAppFlow._DEFAULT_AUTH_PROMPT_MESSAGE,
                       **kwargs):
    """Run the flow using the server strategy.

    The server strategy instructs the user to open the authorization URL in
    their browser and will attempt to automatically open the URL for them.
    It will start a local web server to listen for the authorization
    response. Once authorization is complete the authorization server will
    redirect the user's browser to the local web server. The web server
    will get the authorization code from the response and shutdown. The
    code is then exchanged for a token.

    Args:
        host: str, The hostname for the local redirect server. This will
          be served over http, not https.
        authorization_prompt_message: str, The message to display to tell
          the user to navigate to the authorization URL.
        **kwargs: Additional keyword arguments passed through to
          authorization_url`.

    Returns:
        google.oauth2.credentials.Credentials: The OAuth 2.0 credentials
          for the user.

    Raises:
      LocalServerTimeoutError: If the local server handling redirection timeout
        before receiving the request.
    """
    self.initialize_server()

    self.redirect_uri = 'http://{}:{}/'.format(host, self.server.server_port)
    auth_url, _ = self.authorization_url(**kwargs)

    webbrowser.open(auth_url, new=1, autoraise=True)

    log.err.Print(authorization_prompt_message.format(url=auth_url))
    self.server.handle_request()
    self.server.server_close()

    if not self.app.last_request_uri:
      raise LocalServerTimeoutError(
          'Local server timed out before receiving the redirection request.')
    # Note: using https here because oauthlib requires that
    # OAuth 2.0 should only occur over https.
    authorization_response = self.app.last_request_uri.replace(
        'http:', 'https:')
    # TODO (b/204953716): Remove verify=None
    self.fetch_token(
        authorization_response=authorization_response, include_client_id=True,
        verify=None)

    return self.credentials

  def run_console(self,
                  authorization_prompt_message=google_auth_flow.InstalledAppFlow
                  ._DEFAULT_AUTH_PROMPT_MESSAGE,
                  **kwargs):
    """Run the flow using the console strategy.

    The console strategy instructs the user to open the authorization URL
    in their browser. Once the authorization is complete the authorization
    server will give the user a code. The user then must copy & paste this
    code into the application. The code is then exchanged for a token.

    Args:
        authorization_prompt_message: str, The message to display to tell the
          user to navigate to the authorization URL.
        **kwargs: Additional keyword arguments passed through to
          'authorization_url'.

    Returns:
        google.oauth2.credentials.Credentials: The OAuth 2.0 credentials
          for the user.
    """
    kwargs.setdefault('prompt', 'consent')

    self.redirect_uri = self._OOB_REDIRECT_URI

    auth_url, _ = self.authorization_url(**kwargs)

    code = PromptForAuthCode(authorization_prompt_message, auth_url)
    # TODO (b/204953716): Remove verify=None
    self.fetch_token(code=code, include_client_id=True, verify=None)

    return self.credentials


def CreateLocalServer(wsgi_app, search_start_port, search_end_port):
  """Creates a local wsgi server.

  Finds an available port in the range of [search_start_port, search_end_point)
  for the local server.

  Args:
    wsgi_app: A wsgi app running on the local server.
    search_start_port: int, the port where the search starts.
    search_end_port: int, the port where the search ends.

  Raises:
    LocalServerCreationError: If it cannot find an available port for
      the local server.

  Returns:
    WSGISever, a wsgi server.
  """
  port = search_start_port
  local_server = None
  while not local_server and port < search_end_port:
    try:
      local_server = wsgiref.simple_server.make_server(
          'localhost',
          port,
          wsgi_app,
          server_class=WSGIServer,
          handler_class=google_auth_flow._WSGIRequestHandler)  # pylint:disable=protected-access
    except (socket.error, OSError):
      port += 1
  if local_server:
    return local_server
  raise LocalServerCreationError(
      _PORT_SEARCH_ERROR_MSG.format(
          start_port=search_start_port, end_port=search_end_port - 1))


class _RedirectWSGIApp(object):
  """WSGI app to handle the authorization redirect.

  Stores the request URI and responds with a confirmation page.
  """

  def __init__(self):
    self.last_request_uri = None

  def __call__(self, environ, start_response):
    """WSGI Callable.

    Args:
        environ (Mapping[str, Any]): The WSGI environment.
        start_response (Callable[str, list]): The WSGI start_response callable.

    Returns:
        Iterable[bytes]: The response body.
    """
    start_response(
        six.ensure_str('200 OK'),
        [(six.ensure_str('Content-type'), six.ensure_str('text/html'))])
    self.last_request_uri = wsgiref.util.request_uri(environ)
    query = self.last_request_uri.split('?', 1)[-1]
    query = dict(parse.parse_qsl(query))
    if 'code' in query:
      page = 'oauth2_landing.html'
    else:
      page = 'oauth2_landing_error.html'
    return [pkg_resources.GetResource(__name__, page)]
