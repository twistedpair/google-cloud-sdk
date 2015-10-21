# Copyright 2013 Google Inc. All Rights Reserved.

"""A module to make it easy to set up and run CLIs in the Cloud SDK."""

import platform
import time
import urllib
import urlparse
import uuid

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.credentials import store as c_store
from googlecloudsdk.core.util import platforms
from oauth2client import client


__all__ = ['Http']


class Error(exceptions.Error):
  """Exceptions for the cli module."""


class CannotRefreshAuthTokenError(Error, client.AccessTokenRefreshError):
  """An exception raised when the auth tokens fail to refresh."""

  def __init__(self, msg):
    auth_command = '$ gcloud auth login'
    message = ('There was a problem refreshing your current auth tokens: '
               '{0}.  Please run\n  {1}.'.format(msg, auth_command))
    super(CannotRefreshAuthTokenError, self).__init__(message)


def MakeUserAgentString(cmd_path):
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
          ' interactive/{4}'
          ' python/{5}'
          ' {6}').format(
              config.CLOUD_SDK_VERSION,
              cmd_path,
              uuid.uuid4().hex,
              properties.GetMetricsEnvironment(),
              console_io.IsInteractive(error=True, heuristic=True),
              platform.python_version(),
              platforms.Platform.Current().UserAgentFragment())


def GetDefaultTimeout():
  return 300


def Http(cmd_path=None, trace_token=None,
         trace_email=None,
         trace_log=False,
         auth=True, creds=None, timeout='unset', log_http=False):
  """Get an httplib2.Http object for working with the Google API.

  Args:
    cmd_path: str, Path of command that will use the httplib2.Http object.
    trace_token: str, Token to be used to route service request traces.
    trace_email: str, username to which service request traces should be sent.
    trace_log: bool, Enable/disable server side logging of service requests.
    auth: bool, True if the http object returned should be authorized.
    creds: oauth2client.client.Credentials, If auth is True and creds is not
        None, use those credentials to authorize the httplib2.Http object.
    timeout: double, The timeout in seconds to pass to httplib2.  This is the
        socket level timeout.  If timeout is None, timeout is infinite.  If
        default argument 'unset' is given, a sensible default is selected.
    log_http: bool, Enable/disable client side logging of service requests.

  Returns:
    An authorized httplib2.Http object, or a regular httplib2.Http object if no
    credentials are available.

  Raises:
    c_store.Error: If an error loading the credentials occurs.
  """

  # Compared with setting the default timeout in the function signature (i.e.
  # timeout=300), this lets you test with short default timeouts by mocking
  # GetDefaultTimeout.
  effective_timeout = timeout if timeout != 'unset' else GetDefaultTimeout()

  # TODO(jasmuth): Have retry-once-if-denied logic, to allow client tools to not
  # worry about refreshing credentials.

  http = c_store._Http(  # pylint:disable=protected-access
      timeout=effective_timeout)

  # Wrap first to dump any data added by other wrappers.
  if log_http:
    http = _WrapRequestForLogging(http)

  # Wrap the request method to put in our own user-agent, and trace reporting.
  gcloud_ua = MakeUserAgentString(cmd_path)

  http = _WrapRequestForUserAgentAndTracing(http, trace_token,
                                            trace_email,
                                            trace_log,
                                            gcloud_ua)
  if auth:
    if not creds:
      creds = c_store.Load()
    http = creds.authorize(http)
    # Wrap the request method to put in our own error handling.
    http = _WrapRequestForAuthErrHandling(http)
  return http


def _WrapRequestForUserAgentAndTracing(http, trace_token,
                                       trace_email,
                                       trace_log,
                                       gcloud_ua):
  """Wrap request with user-agent, and trace reporting.

  Args:
    http: The original http object.
    trace_token: str, Token to be used to route service request traces.
    trace_email: str, username to which service request traces should be sent.
    trace_log: bool, Enable/diable server side logging of service requests.
    gcloud_ua: str, User agent string to be included in the request.

  Returns:
    http, The same http object but with the request method wrapped.
  """
  orig_request = http.request

  # TODO(vilasj): Use @functools.wraps, and then remove credentials attr check.
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
    if 'headers' in kwargs:
      cur_ua = kwargs['headers'].get('user-agent', '')
      kwargs['headers']['user-agent'] = UserAgent(cur_ua)
    elif len(args) > 3:
      cur_ua = modified_args[3].get('user-agent', '')
      modified_args[3]['user-agent'] = UserAgent(cur_ua)
    else:
      kwargs['headers'] = {'user-agent': UserAgent()}

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

  http.request = RequestWithUserAgentAndTracing

  # apitools needs this attribute to do credential refreshes during batch API
  # requests.
  if hasattr(orig_request, 'credentials'):
    setattr(http.request, 'credentials', orig_request.credentials)

  return http


def _WrapRequestForAuthErrHandling(http):
  """Wrap request with exception handling for auth.

  We need to wrap exception handling because oauth2client does similar wrapping
  when you authorize the http object.  Because of this, a credential refresh
  error can get raised wherever someone makes an http request.  With no common
  place to handle this exception, we do more wrapping here so we can convert it
  to one of our typed exceptions.

  Args:
    http: The original http object.

  Returns:
    http, The same http object but with the request method wrapped.
  """
  orig_request = http.request

  # TODO(vilasj): Use @functools.wraps, and then remove credentials attr check.
  def RequestWithErrHandling(*args, **kwargs):
    try:
      return orig_request(*args, **kwargs)
    except client.AccessTokenRefreshError as e:
      log.debug('Exception caught during HTTP request: %s', e.message,
                exc_info=True)
      raise CannotRefreshAuthTokenError(e.message)

  http.request = RequestWithErrHandling

  # apitools needs this attribute to do credential refreshes during batch API
  # requests.
  if hasattr(orig_request, 'credentials'):
    setattr(http.request, 'credentials', orig_request.credentials)

  return http


def _WrapRequestForLogging(http):
  """Wrap request for capturing and logging of http request/response data.

  Args:
    http: httplib2.Http, The original http object.

  Returns:
    http, The same http object but with the request method wrapped.
  """

  orig_request = http.request

  # TODO(vilasj): Use @functools.wraps, and then remove credentials attr check.
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

  http.request = RequestWithLogging

  # apitools needs this attribute to do credential refreshes during batch API
  # requests.
  if hasattr(orig_request, 'credentials'):
    setattr(http.request, 'credentials', orig_request.credentials)

  return http


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

  log.status.Print('--request-start--')
  log.status.Print('uri: {uri}'.format(uri=uri))
  log.status.Print('method: {method}'.format(method=method))
  log.status.Print('-headers-start-')
  for h, v in sorted(headers.iteritems()):
    log.status.Print('{0}: {1}'.format(h, v))
  log.status.Print('-headers-end-')
  log.status.Print('-body-start-')
  log.status.Print(body)
  log.status.Print('-body-end-')
  log.status.Print('--request-end--')


def _LogResponse(response, time_taken):
  """Logs response headers and content."""

  headers, content = response
  log.status.Print('--response-start--')
  log.status.Print('-headers-start-')
  for h, v in sorted(headers.iteritems()):
    log.status.Print('{0}: {1}'.format(h, v))
  log.status.Print('-headers-end-')
  log.status.Print('-body-start-')
  log.status.Print(content)
  log.status.Print('-body-end-')
  log.status.Print('total latency (request+response): {0:.3f} secs'
                   .format(time_taken))
  log.status.Print('--response-end--')
