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
"""Helper Classes for creating gapic clients in gcloud."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import time

from googlecloudsdk.core import log
from googlecloudsdk.core import properties

import grpc


class LoggingInterceptor(grpc.UnaryUnaryClientInterceptor):
  """Logging Interceptor for logging requests and responses.

  Logging is enabled if the --log-http flag is provided on any command.
  """

  def log_metadata(self, metadata):
    """Logs the metadata.

    Args:
      metadata: `metadata` to be transmitted to
        the service-side of the RPC.
    """
    for (h, v) in sorted(metadata, key=lambda x: x[0]):
      log.status.Print('{0}: {1}'.format(h, v))

  def log_request(self, client_call_details, request):
    """Logs information about the request.

    Args:
        client_call_details: a grpc._interceptor._ClientCallDetails
            instance containing request metadata.
        request: the request value for the RPC.
    """
    log.status.Print('=======================')
    log.status.Print('==== request start ====')
    log.status.Print('method: {}'.format(client_call_details.method))
    log.status.Print('== headers start ==')
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


def MakeTransport(transport_class, address, credentials):
  """Instantiates a grpc transport."""
  channel = transport_class.create_channel(
      address=address,
      credentials=credentials,
      options={
          'grpc.max_send_message_length': -1,
          'grpc.max_receive_message_length': -1,
      }.items())

  interceptors = []
  if properties.VALUES.core.log_http.GetBool():
    interceptors.append(LoggingInterceptor())

  channel = grpc.intercept_channel(channel, *interceptors)
  return transport_class(channel=channel, address=address)
