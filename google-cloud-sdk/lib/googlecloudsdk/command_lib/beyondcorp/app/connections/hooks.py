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

"""Hooks for beyondcorp app connections commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions

APP_ENDPOINT_PARSE_ERROR = ('Error parsing application endpoint [{}]: endpoint '
                            'must be prefixed of the form <host>:<port>.')

CONNECTOR_RESOURCE_NAME = ('projects/{}/locations/{}/connectors/{}')


class ApplicationEndpointParseError(exceptions.Error):
  """Error if a application endpoint is improperly formatted."""


def ValidateAndParseAppEndpoint(unused_ref, args, request):
  """Validates app endpoint format and sets endpoint host and port after parsing.

  Args:
    unused_ref:
      The unused request URL.
    args:
      arguments set by user.
    request:
      create connection request raised by framework.

  Returns:
    request with modified application endpoint host and port argument.

  Raises:
    ApplicationEndpointParseError:
  """
  if args.IsSpecified('application_endpoint'):
    endpoint_array = args.application_endpoint.split(':')
    if len(endpoint_array) == 2 and endpoint_array[1].isdigit():
      request.connection.applicationEndpoint.host = endpoint_array[0]
      request.connection.applicationEndpoint.port = int(
          endpoint_array[1])
    else:
      raise ApplicationEndpointParseError(
          APP_ENDPOINT_PARSE_ERROR.format(args.application_endpoint))
  return request


def SetConnectors(unused_ref, args, request):
  """Set the connectors to resource based string format.

  Args:
    unused_ref:
      The unused request URL.
    args:
      arguments set by user.
    request:
      create connection request raised by framework.

  Returns:
    request with modified connectors argument.
  """
  if args.IsSpecified('connectors'):
    for index, connector in enumerate(request.connection.connectors):
      request.connection.connectors[index] = CONNECTOR_RESOURCE_NAME.format(
          args.project, args.location, connector)
  return request
