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
"""Module for common transport utilities, such as request wrapping."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import platform
import re
import uuid

from googlecloudsdk.core import config
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.console import console_io

from googlecloudsdk.core.util import platforms

import six
from six.moves import zip  # pylint: disable=redefined-builtin

# Alternative spellings of User-Agent header key that may appear in requests.
_NORMALIZED_USER_AGENT = b'user-agent'

ENCODING = None if six.PY2 else 'utf8'

TOKEN_URIS = [
    'https://accounts.google.com/o/oauth2/token',
    'https://www.googleapis.com/oauth2/v3/token',
    'https://www.googleapis.com/oauth2/v4/token',
    'https://oauth2.googleapis.com/token',
    'https://oauth2.googleapis.com/oauth2/v4/token'
]


class Request(six.with_metaclass(abc.ABCMeta, object)):
  """Encapsulates parameters for making a general HTTP request.

  Attributes:
    uri: URI of the HTTP resource.
    method: HTTP method to perform, such as GET, POST, DELETE, etc.
    headers: Additional headers to include in the request.
    body: Body of the request.
  """

  def __init__(self, uri, method, headers, body):
    """Instantiates a Request object.

    Args:
      uri: URI of the HTTP resource.
      method: HTTP method to perform, such as GET, POST, DELETE, etc.
      headers: Additional headers to include in the request.
      body: Body of the request.

    Returns:
      Request
    """
    self.uri = uri
    self.method = method
    self.headers = headers
    self.body = body

  @classmethod
  @abc.abstractmethod
  def FromRequestArgs(cls, *args, **kwargs):
    """Returns a Request object.

    Args:
      *args: args to be passed into http.request
      **kwargs: dictionary of kwargs to be passed into http.request

    Returns:
      Request
    """

  @abc.abstractmethod
  def ToRequestArgs(self):
    """Returns the args and kwargs to be used when calling http.request."""


class Response(six.with_metaclass(abc.ABCMeta, object)):
  """Encapsulates responses from making a general HTTP request.

  Attributes:
    status_code:
    headers: Headers of the response.
    body: Body of the response.
  """

  def __init__(self, status_code, headers, body):
    """Instantiates a Response object.

    Args:
      status_code:
      headers: Headers of the response.
      body: Body of the response.

    Returns:
      Response
    """
    self.status_code = status_code
    self.headers = headers
    self.body = body

  @classmethod
  @abc.abstractmethod
  def FromResponse(cls, response):
    """Returns a Response object.

    Args:
      response: raw response from calling http.request.

    Returns:
      Response
    """


class RequestWrapper(six.with_metaclass(abc.ABCMeta, object)):
  """Class for wrapping http requests.

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
  request_class = Request
  response_class = Response

  @abc.abstractmethod
  def DecodeResponse(self, response, response_encoding):
    """Decodes the response body according to response_encoding."""

  @abc.abstractmethod
  def AttachCredentials(self, http_client, orig_request):
    """Attaches credentials to the wrapped http_client.request.

    apitools needs this attribute to do credential refreshes during batch API
    requests by calling `http.request.credentials.refresh(http)`.

    Args:
      http_client: The http client with a wrapped request method.
      orig_request: The original unwrapped request method.
    """

  def WrapRequest(self,
                  http_client,
                  handlers,
                  exc_handler=None,
                  exc_type=Exception,
                  response_encoding=None):
    """Wraps an http client with request modifiers.

    Args:
      http_client: The original http client to be wrapped.
      handlers: [Handler], The handlers to execute before and after the original
        request.
      exc_handler: f(e), A function that takes an exception and handles it. It
        should also throw an exception if you don't want it to be swallowed.
      exc_type: The type of exception that should be caught and given to the
        handler.
      response_encoding: str, the encoding to use to decode the response.

    Returns:
      The wrapped http client.
    """
    orig_request = http_client.request

    def WrappedRequest(*args, **kwargs):
      """Replacement http_client.request() method."""
      handler_request = self.request_class.FromRequestArgs(*args, **kwargs)

      # Encode request headers
      headers = {h: v for h, v in six.iteritems(handler_request.headers)}
      handler_request.headers = {}
      for h, v in six.iteritems(headers):
        h, v = _EncodeHeader(h, v)
        handler_request.headers[h] = v

      modifier_data = []
      for handler in handlers:
        modifier_result = handler.request(handler_request)
        modifier_data.append(modifier_result)

      try:
        modified_args, modified_kwargs = handler_request.ToRequestArgs()
        response = orig_request(*modified_args, **modified_kwargs)
      except exc_type as e:  # pylint: disable=broad-except
        response = None
        if exc_handler:
          exc_handler(e)
          return
        else:
          raise

      if response_encoding is not None:
        response = self.DecodeResponse(response, response_encoding)

      handler_response = self.response_class.FromResponse(response)
      for handler, data in zip(handlers, modifier_data):
        if handler.response:
          handler.response(handler_response, data)

      return response

    http_client.request = WrappedRequest

    # Attach credentials on the request to do credential refreshes
    # during apitools batch API requests.
    self.AttachCredentials(http_client, orig_request)
    return http_client


class Handler(object):
  """A holder object for a pair of request and response handlers.

  Request handlers are invoked before the original http request, response
  handlers are invoked after.
  """

  def __init__(self, request, response=None):
    """Creates a new Handler.

    Args:
      request: f(request) -> data, A function that gets called before the
        original http request gets called. It is passed a Request object that
        encapsulates the parameters of an http request. It returns data to be
        passed to its corresponding response hander.
      response: f(response, data), A function that gets called after the
        original http request. It is passed a Response object that encapsulates
        the response of an http request as well as whatever the request handler
        returned as data.
    """
    self.request = request
    self.response = response


def _EncodeHeader(header, value):
  if isinstance(header, six.text_type):
    header = header.encode('utf8')
  if isinstance(value, six.text_type):
    value = value.encode('utf8')
  return header, value


def MakeUserAgentString(cmd_path=None):
  """Return a user-agent string for this request.

  Contains 'gcloud' in addition to several other product IDs used for tracing in
  metrics reporting.

  Args:
    cmd_path: str representing the current command for tracing.

  Returns:
    str, User Agent string.
  """
  return ('gcloud/{version}'
          ' command/{cmd}'
          ' invocation-id/{inv_id}'
          ' environment/{environment}'
          ' environment-version/{env_version}'
          ' interactive/{is_interactive}'
          ' from-script/{from_script}'
          ' python/{py_version}'
          ' term/{term}'
          ' {ua_fragment}').format(
              version=config.CLOUD_SDK_VERSION.replace(' ', '_'),
              cmd=(cmd_path or properties.VALUES.metrics.command_name.Get()),
              inv_id=uuid.uuid4().hex,
              environment=properties.GetMetricsEnvironment(),
              env_version=properties.VALUES.metrics.environment_version.Get(),
              is_interactive=console_io.IsInteractive(
                  error=True, heuristic=True),
              py_version=platform.python_version(),
              ua_fragment=platforms.Platform.Current().UserAgentFragment(),
              from_script=console_io.IsRunFromShellScript(),
              term=console_attr.GetConsoleAttr().GetTermIdentifier())


def GetDefaultTimeout():
  return properties.VALUES.core.http_timeout.GetInt() or 300


def GetTraceValue():
  """Return a value to be used for the trace header."""
  # Token to be used to route service request traces.
  trace_token = properties.VALUES.core.trace_token.Get()
  # Username to which service request traces should be sent.
  trace_email = properties.VALUES.core.trace_email.Get()
  # Enable/disable server side logging of service requests.
  trace_log = properties.VALUES.core.trace_log.GetBool()

  if trace_token:
    return 'token:{0}'.format(trace_token)
  elif trace_email:
    return 'email:{0}'.format(trace_email)
  elif trace_log:
    return 'log'
  return None


def IsTokenUri(uri):
  """Determine if the given URI is for requesting an access token."""
  if uri in TOKEN_URIS:
    return True

  metadata_regexp = ('metadata.google.internal/computeMetadata/.*?/instance/'
                     'service-accounts/.*?/token')

  return re.search(metadata_regexp, uri) is not None
