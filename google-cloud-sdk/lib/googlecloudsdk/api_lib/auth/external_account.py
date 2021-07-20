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
"""Manages logic for external accounts."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core.util import files

_EXTERNAL_ACCOUNT_TYPE = 'external_account'


class Error(exceptions.Error):
  """Errors raised by this module."""


class UnsupportedCredentialsType(Error):
  """Raised when given type credentials cannot be created."""


class BadCredentialFileException(Error):
  """Raised when file cannot be read."""


class BadCredentialJsonFileException(Error):
  """Raised when the JSON file is in an invalid format."""


def GetExternalAccountCredentialsConfig(filename):
  """Returns the JSON content if the file corresponds to an external account.

  This function is useful when the content of a file need to be inspected first
  before determining how to handle it. More specifically, it would check a
  config file contains an external account cred and return its content which can
  then be used with CredentialsFromAdcDictGoogleAuth (if the contents
  correspond to an external account cred) to avoid having to open the file
  twice.

  Args:
    filename (str): The filepath to the ADC file representing an external
      account credentials.

  Returns:
    Optional(Mapping): The JSON content if the configuration represents an
      external account. Otherwise None is returned.

  Raises:
    BadCredentialFileException: If JSON parsing of the file fails.
  """

  content = files.ReadFileContents(filename)
  try:
    content_json = json.loads(content)
  except ValueError as e:
    # File has to be in JSON format.
    raise BadCredentialFileException('Could not read json file {0}: {1}'.format(
        filename, e))
  if IsExternalAccountConfig(content_json):
    return content_json
  else:
    return None


def IsExternalAccountConfig(content_json):
  """Returns whether a JSON content corresponds to an external account cred."""
  return (content_json or {}).get('type') == _EXTERNAL_ACCOUNT_TYPE


def CredentialsFromAdcDictGoogleAuth(external_config):
  """Creates external account creds from a dict of application default creds.

  Args:
    external_config (Mapping): The configuration dictionary representing the
      credentials. This is loaded from the ADC file typically.

  Returns:
    google.auth.external_account.Credentials: The initialized external account
      credentials.

  Raises:
    BadCredentialJsonFileException: If the config format is invalid.
    UnsupportedCredentialsType: If the underlying external account credentials
      are unsupported.
  """
  if ('type' not in external_config or
      external_config['type'] != _EXTERNAL_ACCOUNT_TYPE):
    raise BadCredentialJsonFileException(
        'The provided credentials configuration is not in a valid format.')

  # Some non-cloud scopes will need to be removed when gcloud starts supporting
  # external account creds without service account impersonation.
  # This includes: openid and https://www.googleapis.com/auth/userinfo.email.
  scopes = config.CLOUDSDK_SCOPES
  # There are currently 2 types of external_account credentials.
  creds = None
  try:
    # pylint: disable=g-import-not-at-top
    from google.auth import aws

    # Check if configuration corresponds to an AWS credentials.
    creds = aws.Credentials.from_info(external_config, scopes=scopes)
  except ValueError:
    pass

  try:
    # pylint: disable=g-import-not-at-top
    from google.auth import identity_pool

    creds = identity_pool.Credentials.from_info(external_config, scopes=scopes)
  except ValueError:
    pass

  if not creds:
    # If the configuration is invalid or does not correspond to any
    # supported external_account credentials, raise an error.
    raise BadCredentialJsonFileException(
        'The credentials configuration has to correspond to either a '
        'URL-sourced, file-sourced or AWS external account credentials.')

  # Currently only 3PI workload identity pool credentials with service account
  # impersonation are supported.
  if not creds.service_account_email:
    raise UnsupportedCredentialsType(
        'Workload identity pools without service account impersonation are not '
        'supported.')
  return creds
