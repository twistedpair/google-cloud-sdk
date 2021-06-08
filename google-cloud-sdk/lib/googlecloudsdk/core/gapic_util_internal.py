# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Internal Helper Classes for creating gapic clients in gcloud."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import os
import time

from googlecloudsdk.core import context_aware
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import encoding
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import http_proxy_types

import grpc
from six.moves import urllib
import socks


class Error(exceptions.Error):
  """Exceptions for the gapic module."""


class ClientCallDetailsInterceptor(grpc.UnaryUnaryClientInterceptor,
                                   grpc.UnaryStreamClientInterceptor,
                                   grpc.StreamUnaryClientInterceptor,
                                   grpc.StreamStreamClientInterceptor):
  """Generic Client Interceptor that modifies the ClientCallDetails."""

  def __init__(self, fn):
    self._fn = fn

  def intercept_call(self, continuation, client_call_details, request):
    """Intercepts a RPC.

    Args:
      continuation: A function that proceeds with the invocation by
        executing the next interceptor in chain or invoking the
        actual RPC on the underlying Channel. It is the interceptor's
        responsibility to call it if it decides to move the RPC forward.
        The interceptor can use
        `response_future = continuation(client_call_details, request)`
        to continue with the RPC.
      client_call_details: A ClientCallDetails object describing the
        outgoing RPC.
      request: The request value for the RPC.

    Returns:
        If the response is unary:
          An object that is both a Call for the RPC and a Future.
          In the event of RPC completion, the return Call-Future's
          result value will be the response message of the RPC.
          Should the event terminate with non-OK status, the returned
          Call-Future's exception value will be an RpcError.

        If the response is streaming:
          An object that is both a Call for the RPC and an iterator of
          response values. Drawing response values from the returned
          Call-iterator may raise RpcError indicating termination of
          the RPC with non-OK status.
    """
    new_details = self._fn(client_call_details)
    return continuation(new_details, request)

  def intercept_unary_unary(self, continuation, client_call_details, request):
    """Intercepts a unary-unary invocation asynchronously."""
    return self.intercept_call(continuation, client_call_details, request)

  def intercept_unary_stream(self, continuation, client_call_details,
                             request):
    """Intercepts a unary-stream invocation."""
    return self.intercept_call(continuation, client_call_details, request)

  def intercept_stream_unary(self, continuation, client_call_details,
                             request_iterator):
    """Intercepts a stream-unary invocation asynchronously."""
    return self.intercept_call(continuation, client_call_details,
                               request_iterator)

  def intercept_stream_stream(self, continuation, client_call_details,
                              request_iterator):
    """Intercepts a stream-stream invocation."""
    return self.intercept_call(continuation, client_call_details,
                               request_iterator)


class _ClientCallDetails(
        collections.namedtuple(
            '_ClientCallDetails',
            ('method', 'timeout', 'metadata', 'credentials', 'wait_for_ready',
             'compression')),
        grpc.ClientCallDetails):
  pass


def HeaderAdderInterceptor(headers_func):
  """Returns an interceptor that adds headers."""
  def AddHeaders(client_call_details):
    headers = headers_func()
    if not headers:
      return client_call_details

    metadata = []
    if client_call_details.metadata is not None:
      metadata = list(client_call_details.metadata)

    for header, value in headers:
      metadata.append((header.lower(), value))

    new_client_call_details = _ClientCallDetails(
        client_call_details.method, client_call_details.timeout, metadata,
        client_call_details.credentials, client_call_details.wait_for_ready,
        client_call_details.compression)
    return new_client_call_details

  return ClientCallDetailsInterceptor(AddHeaders)


IAM_AUTHORITY_SELECTOR_HEADER = 'x-goog-iam-authority-selector'
IAM_AUTHORIZATION_TOKEN_HEADER = 'x-goog-iam-authorization-token'


def IAMAuthHeadersInterceptor():
  """Returns an interceptor that adds IAM headers."""
  def GetIAMAuthHeaders():
    headers = []

    authority_selector = properties.VALUES.auth.authority_selector.Get()
    if authority_selector:
      headers.append((IAM_AUTHORITY_SELECTOR_HEADER, authority_selector))

    authorization_token = None
    authorization_token_file = (
        properties.VALUES.auth.authorization_token_file.Get())
    if authorization_token_file:
      try:
        authorization_token = files.ReadFileContents(authorization_token_file)
      except files.Error as e:
        raise Error(e)

    if authorization_token:
      headers.append((
          IAM_AUTHORIZATION_TOKEN_HEADER,
          authorization_token.strip()
      ))
    return headers

  return HeaderAdderInterceptor(GetIAMAuthHeaders)


def RequestReasonInterceptor():
  """Returns an interceptor that adds a request reason header."""
  def GetRequestReasonHeader():
    headers = []
    request_reason = properties.VALUES.core.request_reason.Get()
    if request_reason:
      headers.append(('x-goog-request-reason', request_reason))
    return headers

  return HeaderAdderInterceptor(GetRequestReasonHeader)


def TimeoutInterceptor():
  """Returns an interceptor that adds a timeout."""
  def AddTimeout(client_call_details):
    timeout = properties.VALUES.core.http_timeout.GetInt()
    if not timeout:
      return client_call_details

    new_client_call_details = _ClientCallDetails(
        client_call_details.method, timeout, client_call_details.metadata,
        client_call_details.credentials, client_call_details.wait_for_ready,
        client_call_details.compression)
    return new_client_call_details

  return ClientCallDetailsInterceptor(AddTimeout)


class WrappedStreamingResponse(grpc.Call, grpc.Future):
  """Wrapped streaming response.

  Attributes:
    _response: A grpc.Call/grpc.Future instance representing a service response.
    _fn: Function called on each iteration of this iterator. Takes a lambda
         that produces the next response in the _response iterator.
  """

  def __init__(self, response, fn):
    self._response = response
    self._fn = fn

  def initial_metadata(self):
    return self._response.initial_metadata()

  def trailing_metadata(self):
    return self._response.trailing_metadata()

  def code(self):
    return self._response.code()

  def details(self):
    return self._response.details()

  def debug_error_string(self):
    return self._response.debug_error_string()

  def cancel(self):
    return self._response.cancel()

  def cancelled(self):
    return self._response.cancelled()

  def running(self):
    return self._response.running()

  def done(self):
    return self._response.done()

  def result(self, timeout=None):
    return self._response.result(timeout=timeout)

  def exception(self, timeout=None):
    return self._response.exception(timeout=timeout)

  def traceback(self, timeout=None):
    return self._response.traceback(timeout=timeout)

  def add_done_callback(self, fn):
    return self._response.add_done_callback(fn)

  def add_callback(self, callback):
    return self._response.add_callback(callback)

  def is_active(self):
    return self._response.is_active()

  def time_remaining(self):
    return self._response.time_remaining()

  def __iter__(self):
    return self

  def __next__(self):
    return self._fn(lambda: next(self._response))


class LoggingInterceptor(grpc.UnaryUnaryClientInterceptor,
                         grpc.UnaryStreamClientInterceptor,
                         grpc.StreamUnaryClientInterceptor,
                         grpc.StreamStreamClientInterceptor):
  """Logging Interceptor for logging requests and responses.

  Logging is enabled if the --log-http flag is provided on any command.
  """

  def __init__(self, credentials):
    self._credentials = credentials

  def log_metadata(self, metadata):
    """Logs the metadata.

    Args:
      metadata: `metadata` to be transmitted to
        the service-side of the RPC.
    """
    redact_token = properties.VALUES.core.log_http_redact_token.GetBool()
    for (h, v) in sorted(metadata or [], key=lambda x: x[0]):
      if redact_token and h.lower() == IAM_AUTHORIZATION_TOKEN_HEADER:
        v = '--- Token Redacted ---'
      log.status.Print('{0}: {1}'.format(h, v))

  def log_request(self, client_call_details, request):
    """Logs information about the request.

    Args:
        client_call_details: a grpc._interceptor._ClientCallDetails
            instance containing request metadata.
        request: the request value for the RPC.
    """
    redact_token = properties.VALUES.core.log_http_redact_token.GetBool()

    log.status.Print('=======================')
    log.status.Print('==== request start ====')
    log.status.Print('method: {}'.format(client_call_details.method))
    log.status.Print('== headers start ==')
    if self._credentials:
      if redact_token:
        log.status.Print('authorization: --- Token Redacted ---')
      else:
        log.status.Print('authorization: {}'.format(self._credentials.token))
    self.log_metadata(client_call_details.metadata)
    log.status.Print('== headers end ==')
    log.status.Print('== body start ==')
    log.status.Print('{}'.format(request))
    log.status.Print('== body end ==')
    log.status.Print('==== request end ====')

  def log_response(self, response, time_taken):
    """Logs information about the request.

    Args:
        response: A grpc.Call/grpc.Future instance representing a service
            response.
        time_taken: time, in seconds, it took for the RPC to complete.
    """
    log.status.Print('---- response start ----')
    log.status.Print('code: {}'.format(response.code()))
    log.status.Print('-- headers start --')
    log.status.Print('details: {}'.format(response.details()))
    log.status.Print('-- initial metadata --')
    self.log_metadata(response.initial_metadata())
    log.status.Print('-- trailing metadata --')
    self.log_metadata(response.trailing_metadata())
    log.status.Print('-- headers end --')
    log.status.Print('-- body start --')
    log.status.Print('{}'.format(response.result()))
    log.status.Print('-- body end --')
    log.status.Print(
        'total round trip time (request+response): {0:.3f} secs'.format(
            time_taken))
    log.status.Print('---- response end ----')
    log.status.Print('----------------------')

  def log_requests(self, client_call_details, request_iterator):
    for request in request_iterator:
      self.log_request(client_call_details, request)
      yield request

  def log_streaming_response(self, responses, response, time_taken):
    """Logs information about the response.

    Args:
        responses: A grpc.Call/grpc.Future instance representing a service
            response.
        response: response to log.
        time_taken: time, in seconds, it took for the RPC to complete.
    """
    log.status.Print('---- response start ----')
    log.status.Print('-- headers start --')
    log.status.Print('-- initial metadata --')
    self.log_metadata(responses.initial_metadata())
    log.status.Print('-- headers end --')
    log.status.Print('-- body start --')
    log.status.Print('{}'.format(response))
    log.status.Print('-- body end --')
    log.status.Print(
        'total time (response): {0:.3f} secs'.format(time_taken))
    log.status.Print('---- response end ----')
    log.status.Print('----------------------')

  def log_responses(self, responses):
    def OnDone(response):
      log.status.Print('---- response start ----')
      log.status.Print('code: {}'.format(response.code()))
      log.status.Print('-- headers start --')
      log.status.Print('details: {}'.format(response.details()))
      log.status.Print('-- trailing metadata --')
      self.log_metadata(response.trailing_metadata())
      log.status.Print('-- headers end --')
      log.status.Print('---- response end ----')
      log.status.Print('----------------------')

    def LogResponse(result_generator_func):
      start_time = time.time()
      response = result_generator_func()
      time_taken = time.time() - start_time
      self.log_streaming_response(responses, response, time_taken)
      return response

    responses.add_done_callback(OnDone)
    return WrappedStreamingResponse(responses, LogResponse)

  def intercept_unary_unary(self, continuation, client_call_details, request):
    """Intercepts and logs API interactions.

    Overrides abstract method defined in grpc.UnaryUnaryClientInterceptor.
    Args:
        continuation: a function to continue the request process.
        client_call_details: a grpc._interceptor._ClientCallDetails
            instance containing request metadata.
        request: the request value for the RPC.
    Returns:
        A grpc.Call/grpc.Future instance representing a service response.
    """
    self.log_request(client_call_details, request)

    start_time = time.time()
    response = continuation(client_call_details, request)
    time_taken = time.time() - start_time

    self.log_response(response, time_taken)
    return response

  def intercept_unary_stream(self, continuation, client_call_details,
                             request):
    """Intercepts a unary-stream invocation."""
    self.log_request(client_call_details, request)
    response = continuation(client_call_details, request)
    return self.log_responses(response)

  def intercept_stream_unary(self, continuation, client_call_details,
                             request_iterator):
    """Intercepts a stream-unary invocation asynchronously."""
    start_time = time.time()
    response = continuation(
        client_call_details,
        self.log_requests(client_call_details, request_iterator))
    time_taken = time.time() - start_time
    self.log_response(response, time_taken)
    return response

  def intercept_stream_stream(self, continuation, client_call_details,
                              request_iterator):
    """Intercepts a stream-stream invocation."""
    log.status.Print('initiating request')

    response = continuation(
        client_call_details,
        self.log_requests(client_call_details, request_iterator))

    return self.log_responses(response)


class RPCDurationReporterInterceptor(grpc.UnaryUnaryClientInterceptor):
  """Interceptor for reporting RPC Durations.

  We only report durations for unary-unary RPCs as some streaming RPCs have
  arbitrary duration. i.e. How long they take is decided by the user.
  """

  def intercept_unary_unary(self, continuation, client_call_details, request):
    """Intercepts and logs API interactions.

    Overrides abstract method defined in grpc.UnaryUnaryClientInterceptor.
    Args:
        continuation: a function to continue the request process.
        client_call_details: a grpc._interceptor._ClientCallDetails
            instance containing request metadata.
        request: the request value for the RPC.
    Returns:
        A grpc.Call/grpc.Future instance representing a service response.
    """
    start_time = time.time()
    response = continuation(client_call_details, request)
    time_taken = time.time() - start_time
    metrics.RPCDuration(time_taken)

    return response


def GetSSLCredentials(mtls_enabled):
  """Returns SSL credentials."""
  ca_certs_file = properties.VALUES.core.custom_ca_certs_file.Get()
  certificate_chain = None
  private_key = None

  ca_config = context_aware.Config()
  if mtls_enabled and ca_config:
    log.debug('Using client certificate...')
    certificate_chain, private_key = (ca_config.client_cert_bytes,
                                      ca_config.client_key_bytes)

  if ca_certs_file or certificate_chain or private_key:
    if ca_certs_file:
      ca_certs = files.ReadBinaryFileContents(ca_certs_file)
    else:
      ca_certs = None

    return grpc.ssl_channel_credentials(
        root_certificates=ca_certs,
        certificate_chain=certificate_chain,
        private_key=private_key)
  return None


def MakeProxyFromProperties():
  """Returns the proxy string for use by grpc from gcloud properties."""
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

  proxy_user = properties.VALUES.proxy.username.Get()
  proxy_pass = properties.VALUES.proxy.password.Get()

  http_proxy_type = http_proxy_types.PROXY_TYPE_MAP[proxy_type]
  if http_proxy_type != socks.PROXY_TYPE_HTTP:
    raise ValueError('Unsupported proxy type for gRPC: {}'.format(proxy_type))

  if proxy_user or proxy_pass:
    proxy_auth = ':'.join(
        urllib.parse.quote(x) or '' for x in (proxy_user, proxy_pass))
    proxy_auth += '@'
  else:
    proxy_auth = ''
  return 'http://{}{}:{}'.format(proxy_auth, proxy_address, proxy_port)


def MakeProxyFromEnvironmentVariables():
  """Returns the proxy string for use by grpc from environment variable."""
  # The lowercase versions of these environment variable are already supported
  # by grpc. We add uppercase support for backwards-compatibility with http
  # API clients.
  for env in ['GRPC_PROXY', 'HTTP_PROXY', 'HTTPS_PROXY']:
    proxy = encoding.GetEncodedValue(os.environ, env)
    if proxy:
      return proxy
  return None


def MakeChannelOptions():
  """Returns channel arguments for the underlying gRPC channel.

  See https://grpc.github.io/grpc/python/glossary.html#term-channel_arguments.
  """
  # Default options from transport class
  options = {
      'grpc.max_send_message_length': -1,
      'grpc.max_receive_message_length': -1,
  }

  proxy = MakeProxyFromProperties()
  if not proxy:
    proxy = MakeProxyFromEnvironmentVariables()
  if proxy:
    options['grpc.http_proxy'] = proxy

  return options.items()


def MakeTransport(transport_class, address, credentials, mtls_enabled=False):
  """Instantiates a grpc transport."""
  channel = transport_class.create_channel(
      host=address,
      credentials=credentials,
      ssl_credentials=GetSSLCredentials(mtls_enabled),
      options=MakeChannelOptions())

  interceptors = []
  interceptors.append(RequestReasonInterceptor())
  interceptors.append(IAMAuthHeadersInterceptor())
  interceptors.append(RPCDurationReporterInterceptor())
  if properties.VALUES.core.log_http.GetBool():
    interceptors.append(LoggingInterceptor(credentials))

  channel = grpc.intercept_channel(channel, *interceptors)
  return transport_class(channel=channel, host=address)
