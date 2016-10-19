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

"""A module to get an unauthenticated http object."""


import platform
import time
import urllib
import urlparse
import uuid

from googlecloudsdk.core import config
from googlecloudsdk.core import http_proxy
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import platforms
import httplib2


def Http(timeout='unset'):
  """Get an httplib2.Http client that is properly configured for use by gcloud.

  This method does not add credentials to the client.  For an Http client that
  has been authenticated, use core.credentials.http.Http().

  Args:
    timeout: double, The timeout in seconds to pass to httplib2.  This is the
        socket level timeout.  If timeout is None, timeout is infinite.  If
        default argument 'unset' is given, a sensible default is selected.

  Returns:
    An httplib2.Http client object configured with all the required settings
    for gcloud.
  """
  # Compared with setting the default timeout in the function signature (i.e.
  # timeout=300), this lets you test with short default timeouts by mocking
  # GetDefaultTimeout.
  effective_timeout = timeout if timeout != 'unset' else GetDefaultTimeout()
  no_validate = properties.VALUES.auth.disable_ssl_validation.GetBool()
  ca_certs = properties.VALUES.core.custom_ca_certs_file.Get()
  http_client = httplib2.Http(timeout=effective_timeout,
                              proxy_info=http_proxy.GetHttpProxyInfo(),
                              ca_certs=ca_certs,
                              disable_ssl_certificate_validation=no_validate)

  # Wrap first to dump any data added by other wrappers.
  if properties.VALUES.core.log_http.GetBool():
    http_client = _WrapRequestForLogging(http_client)

  # Wrap the request method to put in our own user-agent, and trace reporting.
  gcloud_ua = MakeUserAgentString(properties.VALUES.metrics.command_name.Get())

  http_client = _WrapRequestForUserAgentAndTracing(
      http_client,
      properties.VALUES.core.trace_token.Get(),
      properties.VALUES.core.trace_email.Get(),
      properties.VALUES.core.trace_log.GetBool(),
      gcloud_ua)

  return http_client


def MakeUserAgentString(cmd_path=None):
  """Return a user-agent string for this request.

  Contains 'gcloud' in addition to several other product IDs used for tracing in
  metrics reporting.

  Args:
    cmd_path: str representing the current command for tracing.

  Returns:
    str, User Agent string.
  """
  return ('gcloud/{0}'
          ' command/{1}'
          ' invocation-id/{2}'
          ' environment/{3}'
          ' environment-version/{4}'
          ' interactive/{5}'
          ' python/{6}'
          ' {7}').format(
              config.CLOUD_SDK_VERSION.replace(' ', '_'),
              cmd_path or properties.VALUES.metrics.command_name.Get(),
              uuid.uuid4().hex,
              properties.GetMetricsEnvironment(),
              properties.VALUES.metrics.environment_version.Get(),
              console_io.IsInteractive(error=True, heuristic=True),
              platform.python_version(),
              platforms.Platform.Current().UserAgentFragment())


def GetDefaultTimeout():
  return properties.VALUES.core.http_timeout.GetInt() or 300


def RequestArgsGetHeader(args, kwargs, header, default=None):
  """Get a specific header given the args and kwargs of an Http Request call."""
  if 'headers' in kwargs:
    return kwargs['headers'].get(header, default)
  elif len(args) > 3:
    return args[3].get(header, default)
  else:
    return default


def RequestArgsSetHeader(args, kwargs, header, value):
  """Set a specific header given the args and kwargs of an Http Request call."""
  if 'headers' in kwargs:
    kwargs['headers'][header] = value
  elif len(args) > 3:
    args[3][header] = value
  else:
    kwargs['headers'] = {header: value}


# TODO(b/25115137): Refactor the wrapper functions to be more clear.
def _WrapRequestForUserAgentAndTracing(http_client, trace_token,
                                       trace_email,
                                       trace_log,
                                       gcloud_ua):
  """Wrap request with user-agent, and trace reporting.

  Args:
    http_client: The original http object.
    trace_token: str, Token to be used to route service request traces.
    trace_email: str, username to which service request traces should be sent.
    trace_log: bool, Enable/diable server side logging of service requests.
    gcloud_ua: str, User agent string to be included in the request.

  Returns:
    http, The same http object but with the request method wrapped.
  """
  orig_request = http_client.request

  def RequestWithUserAgentAndTracing(*args, **kwargs):
    """Wrap request with user-agent, and trace reporting.

    Args:
      *args: Positional arguments.
      **kwargs: Keyword arguments.

    Returns:
      Wrapped request method with user-agent and trace reporting.
    """
    modified_args = list(args)

    # Use gcloud specific user-agent with command path and invocation-id.
    # Pass in the user-agent through kwargs or args.
    def UserAgent(current=''):
      user_agent = '{0} {1}'.format(current, gcloud_ua)
      return user_agent.strip()
    cur_ua = RequestArgsGetHeader(modified_args, kwargs, 'user-agent', '')
    RequestArgsSetHeader(modified_args, kwargs,
                         'user-agent', UserAgent(cur_ua))

    # Modify request url to enable requested tracing.
    url_parts = urlparse.urlsplit(args[0])
    query_params = urlparse.parse_qs(url_parts.query)
    if trace_token:
      query_params['trace'] = 'token:{0}'.format(trace_token)
    elif trace_email:
      query_params['trace'] = 'email:{0}'.format(trace_email)
    elif trace_log:
      query_params['trace'] = 'log'

    # Replace the request url in the args
    modified_url_parts = list(url_parts)
    modified_url_parts[3] = urllib.urlencode(query_params, doseq=True)
    modified_args[0] = urlparse.urlunsplit(modified_url_parts)

    return orig_request(*modified_args, **kwargs)

  http_client.request = RequestWithUserAgentAndTracing

  # apitools needs this attribute to do credential refreshes during batch API
  # requests.
  if hasattr(orig_request, 'credentials'):
    setattr(http_client.request, 'credentials', orig_request.credentials)

  return http_client


# TODO(b/25115137): Refactor the wrapper functions to be more clear.
def _WrapRequestForLogging(http_client):
  """Wrap request for capturing and logging of http request/response data.

  Args:
    http_client: httplib2.Http, The original http object.

  Returns:
    http, The same http object but with the request method wrapped.
  """

  orig_request = http_client.request

  def RequestWithLogging(*args, **kwargs):
    """Wrap request for request/response logging.

    Args:
      *args: Positional arguments.
      **kwargs: Keyword arguments.

    Returns:
      Original returned response of this wrapped request.
    """
    _LogRequest(*args, **kwargs)
    time_start = time.time()
    response = orig_request(*args, **kwargs)
    _LogResponse(response, time.time() - time_start)
    return response

  http_client.request = RequestWithLogging

  # apitools needs this attribute to do credential refreshes during batch API
  # requests.
  if hasattr(orig_request, 'credentials'):
    setattr(http_client.request, 'credentials', orig_request.credentials)

  return http_client


def _LogRequest(*args, **kwargs):
  """Logs request arguments."""

  # http.request has the following signature:
  # request(self, uri, method="GET", body=None, headers=None,
  #         redirections=DEFAULT_MAX_REDIRECTS, connection_type=None)
  uri = args[0]
  method = 'GET'
  body = ''
  headers = {}

  if len(args) > 1:
    method = args[1]
  elif 'method' in kwargs:
    method = kwargs['method']
  if len(args) > 2:
    body = args[2]
    if len(args) > 3:
      headers = args[3]
  if 'body' in kwargs:
    body = kwargs['body']
  if 'headers' in kwargs:
    headers = kwargs['headers']

  log.status.Print('=======================')
  log.status.Print('==== request start ====')
  log.status.Print('uri: {uri}'.format(uri=uri))
  log.status.Print('method: {method}'.format(method=method))
  log.status.Print('== headers start ==')
  for h, v in sorted(headers.iteritems()):
    log.status.Print('{0}: {1}'.format(h, v))
  log.status.Print('== headers end ==')
  log.status.Print('== body start ==')
  log.status.Print(body)
  log.status.Print('== body end ==')
  log.status.Print('==== request end ====')


def _LogResponse(response, time_taken):
  """Logs response headers and content."""

  headers, content = response
  log.status.Print('---- response start ----')
  log.status.Print('-- headers start --')
  for h, v in sorted(headers.iteritems()):
    log.status.Print('{0}: {1}'.format(h, v))
  log.status.Print('-- headers end --')
  log.status.Print('-- body start --')
  log.status.Print(content)
  log.status.Print('-- body end --')
  log.status.Print('total round trip time (request+response): {0:.3f} secs'
                   .format(time_taken))
  log.status.Print('---- response end ----')
  log.status.Print('----------------------')
