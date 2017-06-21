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


import copy
import platform
import time
import urllib
import urlparse
import uuid

from googlecloudsdk.core import config
from googlecloudsdk.core import http_proxy
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
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

  # Wrap the request method to put in our own user-agent, and trace reporting.
  gcloud_ua = MakeUserAgentString(properties.VALUES.metrics.command_name.Get())
  http_client = _Wrap(
      http_client,
      properties.VALUES.core.trace_token.Get(),
      properties.VALUES.core.trace_email.Get(),
      properties.VALUES.core.trace_log.GetBool(),
      gcloud_ua,
      properties.VALUES.core.log_http.GetBool()
  )

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


def _Wrap(
    http_client, trace_token, trace_email, trace_log, gcloud_ua, log_http):
  """Wrap request with user-agent, and trace reporting.

  Args:
    http_client: The original http object.
    trace_token: str, Token to be used to route service request traces.
    trace_email: str, username to which service request traces should be sent.
    trace_log: bool, Enable/diable server side logging of service requests.
    gcloud_ua: str, User agent string to be included in the request.
    log_http: bool, True to enable request/response logging.

  Returns:
    http, The same http object but with the request method wrapped.
  """
  handlers = []

  handlers.append(Modifiers.Handler(
      Modifiers.RecordStartTime(),
      Modifiers.ReportDuration()))

  handlers.append(Modifiers.Handler(
      Modifiers.AppendToHeader('user-agent', gcloud_ua)))

  trace_value = None
  if trace_token:
    trace_value = 'token:{0}'.format(trace_token)
  elif trace_email:
    trace_value = 'email:{0}'.format(trace_email)
  elif trace_log:
    trace_value = 'log'

  if trace_value:
    handlers.append(Modifiers.Handler(
        Modifiers.AddQueryParam('trace', trace_value)))

  # Do this one last so that it sees the affects of the other modifiers.
  if log_http:
    handlers.append(Modifiers.Handler(
        Modifiers.LogRequest(),
        Modifiers.LogResponse()))

  return Modifiers.WrapRequest(http_client, handlers)


class Modifiers(object):
  """Encapsulates a bunch of http request wrapping functionality.

  The general process is that you can define a series of handlers that get
  executed before and after the original http request you are mapping. All the
  request handlers are executed in the order provided. Request handlers must
  return a result that is used when invoking the corresponding response handler.
  Request handlers don't actually execute the request but rather just modify the
  request arguments. After all request handlers are executed, the original http
  request is executed. Finally, all response handlers are executed in order,
  getting passed both the http response as well as the result from their
  corresponding request handler.
  """

  class Handler(object):
    """A holder object for a pair of request and response handlers.

    Request handlers are invoked before the original http request, response
    handlers are invoked after.
    """

    def __init__(self, request, response=None):
      """Creates a new Handler.

      Args:
        request: f(args, kwargs) -> Result, A function that gets called before
          the original http request gets called. It has the same arguments as
          http.request(). It returns a Modifiers.Result object that contains
          data to be passed to later stages of execution.
        response: f(response, Modifiers.Result.data), A function that gets
          called after the original http request. It is passed the http response
          as well as whatever the request handler put in its Result object.
      """
      self.request = request
      self.response = response

  class Result(object):
    """A holder object for data a request modifier needs to return.

    Data from the Result object is later passed into the response handler after
    the original http request is executed.
    """

    def __init__(self, args=None, data=None):
      """Creates a new Result.

      Args:
        args: A modified version of the http request args passed into the
          request modifier (if they need to be changed). This is required
          because the args are a tuple and cannot be modified in place like the
          kwargs can.
        data: Anything the request modifier wants to save for later use in a
          response handler.
      """
      self.args = args
      self.data = data

  @classmethod
  def WrapRequest(cls, http_client, handlers,
                  exc_handler=None, exc_type=Exception):
    """Wraps an http client with request modifiers.

    Args:
      http_client: The original http client to be wrapped.
      handlers: [Modifiers.Handler], The handlers to execute before and after
        the original request.
      exc_handler: f(e), A function that takes an exception and handles it. It
        should also throw an exception if you don't want it to be swallowed.
      exc_type: The type of exception that should be caught and given to the
        handler.

    Returns:
      The wrapped http client.
    """
    orig_request = http_client.request

    def WrappedRequest(*args, **kwargs):
      """Replacement http.request() method."""
      modified_args = args
      # We need to make a copy here because if we don't we will be modifying the
      # dictionary that people pass in.
      # TODO(b/37281703): Copy the entire dictionary. This is blocked on making
      # sure anything that comes through is actually copyable.
      if 'headers' in kwargs:
        kwargs['headers'] = copy.copy(kwargs['headers'])
      modifier_data = []

      for handler in handlers:
        modifier_result = handler.request(modified_args, kwargs)
        if modifier_result.args:
          modified_args = modifier_result.args
        modifier_data.append(modifier_result.data)

      try:
        response = orig_request(*modified_args, **kwargs)
      except exc_type as e:  # pylint: disable=broad-except
        response = None
        if exc_handler:
          exc_handler(e)
        else:
          raise

      for handler, data in zip(handlers, modifier_data):
        if handler.response:
          handler.response(response, data)

      return response

    http_client.request = WrappedRequest

    # apitools needs this attribute to do credential refreshes during batch API
    # requests.
    if hasattr(orig_request, 'credentials'):
      setattr(http_client.request, 'credentials', orig_request.credentials)

    return http_client

  @classmethod
  def AppendToHeader(cls, header, value):
    """Appends the given value to the existing value in the http request.

    Args:
      header: str, The name of the header to append to.
      value: str, The value to append to the existing header value.

    Returns:
      A function that can be used in a Handler.request.
    """
    def _AppendToHeader(args, kwargs):
      """Replacement http.request() method."""
      current_value = Modifiers._GetHeader(args, kwargs, header, '')
      new_value = '{0} {1}'.format(current_value, value).strip()
      modified_args = Modifiers._SetHeader(args, kwargs, header, new_value)
      return Modifiers.Result(args=modified_args)
    return _AppendToHeader

  @classmethod
  def SetHeader(cls, header, value):
    """Sets the given header value in the http request.

    Args:
      header: str, The name of the header to set to.
      value: str, The new value of the header.

    Returns:
      A function that can be used in a Handler.request.
    """
    def _SetHeader(args, kwargs):
      """Replacement http.request() method."""
      modified_args = Modifiers._SetHeader(args, kwargs, header, value)
      return Modifiers.Result(args=modified_args)
    return _SetHeader

  @classmethod
  def AddQueryParam(cls, param, value):
    """Adds the given query parameter to the http request.

    Args:
      param: str, The name of the parameter.
      value: str, The value of the parameter.

    Returns:
      A function that can be used in a Handler.request.
    """
    def _AddQueryParam(args, unused_kwargs):
      """Replacement http.request() method."""
      url_parts = urlparse.urlsplit(args[0])
      query_params = urlparse.parse_qs(url_parts.query)
      query_params[param] = value
      # Need to do this to convert a SplitResult into a list so it can be
      # modified.
      url_parts = list(url_parts)
      url_parts[3] = urllib.urlencode(query_params, doseq=True)
      modified_args = list(args)
      modified_args[0] = urlparse.urlunsplit(url_parts)
      return Modifiers.Result(args=modified_args)
    return _AddQueryParam

  @classmethod
  def LogRequest(cls):
    """Logs the contents of the http request.

    Returns:
      A function that can be used in a Handler.request.
    """
    def _LogRequest(args, kwargs):
      """Replacement http.request() method."""
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

      return Modifiers.Result(data=time.time())
    return _LogRequest

  @classmethod
  def LogResponse(cls):
    """Logs the contents of the http response.

    Returns:
      A function that can be used in a Handler.response.
    """
    def _LogResponse(response, start_time):
      """Response handler."""
      time_taken = time.time() - start_time
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
    return _LogResponse

  @classmethod
  def RecordStartTime(cls):
    """Records the time at which the request was started.

    Returns:
      A function that can be used in a Handler.request.
    """
    def _RecordStartTime(unused_args, unused_kwargs):
      """Replacement http.request() method."""
      return Modifiers.Result(data=time.time())
    return _RecordStartTime

  @classmethod
  def ReportDuration(cls):
    """Reports the duration of response to the metrics module.

    Returns:
      A function that can be used in a Handler.response.
    """
    def _ReportDuration(unused_response, start_time):
      """Response handler."""
      duration = time.time() - start_time
      metrics.RPCDuration(duration)

    return _ReportDuration

  @classmethod
  def _GetHeader(cls, args, kwargs, header, default=None):
    """Get a header given the args and kwargs of an Http Request call."""

    if 'headers' in kwargs:
      return kwargs['headers'].get(header, default)
    elif len(args) > 3 and args[3]:
      return args[3].get(header, default)
    else:
      return default

  @classmethod
  def _SetHeader(cls, args, kwargs, header, value):
    """Set a header given the args and kwargs of an Http Request call."""

    modified_args = list(args)

    if 'headers' in kwargs:
      # Headers was given to request() as a kwarg, we can just update it.
      kwargs['headers'][header] = value
    elif len(modified_args) > 3:
      # Headers was given as a positional, we need to update that arg.
      if modified_args[3] is not None:
        # Headers were actually provided, update that dictionary.
        modified_args[3][header] = value
      else:
        # Headers were explicitly provided as a positional but None, copy the
        # args because the tuple is immutable and insert the header.
        modified_args[3] = {header: value}
    else:
      kwargs['headers'] = {header: value}

    return modified_args
