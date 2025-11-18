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

"""A module to get an unauthenticated requests.Session object."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import atexit
import collections
import inspect
import io
import json
import os
import secrets
import socket
import subprocess
import sys
import time

from google.auth.transport import requests as google_auth_requests
from google.auth.transport.requests import _MutualTlsOffloadAdapter
from googlecloudsdk.core import context_aware
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import transport
from googlecloudsdk.core.util import encoding
from googlecloudsdk.core.util import http_proxy_types
from googlecloudsdk.core.util import platforms
import httplib2
import requests
import six
from six.moves import http_client as httplib
from six.moves import urllib
import socks
from urllib3.util.ssl_ import create_urllib3_context

try:
  import urllib.request as urllib_request  # pylint: disable=g-import-not-at-top
except ImportError:  # PY2
  import urllib as urllib_request  # pylint: disable=g-import-not-at-top


_INVALID_HTTPS_PROXY_ENV_VAR_WARNING = (
    'It appears that the current proxy configuration is using an HTTPS scheme '
    'for contacting the proxy server, which likely indicates an error in your '
    'HTTPS_PROXY environment variable setting. This can usually be resolved '
    'by setting HTTPS_PROXY=http://... instead of HTTPS_PROXY=https://... '
    'See https://cloud.google.com/sdk/docs/proxy-settings for more information.'
)
_invalid_https_proxy_env_var_warning_shown = False


def GetSession(timeout='unset',
               ca_certs=None,
               session=None,
               streaming_response_body=False,
               redact_request_body_reason=None,
               client_certificate=None,
               client_key=None,):
  """Get a requests.Session that is properly configured for use by gcloud.

  This method does not add credentials to the client. For a requests.Session
  that has been authenticated, use core.credentials.requests.GetSession().

  Args:
    timeout: double, The timeout in seconds. This is the
        socket level timeout. If timeout is None, timeout is infinite. If
        default argument 'unset' is given, a sensible default is selected using
        transport.GetDefaultTimeout().
    ca_certs: str, absolute filename of a ca_certs file that overrides the
        default. The gcloud config property for ca_certs, in turn, overrides
        this argument.
    session: requests.Session instance
    streaming_response_body: bool, True indicates that the response body will
        be a streaming body.
    redact_request_body_reason: str, the reason why the request body must be
        redacted if --log-http is used. If None, the body is not redacted.
    client_certificate: str, absolute filename of a client_certificate file that
        is set explicitly for client certificate authentication
    client_key: str, absolute filename of a client_key file that
        is set explicitly for client certificate authentication

  Returns:
    A requests.Session object configured with all the required settings
    for gcloud.
  """
  http_client = _CreateRawSession(timeout, ca_certs, session,
                                  client_certificate, client_key)
  http_client = RequestWrapper().WrapWithDefaults(
      http_client,
      streaming_response_body=streaming_response_body,
      redact_request_body_reason=redact_request_body_reason)
  return http_client


class ClientSideCertificate(
    collections.namedtuple('ClientSideCertificate',
                           ['certfile', 'keyfile', 'password'])):
  """Holds information about a client side certificate.

  Attributes:
    certfile: str, path to a cert file.
    keyfile: str, path to a key file.
    password: str, password to the private key.
  """

  def __new__(cls, certfile, keyfile, password=None):
    return super(ClientSideCertificate, cls).__new__(
        cls, certfile, keyfile, password)


def CreateSSLContext():
  """Returns a urrlib3 SSL context."""
  return create_urllib3_context()


class HTTPAdapter(requests.adapters.HTTPAdapter):
  """Transport adapter for requests.

  Transport adapters provide an interface to extend the default behavior of the
  requests library using the full power of the underlying urrlib3 library.

  See https://requests.readthedocs.io/en/master/user/advanced/
      #transport-adapters for more information about adapters.
  """

  def __init__(self, client_side_certificate, *args, **kwargs):
    self._cert_info = client_side_certificate
    super(HTTPAdapter, self).__init__(*args, **kwargs)

  def init_poolmanager(self, *args, **kwargs):
    self._add_ssl_context(kwargs)
    return super(HTTPAdapter, self).init_poolmanager(*args, **kwargs)

  def proxy_manager_for(self, *args, **kwargs):
    self._add_ssl_context(kwargs)
    return super(HTTPAdapter, self).proxy_manager_for(*args, **kwargs)

  def _add_ssl_context(self, kwargs):
    if not self._cert_info:
      return

    context = CreateSSLContext()
    context.load_default_certs()

    cert_chain_kwargs = {}
    if self._cert_info.keyfile:
      cert_chain_kwargs['keyfile'] = self._cert_info.keyfile
    if self._cert_info.password:
      cert_chain_kwargs['password'] = self._cert_info.password

    context.load_cert_chain(self._cert_info.certfile, **cert_chain_kwargs)

    kwargs['ssl_context'] = context


def GetProxyInfo():
  """Returns the proxy string for use by requests from gcloud properties.

  See https://requests.readthedocs.io/en/master/user/advanced/#proxies.
  """
  proxy_type = properties.VALUES.proxy.proxy_type.Get()
  proxy_address = properties.VALUES.proxy.address.Get()
  proxy_port = properties.VALUES.proxy.port.GetInt()

  proxy_prop_set = len(
      [f for f in (proxy_type, proxy_address, proxy_port) if f])
  if proxy_prop_set > 0 and proxy_prop_set != 3:
    raise properties.InvalidValueError(
        'Please set all or none of the following properties: '
        'proxy/type, proxy/address and proxy/port')

  if not proxy_prop_set:
    return

  proxy_rdns = properties.VALUES.proxy.rdns.GetBool()
  proxy_user = properties.VALUES.proxy.username.Get()
  proxy_pass = properties.VALUES.proxy.password.Get()

  http_proxy_type = http_proxy_types.PROXY_TYPE_MAP[proxy_type]
  if http_proxy_type == socks.PROXY_TYPE_SOCKS4:
    proxy_scheme = 'socks4a' if proxy_rdns else 'socks4'
  elif http_proxy_type == socks.PROXY_TYPE_SOCKS5:
    proxy_scheme = 'socks5h' if proxy_rdns else 'socks5'
  elif http_proxy_type == socks.PROXY_TYPE_HTTP:
    proxy_scheme = 'http'
  else:
    raise ValueError('Unsupported proxy type: {}'.format(proxy_type))

  if proxy_user or proxy_pass:
    proxy_auth = ':'.join(
        urllib.parse.quote(x) or '' for x in (proxy_user, proxy_pass))
    proxy_auth += '@'
  else:
    proxy_auth = ''
  return '{}://{}{}:{}'.format(proxy_scheme, proxy_auth, proxy_address,
                               proxy_port)


_GOOGLER_BUNDLED_PYTHON_WARNING = (
    'Please use the installed gcloud CLI (`apt install google-cloud-cli`)\n'
    ' This version of gcloud you are currently using will encounter issues due'
    ' to\n changes in internal security policy enforcement in the near'
    ' future.\n\n If this is not possible due to dev requirements, please apply'
    ' for\n policy exemption at go/gcloud-cba-exemption-internal-version-gcloud'
    ' using this error message to self-exempt or reach out to\n'
    ' go/gcloud-cba-investigation for investigation.\n'
)


class ECPProxyError(Exception):
  """Custom exception for errors related to the ECP proxy communication.

  For example, startup failures or receiving a specific proxy error header.
  """

  def __init__(self, message, original_exception=None):
    self.original_exception = original_exception
    super().__init__(
        f'{message}: {original_exception}' if original_exception else message
    )


class _LocalECPProxyAdapter(requests.adapters.HTTPAdapter):
  """A requests adapter that routes HTTPS requests through a local ECP proxy.

  This adapter starts the ECP proxy as a background process upon instantiation
  and manages its lifecycle, terminating it when the adapter is closed.
  This avoids the overhead of starting a new process for every request.
  """

  def __init__(
      self,
      certificate_config_file_path: str,
      gcloud_proxy_url: str = None,
      startup_timeout: int = 5,
      **kwargs,
  ):
    """Initializes the adapter and starts the local ECP proxy process.

    Args:
        certificate_config_file_path: Path to the JSON certificate config file.
        gcloud_proxy_url: Optional URL for proxy chaining.
        startup_timeout: Seconds to wait for the proxy to become available.
        **kwargs: Additional arguments for the HTTPAdapter.
    """
    self.certificate_config_file_path = certificate_config_file_path
    self.gcloud_proxy_url = gcloud_proxy_url

    super().__init__(**kwargs)

    # Register a cleanup function to terminate the proxy process on exit.
    # This is necessary to ensure the proxy process is terminated in case of
    # unexpected termination, such as a crash or keyboard interrupt.
    atexit.register(self.close)

    self.proxy_process = None
    self.proxy_host = 'localhost'
    self.nonce_token = secrets.token_hex(16)
    self.proxy_port = self._start_ecp_proxy_with_retries(
        startup_timeout, max_retries=1
    )

  def _find_free_port(self) -> int:
    """Dynamically finds and returns an available TCP port."""
    with socket.socket() as s:
      s.bind(('', 0))
      return s.getsockname()[1]

  def _start_ecp_proxy_with_retries(
      self, timeout: int, max_retries: int = 1
  ) -> int:
    """Attempts to start the ECP Proxy, retrying on failure.

    This method orchestrates the proxy startup by finding an available port,
    launching the proxy process, and waiting for it to become responsive.
    If the proxy fails to start, it retries the process until either succeeds
    or the maximum number of retries is reached.

    Args:
      timeout: The maximum time in seconds to wait for the proxy to start
      max_retries: The maximum number of times to retry starting the proxy.

    Returns:
      The port number on which the proxy successfully started.

    Raises:
      ECPProxyError: If the proxy fails to start after all retry attempts.
    """

    cert_config = context_aware.GetCertificateConfig(
        self.certificate_config_file_path
    )
    ecp_http_proxy = cert_config.get('libs', {}).get('ecp_http_proxy')
    if not ecp_http_proxy:
      raise ECPProxyError(
          'ECP HTTP proxy binary path is not specified in enterprise'
          ' certificate config file. Cannot use mTLS with ECP if the ECP HTTP'
          ' proxy binary does not exist. Please check the ECP configuration.'
          ' See `gcloud topic client-certificate` to learn more about ECP. \nIf'
          ' this error is unexpected either delete {} or generate a new'
          ' configuration with `$ gcloud auth enterprise-certificate-config'
          ' create --help` '.format(self.certificate_config_file_path)
      )

    for attempt in range(max_retries + 1):
      proxy_port = self._find_free_port()
      self._start_ecp_proxy(
          ecp_http_proxy=ecp_http_proxy, proxy_port=proxy_port
      )

      try:
        self._wait_for_proxy(proxy_port=proxy_port, timeout=timeout)
        return proxy_port
      except ECPProxyError as e:
        if self.proxy_process and self.proxy_process.poll() is None:
          self.proxy_process.terminate()
        if attempt < max_retries:
          log.warning(f'ECP proxy failed to start on port {proxy_port}: {e}')
          continue
        log.error(f'ECP proxy failed to start after {max_retries} retries: {e}')
        raise

  def _start_ecp_proxy(self, *, ecp_http_proxy: str, proxy_port: int) -> None:
    """Launches the local ECP proxy executable as a subprocess.

    Constructs the necessary command-line arguments, including the ECP config
    path, port, nonce token, and an optional upstream proxy URL. It then uses
    subprocess.Popen to start the proxy process in the background.

    Args:
      ecp_http_proxy: The path to the ECP HTTP proxy binary.
      proxy_port: The TCP port for the proxy to listen on.

    Raises:
      ECPProxyError: If the subprocess fails to start due to OSError or
        ValueError.
    """
    log.debug(f'Starting local ECP proxy server on port {proxy_port}')

    args = [
        '-enterprise_certificate_file_path',
        self.certificate_config_file_path,
        '-port',
        str(proxy_port),
        '-nonce_token',
        self.nonce_token,
    ]

    if self.gcloud_proxy_url:
      args.extend(
          ['-gcloud_configured_upstream_proxy_url', self.gcloud_proxy_url]
      )

    proxy_args = execution_utils.ArgsForExecutableTool(ecp_http_proxy, *args)
    try:
      self.proxy_process = subprocess.Popen(
          proxy_args,
          stdout=None,
          stderr=None,
      )
    except (OSError, ValueError) as e:
      log.error(f'Failed to start ECP proxy executable: {e}')
      raise ECPProxyError(
          'Failed to start ECP proxy process', original_exception=e
      ) from e

  def _wait_for_proxy(self, *, proxy_port: int, timeout: int) -> None:
    """Waits for the proxy to become available and verifies its identity.

    This method first waits for the proxy's TCP port to accept connections.
    Once the port is open, it sends a request to the `/readyz` endpoint to
    confirm that the proxy is fully operational and to verify a security nonce,
    ensuring that gcloud is communicating with the correct proxy instance.

    Args:
      proxy_port: The port where the proxy is expected to be listening.
      timeout: The maximum time in seconds to wait for the proxy.

    Raises:
      ECPProxyError: If the proxy process terminates unexpectedly, fails to
        respond within the timeout, or returns an invalid nonce.
    """

    log.debug(f'Waiting for the proxy to be ready on port {proxy_port}...')
    start_time = time.monotonic()

    # Check to see if the port is open.
    while time.monotonic() - start_time < timeout:
      # This is a fast-fail. If the process is dead, stop trying.
      if self.proxy_process.poll() is not None:
        raise ECPProxyError(
            'Proxy process terminated unexpectedly with code '
            f'{self.proxy_process.returncode} while waiting for it to start.'
        )

      try:
        with socket.create_connection(
            (self.proxy_host, proxy_port), timeout=0.1
        ):
          # Proxy is ready, break.
          break
      except OSError:
        time.sleep(0.1)
        continue
    else:
      # The 'while' loop finished without a 'break'.
      # This means we timed out while trying to connect to the socket.
      self.close()  # Clean up the zombie process.
      raise ECPProxyError(
          f'ECP Proxy on {self.proxy_host}:{proxy_port} did not become ready in'
          f' {timeout} seconds.'
      )

    # If we're here, the socket is open.
    # Now we do a one-time verification using the /readyz endpoint.
    try:
      readyz_url = f'http://{self.proxy_host}:{proxy_port}/readyz'
      response = requests.get(readyz_url, timeout=1)
      if response.status_code != 200:
        raise ECPProxyError(
            f'Proxy /readyz endpoint returned status {response.status_code}.'
        )

      server_nonce = response.text
      if server_nonce != self.nonce_token:
        raise ECPProxyError('Nonce mismatch from proxy /readyz endpoint.')

      log.debug('Proxy is ready and nonce verified.')
    except requests.exceptions.RequestException as e:
      # Failed during the HTTP call itself (e.g., connection reset)
      raise ECPProxyError(
          'Failed to verify proxy readiness via /readyz endpoint.',
          original_exception=e,
      ) from e

  def send(self, request, **kwargs):
    """Intercepts an outgoing request and reroutes it through the local ECP proxy.

    This method modifies the request's URL to point to the local proxy and
    adds a custom header (`x-goog-ecpproxy-target-host`) to inform the proxy
    of the original destination. It then sends the modified request and passes
    the response to `_handle_proxy_response` for inspection.

    Args:
      request: The `requests.PreparedRequest` object to send.
      **kwargs: Additional arguments passed to the underlying `send` method.

    Returns:
      The `requests.Response` object from the proxy.

    Raises:
      ECPProxyError: If the proxy returns an error or fails to send the request.
    """
    # Rewrite the request to target the proxy
    original_url = urllib.parse.urlsplit(request.url)
    request.headers['x-goog-ecpproxy-target-host'] = original_url.hostname

    # The new URL for the request is the proxy address + original path/query
    # urlunsplit takes (scheme, netloc, path, query, fragment).
    # The empty strings for scheme, netloc, and fragment ensure that only
    # the path and query components from the original URL are used to form
    # the part of the URL that comes after the proxy address.
    proxy_path = urllib.parse.urlunsplit(
        ('', '', original_url.path, original_url.query, '')
    )
    request.url = f'http://{self.proxy_host}:{self.proxy_port}{proxy_path}'

    # We are connecting to the proxy over HTTP, not HTTPS.
    kwargs['verify'] = False

    log.debug(
        f'Redirecting request for {original_url.geturl()} to proxy at'
        f' {request.url}'
    )
    try:
      response = super().send(request, **kwargs)
    except requests.exceptions.RequestException as e:
      raise ECPProxyError(
          'Failed to send request to proxy', original_exception=e
      ) from e

    return self._handle_proxy_response(response)

  def _handle_proxy_response(self, response):
    """Inspects the proxy's response for custom error headers.

    If the `x-goog-ecpproxy-error` header is present in the response, this
    method assumes the proxy encountered an internal error. It attempts to parse
    a detailed error message from the JSON response body and raises an
    `ECPProxyError` with the relevant information.

    Args:
      response: The `requests.Response` object received from the proxy.

    Returns:
      The original `requests.Response` object if no error header is found.

    Raises:
      ECPProxyError: If the `x-goog-ecpproxy-error` header is present.
    """
    proxy_error_header = response.headers.get('x-goog-ecpproxy-error')
    if proxy_error_header:
      log.error('ECP Proxy returned an error')
      try:
        # Attempt to parse a more detailed error from the JSON body.
        error_details = response.json().get('message', 'No message in body.')
        message = f'ECP Proxy indicated an internal error: {error_details}'
      except json.JSONDecodeError:
        message = (
            'ECP Proxy indicated an internal error. Response body:'
            f' {response.text}'
        )
      raise ECPProxyError(message)

    return response

  def close(self):
    """Terminates the background ECP proxy process to clean up resources.

    This method ensures that the local proxy subprocess is properly shut down
    when the session is closed. It first attempts a graceful termination and
    waits briefly, then forcefully kills the process if it does not exit in
    time. Finally, it calls the parent class's `close` method to complete
    the cleanup.
    """
    log.debug('Closing ECP Proxy Adapter and terminating proxy process...')
    if self.proxy_process and self.proxy_process.poll() is None:
      self.proxy_process.terminate()
      try:
        # Wait a moment for graceful shutdown before killing.
        self.proxy_process.wait(timeout=0.5)
      except subprocess.TimeoutExpired:
        log.warning('Proxy process did not terminate gracefully, killing it.')
        self.proxy_process.kill()
    super().close()


def _CreateMutualTlsOffloadAdapter(
    ca_config: context_aware._EnterpriseCertConfigImpl,
) -> requests.adapters.BaseAdapter:
  """Creates a requests adapter for mTLS offloading via ECP.

  This function decides which adapter to use based on the provided
  configuration:
  - If `ca_config.use_local_proxy` is True, it returns a
    `_LocalECPProxyAdapter`, which routes traffic through a local ECP proxy
    subprocess.
  - Otherwise, it returns a `_MutualTlsOffloadAdapter` from the google-auth
    library, which uses the ECP binary for TLS offloading without a local proxy.

  Args:
      ca_config: The enterprise certificate configuration object.

  Returns:
      An instance of a requests adapter for mTLS offloading.

  Raises:
      ValueError: If the certificate configuration file path is not provided.
  """
  if not ca_config or not ca_config.certificate_config_file_path:
    raise ValueError('Certificate config file path must be provided.')

  if ca_config.use_local_proxy:
    return _LocalECPProxyAdapter(
        certificate_config_file_path=ca_config.certificate_config_file_path,
    )
  else:
    return _MutualTlsOffloadAdapter(ca_config.certificate_config_file_path)


def _LinuxNonbundledPythonAndGooglerCheck():
  """Warn users if running non-bundled Python on Linux and is a Googler.

  Checks if the current OS is Linux, running Python that is not bundled and if
  the user is a Googler. If all conditions are true, a warning message will be
  emitted, along with returning true to bypass the mTLS code path.

  Returns:
    True if the conditions are met, False otherwise.
  """
  is_linux = (
      platforms.OperatingSystem.Current() == platforms.OperatingSystem.LINUX)
  is_bundled_python = sys.executable and 'bundled' in sys.executable
  is_internal_user = properties.IsInternalUserCheck()
  if is_linux and not is_bundled_python and is_internal_user:
    log.warning(_GOOGLER_BUNDLED_PYTHON_WARNING)
    return True
  else:
    return False


def Session(
    timeout=None,
    ca_certs=None,
    disable_ssl_certificate_validation=False,
    session=None,
    client_certificate=None,
    client_key=None):
  """Returns a requests.Session subclass.

  Args:
    timeout: float, Request timeout, in seconds.
    ca_certs: str, absolute filename of a ca_certs file
    disable_ssl_certificate_validation: bool, If true, disable ssl certificate
        validation.
    session: requests.Session instance. Otherwise, a new requests.Session will
        be initialized.
    client_certificate: str, absolute filename of a client_certificate file
    client_key: str, absolute filename of a client_key file

  Returns: A requests.Session subclass.
  """
  session = session or requests.Session()
  proxy_info = GetProxyInfo()

  orig_request_method = session.request
  def WrappedRequest(*args, **kwargs):
    if 'timeout' not in kwargs:
      kwargs['timeout'] = timeout

    # Work around a proxy bug in Python's standard library on Windows.
    if _HasBpo42627() and 'proxies' not in kwargs:
      kwargs['proxies'] = _AdjustProxiesKwargForBpo42627(
          proxy_info, urllib_request.getproxies_environment(),
          orig_request_method, *args, **kwargs)

    return orig_request_method(*args, **kwargs)
  session.request = WrappedRequest

  if proxy_info:
    session.trust_env = False
    session.proxies = {
        'http': proxy_info,
        'https': proxy_info,
    }
  elif _HasInvalidHttpsProxyEnvVarScheme():
    # Requests (and by extension gcloud) currently only supports connecting to
    # proxy servers via HTTP. Until that changes, provide a more informative
    # message when attempting to connect via HTTPS (usually due to a
    # misconfigured HTTPS_PROXY env var), since this now results in a (rather
    # opaque) error as of newer versions of urllib3 (b/228647259#comment30).
    global _invalid_https_proxy_env_var_warning_shown
    if not _invalid_https_proxy_env_var_warning_shown:
      # Just do this once per command invocation to avoid spamming the warning
      # multiple times (we initialize multiple sessions per command).
      _invalid_https_proxy_env_var_warning_shown = True
      log.warning(_INVALID_HTTPS_PROXY_ENV_VAR_WARNING)

  client_side_certificate = None
  if client_certificate is not None and client_key is not None and ca_certs is not None:
    log.debug(
        'Using provided server certificate %s, client certificate %s, client certificate key %s',
        ca_certs, client_certificate, client_key)
    client_side_certificate = ClientSideCertificate(
        client_certificate, client_key)
    adapter = HTTPAdapter(client_side_certificate)
  else:
    ca_config = context_aware.Config()
    if ca_config:
      _LinuxNonbundledPythonAndGooglerCheck()
      if ca_config.config_type == context_aware.ConfigType.ENTERPRISE_CERTIFICATE:
        adapter = _CreateMutualTlsOffloadAdapter(ca_config)
      elif ca_config.config_type == context_aware.ConfigType.ON_DISK_CERTIFICATE:
        log.debug('Using client certificate %s',
                  ca_config.encrypted_client_cert_path)
        client_side_certificate = ClientSideCertificate(
            ca_config.encrypted_client_cert_path,
            ca_config.encrypted_client_cert_path,
            ca_config.encrypted_client_cert_password)
        adapter = HTTPAdapter(client_side_certificate)
      else:
        adapter = HTTPAdapter(None)
    else:
      adapter = HTTPAdapter(None)

  if disable_ssl_certificate_validation:
    session.verify = False
  elif ca_certs:
    session.verify = ca_certs

  session.mount('https://', adapter)
  return session


def _CreateRawSession(timeout='unset', ca_certs=None, session=None,
                      client_certificate=None, client_key=None):
  """Create a requests.Session matching the appropriate gcloud properties."""
  # Compared with setting the default timeout in the function signature (i.e.
  # timeout=300), this lets you test with short default timeouts by mocking
  # GetDefaultTimeout.
  if timeout != 'unset':
    effective_timeout = timeout
  else:
    effective_timeout = transport.GetDefaultTimeout()

  no_validate = properties.VALUES.auth.disable_ssl_validation.GetBool() or False
  ca_certs_property = properties.VALUES.core.custom_ca_certs_file.Get()
  # Believe an explicitly-set ca_certs property over anything we added.
  if ca_certs_property:
    ca_certs = ca_certs_property
  if no_validate:
    ca_certs = None
  return Session(timeout=effective_timeout,
                 ca_certs=ca_certs,
                 disable_ssl_certificate_validation=no_validate,
                 session=session,
                 client_certificate=client_certificate,
                 client_key=client_key)


def _GetURIFromRequestArgs(url, params):
  """Gets the complete URI by merging url and params from the request args."""
  url_parts = urllib.parse.urlsplit(url)
  query_params = urllib.parse.parse_qs(url_parts.query, keep_blank_values=True)
  for param, value in six.iteritems(params or {}):
    query_params[param] = value
  # Need to do this to convert a SplitResult into a list so it can be modified.
  url_parts = list(url_parts)
  # pylint:disable=redundant-keyword-arg, this is valid syntax for this lib
  url_parts[3] = urllib.parse.urlencode(query_params, doseq=True)

  # pylint:disable=too-many-function-args, This is just bogus.
  return urllib.parse.urlunsplit(url_parts)


class Request(transport.Request):
  """Encapsulates parameters for making a general HTTP request.

  This implementation does additional manipulation to ensure that the request
  parameters are specified in the same way as they were specified by the
  caller. That is, if the user calls:
      request('URI', 'GET', None, {'header': '1'})

  After modifying the request, we will call request using positional
  parameters, instead of transforming the request into:
      request('URI', method='GET', body=None, headers={'header': '1'})
  """

  @classmethod
  def FromRequestArgs(cls, *args, **kwargs):
    return cls(*args, **kwargs)

  def __init__(self, method, url, params=None, data=None, headers=None,
               **kwargs):
    self._kwargs = kwargs
    uri = _GetURIFromRequestArgs(url, params)
    super(Request, self).__init__(uri, method, headers or {}, data)

  def ToRequestArgs(self):
    args = [self.method, self.uri]
    kwargs = dict(self._kwargs)
    kwargs['headers'] = self.headers
    if self.body:
      kwargs['data'] = self.body
    return args, kwargs


class Response(transport.Response):
  """Encapsulates responses from making a general HTTP request."""

  @classmethod
  def FromResponse(cls, response):
    return cls(response.status_code, response.headers, response.content)


class RequestWrapper(transport.RequestWrapper):
  """Class for wrapping request.Session requests."""

  request_class = Request
  response_class = Response

  def DecodeResponse(self, response, response_encoding):
    """Returns the response without decoding."""
    del response_encoding  # unused
    # The response decoding is handled by the _ApitoolsRequests.request method.
    return response


def GoogleAuthRequest():
  """Returns a gcloud's requests session to refresh google-auth credentials."""
  session = GetSession()

  # Ensure requests to the GCE metadata server are not proxied. We respect the
  # same env vars for overriding the metadata server hostname/IP as google-auth:
  # https://googleapis.dev/python/google-auth/latest/reference/google.auth.environment_vars.html
  metadata_root = encoding.GetEncodedValue(
      os.environ,
      'GCE_METADATA_HOST',
      encoding.GetEncodedValue(
          os.environ,
          'GCE_METADATA_ROOT',
          'metadata.google.internal'))
  metadata_ip_root = encoding.GetEncodedValue(
      os.environ, 'GCE_METADATA_IP', '169.254.169.254')
  # Ideally we would set 'no_proxy' in the proxies dict, but requests doesn't
  # actually handle this correctly: https://github.com/psf/requests/issues/5000.
  # Instead we specify the hostnames/addresses not to proxy as individual keys
  # with empty values, which works because requests also consider these keys
  # when evaluating whether to proxy a URL.
  session.proxies.update({
      f'http://{metadata_root}': '',
      f'http://{metadata_ip_root}': '',
  })

  return google_auth_requests.Request(session=session)


class _GoogleAuthApitoolsCredentials():

  def __init__(self, credentials):
    self.credentials = credentials

  def refresh(self, http_client):  # pylint: disable=invalid-name
    del http_client  # unused
    auth_request = GoogleAuthRequest()
    self.credentials.refresh(auth_request)


def GetApitoolsRequests(session, response_handler=None, response_encoding=None):
  """Returns an authenticated httplib2.Http-like object for use by apitools."""
  http_client = _ApitoolsRequests(session, response_handler, response_encoding)
  # apitools needs this attribute to do credential refreshes during batch API
  # requests.
  if hasattr(session, '_googlecloudsdk_credentials'):
    creds = _GoogleAuthApitoolsCredentials(session._googlecloudsdk_credentials)  # pylint: disable=protected-access

    orig_request_method = http_client.request

    # The closure that will replace 'httplib2.Http.request'.
    def HttpRequest(*args, **kwargs):
      return orig_request_method(*args, **kwargs)

    http_client.request = HttpRequest
    setattr(http_client.request, 'credentials', creds)

  return http_client


class ResponseHandler(six.with_metaclass(abc.ABCMeta)):
  """Handler to process the Http Response.

  Attributes:
    use_stream: bool, if True, the response body gets returned as a stream
        of data instead of returning the entire body at once.
  """

  def __init__(self, use_stream):
    """Initializes ResponseHandler.

    Args:
      use_stream: bool, if True, the response body gets returned as a stream of
        data instead of returning the entire body at once.
    """
    self.use_stream = use_stream

  @abc.abstractmethod
  def handle(self, response_stream):
    """Handles the http response."""


class _ApitoolsRequests():
  """A httplib2.Http-like object for use by apitools."""

  def __init__(self, session, response_handler=None, response_encoding=None):
    self.session = session
    # Mocks the dictionary of connection instances that apitools iterates over
    # to modify the underlying connection.
    self.connections = {}
    if response_handler:
      if not isinstance(response_handler, ResponseHandler):
        raise ValueError('response_handler should be of type ResponseHandler.')
    self._response_handler = response_handler
    self._response_encoding = response_encoding

  def ResponseHook(self, response, *args, **kwargs):
    """Response hook to be used if response_handler has been set."""
    del args, kwargs  # Unused.
    if response.status_code not in (httplib.OK, httplib.PARTIAL_CONTENT):
      log.debug('Skipping response_handler as response is invalid.')
      return

    if (self._response_handler.use_stream and
        properties.VALUES.core.log_http.GetBool() and
        properties.VALUES.core.log_http_streaming_body.GetBool()):
      # The response_handler uses streaming body, but since a request was
      # made to log the response body, we should retain a copy of the response
      # data. A call to response.content would read the entire data in-memory.
      stream = io.BytesIO(response.content)
    else:
      stream = response.raw
    self._response_handler.handle(stream)

  def request(
      self,
      uri,
      method='GET',
      body=None,
      headers=None,
      redirections=0,
      connection_type=None,
  ):  # pylint: disable=invalid-name
    """Makes an HTTP request using httplib2 semantics."""
    del connection_type  # Unused

    if redirections > 0:
      self.session.max_redirects = redirections

    hooks = {}
    if self._response_handler is not None:
      hooks['response'] = self.ResponseHook
      use_stream = self._response_handler.use_stream
    else:
      use_stream = False

    response = self.session.request(
        method, uri, data=body, headers=headers, stream=use_stream, hooks=hooks)
    headers = dict(response.headers)
    headers['status'] = response.status_code

    if use_stream:
      # If use_stream is True, we assume that the data will be read from the
      # response_handler
      content = b''
    elif self._response_encoding is not None:
      # We update response.encoding before calling response.text because
      # response.text property will try to make an educated guess about the
      # encoding based on the response header, which might be different from
      # the self._response_encoding set by the caller.
      response.encoding = self._response_encoding
      content = response.text
    else:
      content = response.content

    return httplib2.Response(headers), content


def _HasInvalidHttpsProxyEnvVarScheme():
  """Returns whether the HTTPS proxy env var is using an HTTPS scheme."""
  # We call urllib.getproxies_environment instead of checking os.environ
  # ourselves to ensure we match the semantics of what the requests library ends
  # up doing.
  env_proxies = urllib_request.getproxies_environment()
  return env_proxies.get('https', '').startswith('https://')


def _HasBpo42627():
  """Returns whether Python is affected by https://bugs.python.org/issue42627.

  Due to a bug in Python's standard library, urllib.request misparses the
  Windows registry proxy settings and assumes that HTTPS URLs should use an
  HTTPS proxy, when in fact they should use an HTTP proxy.

  This bug affects PY<3.9, as well as lower patch versions of 3.9, 3.10, and
  3.11.

  Returns:
    True if proxies read from the Windows registry are being parsed incorrectly.
  """
  return (
      platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS
      and hasattr(urllib_request, 'getproxies_registry')
      and urllib_request.getproxies_registry().get('https', '').startswith(
          'https://')
  )


def _AdjustProxiesKwargForBpo42627(
    gcloud_proxy_info, environment_proxies,
    orig_request_method, *args, **kwargs):
  """Returns proxies to workaround https://bugs.python.org/issue42627 if needed.

  Args:
    gcloud_proxy_info: str, Proxy info from gcloud properties.
    environment_proxies: dict, Proxy config from http/https_proxy env vars.
    orig_request_method: function, The original requests.Session.request method.
    *args: Positional arguments to the original request method.
    **kwargs: Keyword arguments to the original request method.
  Returns:
    Optional[dict], Adjusted proxies to pass to the request method, or None if
      no adjustment is necessary.
  """
  # Proxy precedence:
  #   gcloud properties > http/https/no_proxy env vars > registry settings
  # So if proxy settings come from either of the first two, then there's no need
  # to adjust anything.
  if gcloud_proxy_info or environment_proxies:
    return None

  # We want to correct proxies incorrectly parsed from the registry by sending a
  # tweaked 'proxies' kwarg to the requests.Session.request method. However,
  # proxies passed in this manner apply unconditionally, and we still wish to
  # respect the "ProxyOverride" settings from the registry. So we extract the
  # URL passed to the method, and only pass a corrected HTTPS proxy if requests
  # would end up using the proxy for that URL when taking "ProxyOverride"
  # settings into account.
  url = inspect.getcallargs(orig_request_method, *args, **kwargs)['url']  # pylint: disable=deprecated-method, for PY2 compatibility
  proxies = requests.utils.get_environ_proxies(url)  # Respects ProxyOverride.
  https_proxy = proxies.get('https')
  if not https_proxy:
    return None

  if not https_proxy.startswith('https://'):
    # This should theoretically never happen, since
    # requests.utils.get_environ_proxies should have returned proxies from the
    # registry if we got here, and those will have been bugged. But just in case
    # some implementation detail changes, don't try to adjust anything.
    return None

  return {
      'https': https_proxy.replace('https://', 'http://', 1)
  }
