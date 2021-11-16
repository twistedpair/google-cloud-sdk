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
"""Calls cloud run service of a Google Cloud Function."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json

from googlecloudsdk.api_lib.functions.v2 import exceptions
from googlecloudsdk.api_lib.functions.v2 import util as v2_api_util
from googlecloudsdk.command_lib.config import config_helper
from googlecloudsdk.core import requests as core_requests
from googlecloudsdk.core.credentials import store


import six

_CONTENT_TYPE = 'Content-Type'

# Required and Optional CloudEvent attributes
# https://github.com/cloudevents/spec/blob/v1.0.1/spec.md
_FIELDS = (
    'id', 'source', 'specversion', 'type', 'dataschema', 'subject', 'time'
)

# v2 HTTP triggered functions interpret an empty Content-Type header as leaving
# the request body empty, therefore default the content type as json.
_DEFAULT_HEADERS = {_CONTENT_TYPE: 'application/json'}


def GenerateIdToken():
  """Generate an expiring Google-signed OAuth2 identity token.

  Returns:
    token: str, expiring Google-signed OAuth2 identity token
  """

  # str | None, account is either a user account or google service account.
  account = None

  # oauth2client.client.OAuth2Credentials |
  # core.credentials.google_auth_credentials.Credentials
  cred = store.Load(
      # if account is None, implicitly retrieves properties.VALUES.core.account
      account,
      allow_account_impersonation=True,
      use_google_auth=True)

  # sets token on property of either
  # credentials.token_response['id_token'] or
  # credentials.id_tokenb64
  store.Refresh(cred)

  credential = config_helper.Credential(cred)

  # str, Expiring Google-signed OAuth2 identity token
  token = credential.id_token

  return token


def _StructuredToBinaryData(request_data_json):
  """Convert CloudEvents structured format to binary format.

  Args:
    request_data_json: dict, the parsed request body data

  Returns:
    cloudevent_data: str, the CloudEvent expected data with attributes in header
    cloudevent_headers: dict, the CloudEvent headers
  """

  cloudevent_headers = {}
  cloudevent_data = None

  for key, value in list(request_data_json.items()):
    normalized_key = key.lower()
    if normalized_key == 'data':
      cloudevent_data = value
    elif normalized_key in _FIELDS:
      cloudevent_headers['ce-'+normalized_key] = value
    elif normalized_key == 'datacontenttype':
      cloudevent_headers[_CONTENT_TYPE] = value
    else:
      cloudevent_headers[normalized_key] = value

  if _CONTENT_TYPE not in cloudevent_headers:
    cloudevent_headers[_CONTENT_TYPE] = 'application/json'
  return json.dumps(cloudevent_data), cloudevent_headers


def Run(args, release_track):
  """Call a v2 Google Cloud Function."""
  v2_client = v2_api_util.GetClientInstance(release_track=release_track)
  v2_messages = v2_client.MESSAGES_MODULE

  function_ref = args.CONCEPTS.name.Parse()

  if args.data:
    try:
      json.loads(args.data)
    except ValueError as e:
      raise exceptions.InvalidArgumentException(
          '--data', 'Is not a valid JSON: ' + six.text_type(e))
    request_data = args.data
    headers = _DEFAULT_HEADERS
  elif args.cloud_event:
    try:
      request_data_json = json.loads(args.cloud_event)
    except ValueError as e:
      raise exceptions.InvalidArgumentException(
          '--cloud-event', 'Is not a valid JSON: ' + six.text_type(e))
    request_data, headers = _StructuredToBinaryData(request_data_json)
  else:
    # If neither --data nor --cloud-event flag are specified
    request_data = None
    headers = _DEFAULT_HEADERS

  # cloudfunctions_v2alpha_messages.Function
  function = v2_client.projects_locations_functions.Get(
      v2_messages.CloudfunctionsProjectsLocationsFunctionsGetRequest(
          name=function_ref.RelativeName()))

  cloud_run_uri = function.serviceConfig.uri

  token = GenerateIdToken()
  headers['Authorization'] = 'Bearer {}'.format(token)

  requests_session = core_requests.GetSession()
  response = requests_session.post(
      cloud_run_uri,
      # None | str, if None an empty body is sent in POST request.
      data=request_data,
      headers=headers)

  response.raise_for_status()

  return response.content
