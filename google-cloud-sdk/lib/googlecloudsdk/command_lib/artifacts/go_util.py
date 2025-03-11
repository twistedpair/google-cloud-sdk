# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Golang related utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64

from google.auth import exceptions as ga_exceptions
from googlecloudsdk.api_lib.artifacts import exceptions as ar_exceptions
from googlecloudsdk.command_lib.artifacts.print_settings import credentials
from googlecloudsdk.command_lib.util.anthos import binary_operations
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import requests
from googlecloudsdk.core.credentials import creds as c_creds
from googlecloudsdk.core.credentials import store


class PackOperation(binary_operations.BinaryBackedOperation):
  """PackOperation is a wrapper of the package-go-module binary."""

  def __init__(self, **kwargs):
    super(PackOperation, self).__init__(binary='package-go-module', **kwargs)

  def _ParseArgsForCommand(self, module_path, version, source, output,
                           **kwargs):
    args = [
        '--module_path=' + module_path,
        '--version=' + version,
        '--source=' + source,
        '--output=' + output,
    ]
    return args


def _GetAdcToken():
  """Returns the ADC token."""
  creds, _ = c_creds.GetGoogleAuthDefault().default()
  creds.refresh(requests.GoogleAuthRequest())
  return creds.token


def AuthorizationHeader(json_key):
  """Returns the authorization header."""
  # Try --json-key first.
  try:
    creds = credentials.GetServiceAccountCreds(json_key)
    if creds:
      return _BasicAuthHeader(
          '_json_key_base64',
          creds,
      )
    else:
      json_key_err = ar_exceptions.NoJsonKeyCredentialsError(
          '--json-key unspecified'
      )
  except core_exceptions.Error as e:
    json_key_err = ar_exceptions.NoJsonKeyCredentialsError(e)

  # Try ADC next.
  try:
    token = _GetAdcToken()
    return _BearerAuthHeader(token)
  except (ga_exceptions.DefaultCredentialsError, core_exceptions.Error) as e:
    default_creds_err = ar_exceptions.NoDefaultCredentialsError(e)

  # Try user credentials finally.
  try:
    token = store.GetAccessToken()
    return _BearerAuthHeader(token)
  except core_exceptions.Error as e:
    user_creds_err = ar_exceptions.NoUserCredentialsError(e)

  # No credentials found.
  raise ar_exceptions.NoCredentialsError(
      json_key_err, default_creds_err, user_creds_err
  )


def _BasicAuthHeader(username, password):
  creds = base64.b64encode(
      f'{username}:{password}'.encode('utf-8')
  ).decode('utf-8')
  return f'Authorization: Basic {creds}'


def _BearerAuthHeader(token):
  return f'Authorization: Bearer {token}'
